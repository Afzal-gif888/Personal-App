"""The LangGraph workflow and the runner that executes it safely.

    START
      -> validate_input -> load_context -> understand_request -> gather_context -> plan
      -> agent --(tool calls)--> execute_tools -> observe --(continue)--> agent
         agent --(answer / error / limit)--> final_response -> END

Loop safety: `max_agent_iterations` and `max_tool_calls` stop the loop from inside the graph, the
LangGraph recursion limit backs them up, and `agent_timeout_seconds` bounds the whole run.
"""

import asyncio
import logging
import uuid
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.errors import GraphRecursionError
from langgraph.graph import END, START, StateGraph

from app.agent import nodes, router
from app.agent.nodes import RunDeps
from app.agent.state import AgentState
from app.schemas.agent import (
    AgentError,
    AgentRunRequest,
    AgentRunResponse,
    ErrorCode,
    RunStatus,
)
from app.schemas.events import AgentEventType, event

logger = logging.getLogger(__name__)


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("validate_input", nodes.validate_input)
    graph.add_node("load_context", nodes.load_context)
    graph.add_node("understand_request", nodes.understand_request)
    graph.add_node("gather_context", nodes.gather_context)
    graph.add_node("plan", nodes.plan)
    graph.add_node("agent", nodes.agent)
    graph.add_node("execute_tools", nodes.execute_tools)
    graph.add_node("observe", nodes.observe)
    graph.add_node("final_response", nodes.final_response)

    graph.add_edge(START, "validate_input")
    graph.add_conditional_edges("validate_input", router.after_validate, ["load_context", "final_response"])
    graph.add_conditional_edges("load_context", router.after_load_context, ["understand_request", "final_response"])
    graph.add_edge("understand_request", "gather_context")
    graph.add_edge("gather_context", "plan")
    graph.add_edge("plan", "agent")
    graph.add_conditional_edges("agent", router.after_agent, ["execute_tools", "final_response"])
    graph.add_edge("execute_tools", "observe")
    graph.add_conditional_edges("observe", router.after_observe, ["agent", "final_response"])
    graph.add_edge("final_response", END)
    return graph.compile()


class AgentRunner:
    def __init__(self, graph=None) -> None:
        self.graph = graph or build_graph()

    @staticmethod
    def recursion_limit(max_iterations: int) -> int:
        # 5 fixed nodes before the loop, 3 nodes per iteration (agent, execute_tools, observe), final.
        return 3 * max_iterations + 10

    async def run(self, request: AgentRunRequest, deps: RunDeps, *, run_id: str | None = None) -> AgentRunResponse:
        run_id = run_id or f"run_{uuid.uuid4().hex}"
        initial = AgentState(
            run_id=run_id, request=request.message, conversation_id=request.conversation_id,
            expected_user_id=request.user_id, history=request.history,
        )
        config: RunnableConfig = {
            "configurable": {"deps": deps},
            "recursion_limit": self.recursion_limit(deps.settings.max_agent_iterations),
        }
        last: dict[str, Any] = initial.model_dump()
        try:
            async with asyncio.timeout(deps.settings.agent_timeout_seconds):
                async for values in self.graph.astream(initial, config=config, stream_mode="values"):
                    last = values if isinstance(values, dict) else values.model_dump()
            state = AgentState.model_validate(last)
        except TimeoutError:
            state = self._stopped(last, ErrorCode.TIMEOUT, "That took too long, so I stopped. Please try a simpler request.")
        except GraphRecursionError:
            state = self._stopped(last, ErrorCode.ITERATION_LIMIT, "I stopped because this request needed too many steps.")
        except Exception:
            logger.exception("Agent run crashed", extra={"run_id": run_id})
            state = self._stopped(last, ErrorCode.INTERNAL_ERROR, "Something went wrong on our side. Please try again.")
        return self._response(state)

    @staticmethod
    def _stopped(last: dict[str, Any], code: ErrorCode, message: str) -> AgentState:
        state = AgentState.model_validate(last)
        status = RunStatus.INCOMPLETE if code == ErrorCode.ITERATION_LIMIT else RunStatus.FAILED
        return state.model_copy(update={
            "error": AgentError(code=code, message=message, retryable=code == ErrorCode.TIMEOUT),
            "status": status, "final_response": message,
            "events": [*state.events, event(AgentEventType.RUN_FAILED, state.run_id, code=code.value)],
        })

    @staticmethod
    def _response(state: AgentState) -> AgentRunResponse:
        status = state.status or (RunStatus.FAILED if state.error else RunStatus.COMPLETED)
        return AgentRunResponse(
            run_id=state.run_id,
            status=status,
            response=state.final_response or "",
            tool_calls=state.tool_calls,
            approval_required=bool(state.pending_approvals),
            approvals=state.pending_approvals,
            retrieved_documents=[
                {"document_id": c.document_id, "document_name": c.document_name, "chunk_id": c.chunk_id, "score": c.score}
                for c in state.retrieved_documents
            ],
            events=[e.model_dump(mode="json") for e in state.events],
            error=state.error,
            metadata={
                **{k: v for k, v in state.metadata.items() if isinstance(v, str | int | float | bool)},
                "iterations": state.iterations,
                "tool_call_count": state.tool_call_count,
                "plan_steps": len(state.plan),
                "domains": [d.value for d in state.intent.domains],
            },
        )
