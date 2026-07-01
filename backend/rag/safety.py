import re

from llama_index.core.llms import ChatMessage, MessageRole

# Explicit, high-confidence red flags. Deliberately deterministic (no LLM in the loop)
# so the clearest, highest-danger disclosures never depend on model judgment.
_HIGH_RISK_PATTERNS = [
    # Physical violence
    r"\bhit(s|ting)?\s+me\b", r"\bhit me\b", r"\bpunch(ed|es|ing)?\s+me\b",
    r"\bslap(ped|s|ping)?\s+me\b", r"\bchoke[ds]?\s+me\b", r"\bstrangl",
    r"\bthrew\s+(a|the|something)\s+at\s+me\b", r"\bpushed?\s+me\b", r"\bkicked?\s+me\b",
    r"\bbeats?\s+me\b", r"\bbeat\s+me\s+up\b", r"\bleft\s+bruises?\b",
    # Weapons / threats to life
    r"\bweapon\b", r"\bpointed\s+a\s+gun\b", r"\bhe\s+has\s+a\s+gun\b",
    r"\bthreatened?\s+to\s+kill\b", r"\bthreatened?\s+to\s+hurt\b",
    r"\bsaid\s+(he|she|they)('d|\s+would)\s+(kill|hurt)\s+me\b",
    # Fear of partner
    r"\bi'?m\s+(scared|afraid|terrified)\s+of\s+(him|her|them|my\s+\w+)\b",
    r"\b(he|she|they)\s+scares?\s+me\b", r"\bi\s+don'?t\s+feel\s+safe\b",
    r"\bmakes?\s+me\s+feel\s+unsafe\b",
    # Sexual coercion
    r"\bforced?\s+(me\s+)?(to\s+have\s+sex|into\s+sex)\b", r"\brape[ds]?\b",
    r"\bsexual(ly)?\s+assault",
    # Stalking / surveillance / isolation
    r"\bstalking\b", r"\bstalks?\s+me\b", r"\bfollows?\s+me\s+everywhere\b",
    r"\btracks?\s+my\s+(phone|location|car)\b", r"\bwon'?t\s+let\s+me\s+(leave|see\s+my\s+(friends|family))\b",
    r"\bisolat(e[sd]?|ing|ion)\s+me\b", r"\bcuts?\s+me\s+off\s+from\b",
    # Financial control
    r"\bcontrols?\s+(all|my)\s+(the\s+)?money\b", r"\bwon'?t\s+let\s+me\s+(have|use)\s+(my\s+own\s+)?(bank|money|credit)\b",
    r"\btakes?\s+(all\s+)?my\s+paych(eck|ecks)\b", r"\bfinancial\s+abuse\b",
    # Retaliation / explicit disclosure
    r"\bthreatened?\s+to\s+take\s+(the\s+)?kids\b", r"\bthreatened?\s+to\s+leak\b",
    r"\bcoercive\s+control\b", r"\bdomestic\s+violence\b", r"\bhe'?s\s+abusive\b",
    r"\bshe'?s\s+abusive\b", r"\babusive\s+relationship\b",
]
_HIGH_RISK_RE = re.compile("|".join(_HIGH_RISK_PATTERNS), re.IGNORECASE)


def contains_high_risk_language(text: str) -> bool:
    return bool(_HIGH_RISK_RE.search(text))


_CLASSIFIER_SYSTEM_PROMPT = """\
You are a safety classifier for a relationship-support chat app. Your ONLY job is to decide \
whether the user's latest message, read in light of the conversation so far, describes signs of \
intimate partner violence (IPV) or abuse in their relationship — not an ordinary disagreement.

Per the CDC and the National Domestic Violence Hotline, treat any ONE of the following as a \
red flag, even on its own:
- Fear of a partner, or fear of what a partner might do
- Threats of harm, violence, or retaliation
- Physical violence of any kind
- Coercive control (controlling what the person does, wears, or who they see)
- Isolation from friends or family
- Stalking or surveillance (monitoring phone, location, messages)
- Forced or coerced sexual activity
- Financial control (restricting access to money, accounts, or income)

Do NOT flag ordinary relationship conflict: disagreements about chores, spending decisions \
(without control), parenting differences, feeling unheard, or jealousy without threats.

Respond with exactly one word, nothing else: YES or NO.
"""


async def classify_abuse_risk(llm, message: str, recent_history: list[ChatMessage]) -> bool:
    """Ask the LLM to judge whether the message/context describes IPV. Used only when the
    deterministic keyword gate finds nothing, to catch subtler or indirect disclosures."""
    messages = (
        [ChatMessage(role=MessageRole.SYSTEM, content=_CLASSIFIER_SYSTEM_PROMPT)]
        + recent_history
        + [ChatMessage(role=MessageRole.USER, content=message)]
    )
    response = await llm.achat(messages)
    answer = (response.message.content or "").strip().upper()
    return answer.startswith("YES")


SAFETY_RESOURCES_RESPONSE = """\
What you're describing doesn't sound like an ordinary disagreement — it sounds like it may \
involve fear, control, or violence. That's outside what a communication-coaching tool like this \
one is safe to help with, and I don't want to give advice that could put you at more risk.

You deserve support from people trained for this:

- **National Domestic Violence Hotline** — call 1-800-799-7233, or text START to 88788, \
available 24/7
- **thehotline.org** — live chat and safety planning resources
- If you're in immediate danger, please call 911 (or your local emergency number).

I'm not going to suggest talking this through with your partner or couples counseling — when \
abuse is present, joint counseling can be unsafe, and advocates specifically advise against it. \
A trained advocate can help you think through next steps at your own pace, including whether and \
how to leave safely, without any pressure to decide right now.\
"""
