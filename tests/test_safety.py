from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.conftest import AUTH_HEADERS
from backend.rag.safety import classify_abuse_risk, contains_high_risk_language

POSITIVE_EXAMPLES = [
    "He hit me last night after we argued about money.",
    "He threatened to kill me if I ever tried to leave.",
    "He controls all our money and won't let me have my own bank account.",
    "He tracks my phone constantly and gets angry if I don't answer right away.",
    "He forced me to have sex when I said no.",
    "I'm scared of my husband, he scares me when he gets like this.",
    "He said he'd hurt me if I told anyone.",
    "This feels like coercive control, not a normal disagreement.",
    "I think I'm in an abusive relationship.",
]

NEGATIVE_EXAMPLES = [
    "I came home exhausted and found the kitchen exactly how I'd left it that morning.",
    "I saw a $900 charge on the shared credit card for a new road bike.",
    "His mother invited us to a family trip and told us the dates before asking us.",
    "He let our daughter watch tablet videos through dinner again.",
    "I started telling him about a frustrating meeting and he jumped to solutions.",
    "We disagree about how to split chores around the house.",
]


@pytest.mark.parametrize("text", POSITIVE_EXAMPLES)
def test_high_risk_language_detects_explicit_red_flags(text):
    assert contains_high_risk_language(text) is True


@pytest.mark.parametrize("text", NEGATIVE_EXAMPLES)
def test_high_risk_language_does_not_flag_ordinary_conflict(text):
    assert contains_high_risk_language(text) is False


@pytest.mark.asyncio
async def test_classify_abuse_risk_parses_yes():
    llm = MagicMock()
    llm.achat = AsyncMock(return_value=MagicMock(message=MagicMock(content="YES")))
    result = await classify_abuse_risk(llm, "he won't let me see my friends anymore", [])
    assert result is True


@pytest.mark.asyncio
async def test_classify_abuse_risk_parses_no():
    llm = MagicMock()
    llm.achat = AsyncMock(return_value=MagicMock(message=MagicMock(content="NO")))
    result = await classify_abuse_risk(llm, "we disagreed about chores", [])
    assert result is False


def test_session_safety_flag_defaults_false_and_is_sticky(history_store):
    history_store.create_session("s1")
    assert history_store.is_session_flagged("s1") is False

    history_store.flag_session_safety("s1")
    assert history_store.is_session_flagged("s1") is True


def test_flagging_unknown_session_is_safe_noop(history_store):
    history_store.flag_session_safety("does-not-exist")
    assert history_store.is_session_flagged("does-not-exist") is False


def test_chat_uses_mocked_engine_regardless_of_safety_wiring(client):
    # The router-level client fixture mocks RAGEngine entirely, so this just
    # confirms /chat still works end-to-end with the new engine constructor signature.
    session_id = client.post("/sessions", headers=AUTH_HEADERS).json()["session_id"]
    resp = client.post(
        "/chat",
        headers=AUTH_HEADERS,
        json={"session_id": session_id, "message": "hello", "stream": False},
    )
    assert resp.status_code == 200
