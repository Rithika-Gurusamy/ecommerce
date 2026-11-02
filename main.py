from fastapi import FastAPI,HTTPException
from pydantic import BaseModel


orders = []
order_id = 1

class OrderCreate(BaseModel):
    product_id: int
    quantity: int


app = FastAPI()


products = [
{
"product_id": 101,
"name": "Wireless Mouse",
"price": 799.00,
"quantity": 20,
"category": "Electronics"
},
{
"product_id": 102,
"name": "Mechanical Keyboard",
"price": 1499.00,
"quantity": 15,
"category": "Electronics"
},
{
"product_id": 103,
"name": "USB-C Charger",
"price": 599.00,
"quantity": 30,
"category": "Accessories"
},
{
"product_id": 104,
"name": "Laptop Stand",
"price": 999.00,
"quantity": 10,
"category": "Accessories"
},
{
"product_id": 105,
"name": "Bluetooth Headphones",
"price": 2499.00,
"quantity": 12,
"category": "Electronics"
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

            order = {
                "order_id": order_id,
                "product_id": order.product_id,
                "product_name": product["name"],
                "quantity": order.quantity,
                "total_price": product["price"] * order.quantity,
                "status": "confirmed"
            }

            orders.append(order)
            order_id += 1

            return order

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