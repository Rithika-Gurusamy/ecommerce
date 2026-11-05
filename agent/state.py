from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """State schema for the e-commerce agent graph."""
    # Chat history — LangGraph's add_messages reducer appends new messages
    messages: Annotated[list, add_messages]
