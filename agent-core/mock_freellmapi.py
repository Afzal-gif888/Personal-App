"""Lightweight mock server for hermetic testing and offline development.

Usage:
    python mock_freellmapi.py --port 31415 --key test-key
"""

import argparse
import asyncio
import json
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
import uvicorn

app = FastAPI(title="Mock FreeLLMAPI")
VALID_KEY = "test-key"


def set_valid_key(key: str) -> None:
    global VALID_KEY
    VALID_KEY = key


@app.get("/v1/models")
async def list_models(authorization: Optional[str] = Header(None)):
    if not authorization or authorization != f"Bearer {VALID_KEY}":
        raise HTTPException(status_code=401, detail="Invalid API key")
    return {"object": "list", "data": [{"id": "auto"}, {"id": "auto:fast"}, {"id": "llama-3.3-70b"}]}


@app.get("/models")
async def list_models_alias(authorization: Optional[str] = Header(None)):
    return await list_models(authorization=authorization)


@app.post("/v1/chat/completions")
async def chat_completion(request: Request, authorization: Optional[str] = Header(None)):
    if not authorization or authorization != f"Bearer {VALID_KEY}":
        raise HTTPException(status_code=401, detail="Invalid API key")

    body = await request.json()
    stream = body.get("stream", False)
    content = "This is a verified mock response from FreeLLMAPI."
    if not stream:
        return {
            "id": "chatcmpl-mock",
            "object": "chat.completion",
            "choices": [{"message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
        }

    async def event_generator():
        words = content.split()
        for w in words:
            chunk = {
                "choices": [{"delta": {"content": w + " "}, "finish_reason": None}]
            }
            yield f"data: {json.dumps(chunk)}\n\n"
            await asyncio.sleep(0.01)
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/chat/completions")
async def chat_completion_alias(request: Request, authorization: Optional[str] = Header(None)):
    return await chat_completion(request=request, authorization=authorization)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=31415)
    parser.add_argument("--key", default="test-key")
    args = parser.parse_args()
    VALID_KEY = args.key
    uvicorn.run(app, host="127.0.0.1", port=args.port)
