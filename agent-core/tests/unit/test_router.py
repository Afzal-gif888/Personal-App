from app.agent.router import offered_domains, understand
from app.schemas.tool import ToolDomain as D


def test_document_questions_need_retrieval():
    for text in ("According to my uploaded DBMS notes, explain normalization.",
                 "What do my notes say about joins?", "Based on my documents, summarise chapter 2"):
        intent = understand(text)
        assert intent.needs_documents, text
        assert D.DOCUMENTS in intent.domains


def test_unrelated_requests_do_not_trigger_retrieval():
    for text in ("What bills are due this week?", "Create a task to finish my ML assignment tomorrow.",
                 "Remind me to pay my electricity bill tomorrow at 7 PM.", "Hi!"):
        assert not understand(text).needs_documents, text


def test_domains_scope_the_tools_offered():
    assert D.FINANCE in understand("What bills are due this week?").domains
    assert D.REMINDERS in understand("Remind me every Monday to review my study plan").domains
    study = understand("I have an ML exam next Friday. Create a study plan based on my tasks.")
    assert {D.STUDY, D.TASKS, D.EVENTS} <= set(study.domains)
    assert study.multi_step and study.wants_change


def test_overview_requests_cover_every_life_area():
    intent = understand("What do I need to take care of this week?")
    assert {D.TASKS, D.EVENTS, D.REMINDERS, D.FINANCE, D.GOALS, D.STUDY} <= set(intent.domains)
    assert intent.multi_step and not intent.needs_documents


def test_unscoped_requests_offer_all_tools():
    intent = understand("Hello there")
    assert intent.domains == [] and offered_domains(intent) is None
