from fastapi import FastAPI,HTTPException

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