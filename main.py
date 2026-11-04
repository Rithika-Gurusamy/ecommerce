import sys
import os

# Ensure the project root is on sys.path so `agent` package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.types import Command

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/images", StaticFiles(directory="images"), name="images")

orders = []
order_id = 1

class OrderCreate(BaseModel):
    product_id: int
    quantity: int


products = [
    {
        "product_id": 101,
        "name": "Wireless Mouse",
        "price": 799.00,
        "quantity": 20,
        "category": "Electronics",
        "image_url": "/images/101.png"
    },
    {
        "product_id": 102,
        "name": "Mechanical Keyboard",
        "price": 1499.00,
        "quantity": 15,
        "category": "Electronics",
        "image_url": "/images/102.png"
    },
    {
        "product_id": 103,
        "name": "USB-C Charger",
        "price": 599.00,
        "quantity": 30,
        "category": "Accessories",
        "image_url": "/images/103.png"
    },
    {
        "product_id": 104,
        "name": "Laptop Stand",
        "price": 999.00,
        "quantity": 10,
        "category": "Accessories",
        "image_url": "/images/104.png"
    },
    {
        "product_id": 105,
        "name": "Bluetooth Headphones",
        "price": 2499.00,
        "quantity": 12,
        "category": "Electronics",
        "image_url": "/images/105.png"
    }
]


@app.get("/")
def home():
    return "hello"

@app.get("/products")
def get_products():
    return products

@app.get("/products/{product_id}")
def get_product(product_id: int):
    for product in products:
        if product["product_id"] == product_id:
            return product

    raise HTTPException(status_code=404, detail="Product not found")

@app.post("/orders")
def create_order(order: OrderCreate):
    global order_id

    if order.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be greater than zero")

    for product in products:
        if product["product_id"] == order.product_id:
            if product["quantity"] < order.quantity:
                raise HTTPException(status_code=400, detail="Not enough stock")

            product["quantity"] -= order.quantity

            new_order = {
                "order_id": order_id,
                "product_id": order.product_id,
                "product_name": product["name"],
                "quantity": order.quantity,
                "total_price": product["price"] * order.quantity,
                "status": "confirmed"
            }

            orders.append(new_order)
            order_id += 1

            return new_order

    raise HTTPException(status_code=404, detail="Product not found")

@app.get("/orders")
def get_orders():
    return orders


@app.get("/orders/{order_id}")
def get_order(order_id: int):
    for order in orders:
        if order["order_id"] == order_id:
            return order

    raise HTTPException(status_code=404, detail="Order not found")

@app.post("/orders/cancel/{order_id}")
def cancel_order(order_id: int):
    for order in orders:
        if order["order_id"] == order_id:

            if order["status"] == "cancelled":
                raise HTTPException(
                    status_code=400,
                    detail="Order is already cancelled"
                )

            for product in products:
                if product["product_id"] == order["product_id"]:
                    product["quantity"] += order["quantity"]
                    order["status"] = "cancelled"
                    return order

    raise HTTPException(status_code=404, detail="Order not found")


# ══════════════════════════════════════════════════════════════════
# Agent Endpoints
# ══════════════════════════════════════════════════════════════════

class ChatRequest(BaseModel):
    session_id: str
    message: str

class ConfirmRequest(BaseModel):
    session_id: str


@app.post("/agent/chat")
async def agent_chat(req: ChatRequest):
    """Send a message to the agent and get a response."""
    from agent.graph import get_agent

    graph = get_agent()
    config = {"configurable": {"thread_id": req.session_id}}

    # Run the graph with the new user message
    result = graph.invoke(
        {"messages": [HumanMessage(content=req.message)]},
        config=config,
    )

    # Check if the graph hit an interrupt (pending order confirmation)
    graph_state = graph.get_state(config)

    if graph_state.next:
        # Graph is paused at human_confirmation node
        # The interrupt value contains the pending order info
        interrupt_value = None
        if graph_state.tasks:
            for task in graph_state.tasks:
                if hasattr(task, "interrupts") and task.interrupts:
                    interrupt_value = task.interrupts[0].value

        # Get the last AI message for the response text
        response_text = _extract_last_ai_message(result["messages"])

        return {
            "session_id": req.session_id,
            "response": response_text,
            "action": "confirm_order",
            "pending_order": interrupt_value.get("pending_order") if interrupt_value else None,
        }

    # Normal response — no confirmation needed
    response_text = _extract_last_ai_message(result["messages"])

    return {
        "session_id": req.session_id,
        "response": response_text,
        "action": "none",
        "pending_order": None,
    }


@app.post("/agent/confirm")
async def agent_confirm(req: ConfirmRequest):
    """Confirm a pending order."""
    from agent.graph import get_agent

    graph = get_agent()
    config = {"configurable": {"thread_id": req.session_id}}

    # Resume the graph with confirmation
    result = graph.invoke(
        Command(resume={"confirmed": True}),
        config=config,
    )

    response_text = _extract_last_ai_message(result["messages"])

    return {
        "session_id": req.session_id,
        "response": response_text,
        "action": "order_placed",
    }


@app.post("/agent/cancel")
async def agent_cancel(req: ConfirmRequest):
    """Cancel a pending order."""
    from agent.graph import get_agent

    graph = get_agent()
    config = {"configurable": {"thread_id": req.session_id}}

    # Resume the graph with cancellation
    result = graph.invoke(
        Command(resume={"confirmed": False}),
        config=config,
    )

    response_text = _extract_last_ai_message(result["messages"])

    return {
        "session_id": req.session_id,
        "response": response_text,
        "action": "order_cancelled",
    }


def _extract_last_ai_message(messages: list) -> str:
    """Extract the text content of the last AI message."""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content:
            # content can be a string or a list of content blocks
            if isinstance(msg.content, str):
                return msg.content
            elif isinstance(msg.content, list):
                text_parts = []
                for block in msg.content:
                    if isinstance(block, str):
                        text_parts.append(block)
                    elif isinstance(block, dict) and block.get("type") == "text":
                        text_parts.append(block["text"])
                return "\n".join(text_parts) if text_parts else ""
    return "I'm sorry, I couldn't generate a response."
