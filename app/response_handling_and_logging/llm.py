"""
llm.py — tool-calling agent implementing the hydration algorithm:
  - log water directly if amount is clear
  - if user references a container, look it up first, then log
  - if container not found, ask a clarifying question instead of logging
  - "how much left" -> get_remaining_goal
  - "how am I doing" -> get_analytics

phone_number is NEVER a model-supplied argument — it's bound into each
tool via closure, per request, so the model can't mis-target a user.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition

import app.util.hydration_service  as firestore_tools
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
max_tokens = int(os.getenv("MAX_TOKENS", 500))
model_name = os.getenv("LLM_MODEL", "gemini-2.5-flash-lite")
logger = logging.getLogger("llm")

SYSTEM_PROMPT = """You are BlueDrop's hydration assistant, texting with a user over WhatsApp.

- If they mention drinking water with a clear amount, log it and confirm briefly.
- If they reference "my bottle" / "my cup" / a container instead of a number,
  look up their containers first to resolve the amount, then log it.
  If no matching container is found, ask a short clarifying question instead
  of logging anything.
- If they ask how much water they have left today, look it up and tell them.
- If they ask how they're doing / their progress, pull their analytics and
  summarize it briefly and warmly.
- Keep replies short — this is a text message, not an email.
"""

model = ChatGoogleGenerativeAI(model=model_name, api_key=api_key, max_output_tokens=max_tokens, temperature=0.2)


def _build_tools(phone_number: str):
    """Tools bound to one specific user. Rebuilt per request — phone_number
    is captured here, never exposed as an argument the model can set."""

    @tool
    def log_water(amount: int) -> dict:
        """Log that the user drank `amount` milliliters of water."""
        result = firestore_tools.log_water(phone_number, amount)
        return result.data if not result.failed else {"error": result.error}

    @tool
    def get_remaining_goal() -> dict:
        """Get how much water the user still needs today to hit their goal."""
        result = firestore_tools.get_remaining_goal(phone_number)
        return result.data if not result.failed else {"error": result.error}

    @tool
    def get_user_container() -> dict:
        """Get the user's hydration container(s) — use this to resolve an
        amount when the user references a container instead of a number."""
        result = firestore_tools.get_user_container(phone_number)
        return result.data if not result.failed else {"error": result.error}

    @tool
    def get_analytics() -> dict:
        """Get the user's hydration analytics/progress summary."""
        result = firestore_tools.get_analytics(phone_number)
        return result.data if not result.failed else {"error": result.error}

    return [log_water, get_remaining_goal, get_user_container, get_analytics]


def _build_graph(tools):
    model_with_tools = model.bind_tools(tools)
    tool_node = ToolNode(tools)

    def call_model(state: MessagesState):
        response = model_with_tools.invoke(state["messages"])
        return {"messages": [response]}

    graph = StateGraph(MessagesState)
    graph.add_node("agent", call_model)
    graph.add_node("tools", tool_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", tools_condition)
    graph.add_edge("tools", "agent")
    return graph.compile()


@dataclass
class AgentResult:
    failed: bool
    reply_text: Optional[str] = None
    error: str = ""


def _extract_reply_text(content) -> str:
    """
    Gemini's content can come back as a plain string, or as a list of
    content blocks (each a dict with 'type'/'text'/'extras'). Always
    reduce to a plain string — never send raw blocks to WhatsApp.
    """
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        return " ".join(parts).strip()

    return str(content)


def process(phone_number: str, text: str) -> AgentResult:
    try:
        tools = _build_tools(phone_number)
        graph = _build_graph(tools)

        final_state = graph.invoke({
            "messages": [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=text),
            ]
        })

        last_message = final_state["messages"][-1]
        return AgentResult(failed=False, reply_text=_extract_reply_text(last_message.content))
    except Exception as e:
        logger.error("llm.process failed for phone_number=%s: %s", phone_number, e)
        return AgentResult(failed=True, error=str(e))
    
    
if __name__ == "__main__":
    TEST_CASES = [
        ("direct log, clear amount", "I just drank 250ml of water."),
        ("direct log, vague quantity word", "Just had a glass of water."),
        ("container reference, should resolve via lookup", "Finished my whole bottle just now."),
        ("container reference, none on file (expect clarify)", "Drank a full flask."),
        ("remaining goal query", "How much water do I have left to drink today?"),
        ("analytics / progress query", "How am I doing with my water this week?"),
        ("ambiguous, no amount/container", "water"),
        ("unrelated message (expect graceful fallback)", "What's the weather like today?"),
    ]

    phone_number = "08142156076"

    for label, text in TEST_CASES:
        print(f"\n=== {label} ===")
        print(f"  input: {text!r}")
        result = process(phone_number, text)
        if result.failed:
            print(f"  FAILED: {result.error}")
        else:
            print(f"  reply: {result.reply_text}")