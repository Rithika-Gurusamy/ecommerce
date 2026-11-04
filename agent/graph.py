"""
LangGraph ReAct agent for the e-commerce store.

Graph flow:
  User message → reason (LLM) → tool call → reason → ... → response
  If prepare_order tool succeeds → interrupt for human confirmation → finalize
"""
import os
import json

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command

from agent.state import AgentState
from agent.prompts import SYSTEM_PROMPT
from agent.tools import all_tools, get_product_info, prepare_order


# ── LLM setup ────────────────────────────────────────────────────
def _get_llm():
    api_key = os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable is not set.")
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
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
    pending_order = state.get("pending_order")

    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]

        if tool_name in tool_map:
            result = tool_map[tool_name].invoke(tool_args)
        else:
            result = f"Error: Unknown tool '{tool_name}'"

        # Check if prepare_order returned a pending order
        if tool_name == "prepare_order" and isinstance(result, str) and result.startswith("PENDING_ORDER|"):
            parts = result.split("|")
            pending_order = {
                "product_id": int(parts[1]),
                "product_name": parts[2],
                "quantity": int(parts[3]),
                "unit_price": float(parts[4]),
                "total_price": float(parts[5]),
            }
            # Give the LLM a clean message instead of the raw format
            result = (
                f"Pending order created:\n"
                f"Product: {pending_order['product_name']}\n"
                f"Quantity: {pending_order['quantity']}\n"
                f"Unit Price: ₹{pending_order['unit_price']}\n"
                f"Total: ₹{pending_order['total_price']}\n\n"
                f"Awaiting user confirmation."
            )

        results.append(
            ToolMessage(content=str(result), tool_call_id=tool_call["id"])
        )

    return {"messages": results, "pending_order": pending_order}


def human_confirmation(state: AgentState) -> dict:
    """Interrupt the graph and wait for human to confirm or cancel the order."""
    pending = state.get("pending_order")
    if not pending:
        return {"messages": [], "order_confirmed": None}

    # This pauses the graph — it will resume when the user sends a Command
    decision = interrupt(
        {
            "type": "confirm_order",
            "pending_order": pending,
            "message": (
                f"🛒 **Order Summary**\n"
                f"- Product: {pending['product_name']}\n"
                f"- Quantity: {pending['quantity']}\n"
                f"- Unit Price: ₹{pending['unit_price']}\n"
                f"- Total: ₹{pending['total_price']}\n\n"
                f"Please **confirm** or **cancel** this order."
            ),
        }
    )

    # `decision` is the value passed in via Command(resume=...) 
    confirmed = decision.get("confirmed", False) if isinstance(decision, dict) else bool(decision)
    return {"order_confirmed": confirmed}


def finalize_order(state: AgentState) -> dict:
    """Finalize or discard the order based on human decision."""
    from main import products, orders, order_id as _oid
    import main

    pending = state.get("pending_order")
    confirmed = state.get("order_confirmed", False)

    if not pending:
        msg = "No pending order to process."
        return {
            "messages": [AIMessage(content=msg)],
            "pending_order": None,
            "order_confirmed": None,
        }

    if confirmed:
        # Actually place the order — reuse logic from main.py
        for product in products:
            if product["product_id"] == pending["product_id"]:
                if product["quantity"] < pending["quantity"]:
                    msg = f"❌ Sorry, stock changed while waiting. Only {product['quantity']} left."
                    return {
                        "messages": [AIMessage(content=msg)],
                        "pending_order": None,
                        "order_confirmed": None,
                    }

                product["quantity"] -= pending["quantity"]

                new_order = {
                    "order_id": main.order_id,
                    "product_id": pending["product_id"],
                    "product_name": pending["product_name"],
                    "quantity": pending["quantity"],
                    "total_price": pending["total_price"],
                    "status": "confirmed",
                }
                orders.append(new_order)
                main.order_id += 1

                msg = (
                    f"✅ **Order #{new_order['order_id']} confirmed!**\n"
                    f"{pending['product_name']} × {pending['quantity']} = ₹{pending['total_price']}\n\n"
                    f"You can view it in My Orders."
                )
                return {
                    "messages": [AIMessage(content=msg)],
                    "pending_order": None,
                    "order_confirmed": None,
                }

        msg = "❌ Error: Product not found. The order could not be placed."
    else:
        msg = "❌ Order cancelled. No changes were made."

    return {
        "messages": [AIMessage(content=msg)],
        "pending_order": None,
        "order_confirmed": None,
    }


# ── Conditional Edges ────────────────────────────────────────────

def should_continue(state: AgentState) -> str:
    """After the LLM responds, decide: call tools or finish?"""
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return "end"


def after_tools(state: AgentState) -> str:
    """After tools execute, check if there's a pending order needing confirmation."""
    if state.get("pending_order"):
        return "human_confirmation"
    return "reason"


# ── Build the Graph ──────────────────────────────────────────────

def build_graph():
    """Construct and compile the LangGraph agent."""
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("reason", reason)
    graph.add_node("tools", tool_executor)
    graph.add_node("human_confirmation", human_confirmation)
    graph.add_node("finalize_order", finalize_order)

    # Entry point
    graph.add_edge(START, "reason")

    # After reasoning: either call tools or respond to user
    graph.add_conditional_edges("reason", should_continue, {
        "tools": "tools",
        "end": END,
    })

    # After tools: either go to confirmation or back to reasoning
    graph.add_conditional_edges("tools", after_tools, {
        "human_confirmation": "human_confirmation",
        "reason": "reason",
    })

    # After human confirmation → finalize
    graph.add_edge("human_confirmation", "finalize_order")

    # After finalize → done
    graph.add_edge("finalize_order", END)

    # Compile with in-memory checkpointing (supports interrupt/resume)
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

