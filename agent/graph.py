"""
LangGraph ReAct agent for the e-commerce store.

Graph flow:
  User message → reason (LLM) → tool call → reason (LLM) → response
"""
import os
from dotenv import load_dotenv

# Automatically load environment variables from .env
load_dotenv()

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import ToolMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from agent.state import AgentState
from agent.prompts import SYSTEM_PROMPT
from agent.tools import all_tools


# ── LLM setup ────────────────────────────────────────────────────
def _get_llm():
    api_key = os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable is not set.")
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=api_key,
    )
    return llm.bind_tools(all_tools)


# ── Graph Nodes ───────────────────────────────────────────────────

def reason(state: AgentState) -> dict:
    """LLM reasons about the user's message and decides whether to call a tool."""
    llm = _get_llm()
    messages = state["messages"]

    # Prepend system prompt if not already there
    if not messages or not isinstance(messages[0], SystemMessage):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + list(messages)

    response = llm.invoke(messages)
    return {"messages": [response]}


def tool_executor(state: AgentState) -> dict:
    """Execute the tool(s) requested by the LLM."""
    last_message = state["messages"][-1]

    tool_map = {t.name: t for t in all_tools}
    results = []

    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]

        if tool_name in tool_map:
            result = tool_map[tool_name].invoke(tool_args)
        else:
            result = f"Error: Unknown tool '{tool_name}'"

        results.append(
            ToolMessage(content=str(result), tool_call_id=tool_call["id"])
        )

    return {"messages": results}


# ── Conditional Edges ────────────────────────────────────────────

def should_continue(state: AgentState) -> str:
    """After the LLM responds, decide: call tools or finish?"""
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return "end"


# ── Build the Graph ──────────────────────────────────────────────

def build_graph():
    """Construct and compile the LangGraph agent."""
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("reason", reason)
    graph.add_node("tools", tool_executor)

    # Entry point
    graph.add_edge(START, "reason")

    # After reasoning: either call tools or respond to user
    graph.add_conditional_edges("reason", should_continue, {
        "tools": "tools",
        "end": END,
    })

    # After tools execute: back to reasoning to formulate final response
    graph.add_edge("tools", "reason")

    # Compile with in-memory checkpointing (thread_id per session)
    memory = MemorySaver()
    return graph.compile(checkpointer=memory)


# Single graph instance shared across the app
agent_graph = None


def get_agent():
    """Get or create the singleton agent graph."""
    global agent_graph
    if agent_graph is None:
        agent_graph = build_graph()
    return agent_graph
