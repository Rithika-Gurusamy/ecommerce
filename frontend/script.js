const API = "http://127.0.0.1:8000";

// ── Load & render products ──────────────────────────────────────
async function getProducts() {
    try {
        const response = await fetch(`${API}/products`);
        const products = await response.json();
        const container = document.getElementById("product-container");
        container.innerHTML = "";

        products.forEach(product => {
            const card = document.createElement("div");
            card.className = "product-card";
            card.id = `product-${product.product_id}`;

            card.innerHTML = `
                <img src="${API}${product.image_url}" alt="${product.name}">
                <h3>${product.name}</h3>
                <p class="price">₹${product.price}</p>
                <p class="stock">Available: ${product.quantity}</p>
                <div class="qty-row">
                    <label>Qty:</label>
                    <input type="number" min="1" max="${product.quantity}" value="1"
                           id="qty-${product.product_id}">
                </div>
                <button onclick="buyProduct(${product.product_id})">Buy Now</button>
            `;

            container.appendChild(card);
        });
    } catch (err) {
        console.error("Failed to load products:", err);
    }
}

// ── Place an order (POST /orders) ───────────────────────────────
async function buyProduct(productId) {
    const qtyInput = document.getElementById(`qty-${productId}`);
    const quantity = parseInt(qtyInput.value);

    if (!quantity || quantity <= 0) {
        alert("Please enter a valid quantity.");
        return;
    }

    try {
        const response = await fetch(`${API}/orders`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ product_id: productId, quantity: quantity })
        });

        if (!response.ok) {
            const err = await response.json();
            alert(`Order failed: ${err.detail}`);
            return;
        }

        const order = await response.json();
        alert(`✅ Order #${order.order_id} confirmed!\n${order.product_name} × ${order.quantity} = ₹${order.total_price}`);

        // Refresh products (stock changed) and orders
        getProducts();
        loadOrders();
    } catch (err) {
        console.error("Order error:", err);
        alert("Something went wrong placing the order.");
    }
}

// ── Load & render orders (GET /orders) ──────────────────────────
async function loadOrders() {
    try {
        const response = await fetch(`${API}/orders`);
        const orders = await response.json();
        const container = document.getElementById("orders-container");

        if (orders.length === 0) {
            container.innerHTML = '<p class="empty-msg">No orders yet.</p>';
            return;
        }

        container.innerHTML = "";

        orders.forEach(order => {
            const card = document.createElement("div");
            card.className = `order-card ${order.status}`;

            const cancelBtn = order.status === "confirmed"
                ? `<button class="cancel-btn" onclick="cancelOrder(${order.order_id})">Cancel Order</button>`
                : `<span class="cancelled-badge">Cancelled</span>`;

            card.innerHTML = `
                <h3>Order #${order.order_id}</h3>
                <p><strong>Product:</strong> ${order.product_name}</p>
                <p><strong>Quantity:</strong> ${order.quantity}</p>
                <p><strong>Total:</strong> ₹${order.total_price}</p>
                <p><strong>Status:</strong> ${order.status}</p>
                ${cancelBtn}
            `;

            container.appendChild(card);
        });
    } catch (err) {
        console.error("Failed to load orders:", err);
    }
}

// ── Cancel an order (POST /orders/cancel/{id}) ──────────────────
async function cancelOrder(orderId) {
    if (!confirm(`Cancel order #${orderId}?`)) return;

    try {
        const response = await fetch(`${API}/orders/cancel/${orderId}`, {
            method: "POST"
        });

        if (!response.ok) {
            const err = await response.json();
            alert(`Cancel failed: ${err.detail}`);
            return;
        }

        alert(`Order #${orderId} has been cancelled.`);
        getProducts();   // stock restored
        loadOrders();    // refresh order list
    } catch (err) {
        console.error("Cancel error:", err);
        alert("Something went wrong cancelling the order.");
    }
}

// ── Toggle between Products / Orders views ──────────────────────
function toggleOrders() {
    const productsSection = document.getElementById("products-section");
    const ordersSection = document.getElementById("orders-section");
    const btn = document.getElementById("toggle-orders-btn");

    if (ordersSection.classList.contains("hidden")) {
        ordersSection.classList.remove("hidden");
        productsSection.classList.add("hidden");
        btn.textContent = "Back to Products";
        loadOrders();
    } else {
        productsSection.classList.remove("hidden");
        ordersSection.classList.add("hidden");
        btn.textContent = "My Orders";
    }
}

// ── Init ─────────────────────────────────────────────────────────
getProducts();
