"""
Tools for the e-commerce agent.
These functions directly access the in-memory products/orders lists from main.py.
"""
from langchain_core.tools import tool


def _get_products_ref():
    """Lazy import to avoid circular imports — grabs the live products list from main."""
    from main import products
    return products


@tool
def get_product_info(query: str) -> str:
    """Look up product information from the store inventory.

    Use this tool when the user asks about products, prices, availability, or categories.

    Args:
        query: A product name, keyword, category, or "all" to list everything.
    """
    products = _get_products_ref()

    # If user wants all products
    if query.strip().lower() in ("all", "list", "everything", "show all", "products"):
        lines = []
        for p in products:
            lines.append(
                f"- {p['name']} (ID: {p['product_id']}) | "
                f"Price: ₹{p['price']} | "
                f"In Stock: {p['quantity']} | "
                f"Category: {p['category']}"
            )
        return "Here are all available products:\n" + "\n".join(lines)

    # Fuzzy search by name or category
    query_lower = query.strip().lower()
    matches = []
    for p in products:
        if (query_lower in p["name"].lower() or
                query_lower in p["category"].lower()):
            matches.append(p)

    if not matches:
        return f"No products found matching '{query}'. Try searching by name or category, or use 'all' to see everything."

    lines = []
    for p in matches:
        lines.append(
            f"- {p['name']} (ID: {p['product_id']}) | "
            f"Price: ₹{p['price']} | "
            f"In Stock: {p['quantity']} | "
            f"Category: {p['category']}"
        )
    return f"Found {len(matches)} product(s):\n" + "\n".join(lines)


@tool
def prepare_order(product_name: str, quantity: int = 1) -> str:
    """Prepare a pending order for a product. This does NOT finalize the order —
    the user must confirm it first.

    Use this tool when the user wants to buy/order a product.

    Args:
        product_name: The name (or partial name) of the product to order.
        quantity: How many units to order. Defaults to 1.
    """
    products = _get_products_ref()

    if quantity <= 0:
        return "Error: Quantity must be at least 1."

    # Find the product by fuzzy name match
    name_lower = product_name.strip().lower()
    matched_product = None
    for p in products:
        if name_lower in p["name"].lower():
            matched_product = p
            break

    if not matched_product:
        return f"Error: No product found matching '{product_name}'. Please check the product name and try again."

    if matched_product["quantity"] < quantity:
        return (
            f"Error: Not enough stock for {matched_product['name']}. "
            f"Requested: {quantity}, Available: {matched_product['quantity']}."
        )

    # Build the pending order (NOT yet placed)
    total_price = matched_product["price"] * quantity
    pending = {
        "product_id": matched_product["product_id"],
        "product_name": matched_product["name"],
        "quantity": quantity,
        "unit_price": matched_product["price"],
        "total_price": total_price,
    }

    # Return a structured string — the graph node will parse this and set pending_order
    return (
        f"PENDING_ORDER|"
        f"{pending['product_id']}|"
        f"{pending['product_name']}|"
        f"{pending['quantity']}|"
        f"{pending['unit_price']}|"
        f"{pending['total_price']}"
    )


# All tools available to the agent
all_tools = [get_product_info, prepare_order]

