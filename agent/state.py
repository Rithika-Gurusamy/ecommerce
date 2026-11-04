from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """State schema for the e-commerce agent graph."""
    # Chat history — LangGraph's add_messages reducer appends new messages
    messages: Annotated[list, add_messages]
    # Pending order awaiting human confirmation (None if no pending order)
    pending_order: dict | None
    # Human decision: True = confirm, False = cancel, None = waiting
    order_confirmed: bool | None

