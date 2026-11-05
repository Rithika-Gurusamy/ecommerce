const API = "http://127.0.0.1:8000";

// ═══════════════════════════════════════════════════════════════════
//  PRODUCT & ORDER LOGIC (existing)
// ═══════════════════════════════════════════════════════════════════

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

        getProducts();
        loadOrders();
    } catch (err) {
        console.error("Order error:", err);
        alert("Something went wrong placing the order.");
    }
}

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
        getProducts();
        loadOrders();
    } catch (err) {
        console.error("Cancel error:", err);
        alert("Something went wrong cancelling the order.");
    }
}

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


// ═══════════════════════════════════════════════════════════════════
//  CHAT WIDGET — Agent Frontend
// ═══════════════════════════════════════════════════════════════════

// Generate a unique session id per browser tab
const SESSION_ID = "session-" + Math.random().toString(36).substring(2, 10);

// ── Toggle chat open / close ────────────────────────────────────
function toggleChat() {
    const chatWindow = document.getElementById("chat-window");
    const fabIcon    = document.getElementById("chat-fab-icon");
    const fabClose   = document.getElementById("chat-fab-close");

    const isOpen = !chatWindow.classList.contains("hidden");

    if (isOpen) {
        chatWindow.classList.add("hidden");
        fabIcon.classList.remove("hidden");
        fabClose.classList.add("hidden");
    } else {
        chatWindow.classList.remove("hidden");
        fabIcon.classList.add("hidden");
        fabClose.classList.remove("hidden");
        document.getElementById("chat-input").focus();
    }
}

// ── Render a message bubble ─────────────────────────────────────
function addMessage(text, sender) {
    // sender: "user" | "bot"
    const container = document.getElementById("chat-messages");
    const bubble = document.createElement("div");
    bubble.className = `chat-bubble ${sender}`;

    // Support basic markdown-like bold (**text**) and newlines
    const formatted = text
        .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
        .replace(/\n/g, "<br>");

    bubble.innerHTML = formatted;
    container.appendChild(bubble);

    // Auto-scroll to bottom
    container.scrollTop = container.scrollHeight;
}

// ── Show / hide the typing indicator ────────────────────────────
function showTyping() {
    const container = document.getElementById("chat-messages");
    const indicator = document.createElement("div");
    indicator.className = "chat-bubble bot typing-indicator";
    indicator.id = "typing-indicator";
    indicator.innerHTML = '<span class="dot"></span><span class="dot"></span><span class="dot"></span>';
    container.appendChild(indicator);
    container.scrollTop = container.scrollHeight;
}

function hideTyping() {
    const el = document.getElementById("typing-indicator");
    if (el) el.remove();
}

// ── Send user message to agent ──────────────────────────────────
async function sendMessage() {
    const input = document.getElementById("chat-input");
    const text = input.value.trim();
    if (!text) return;

    // Show user bubble
    addMessage(text, "user");
    input.value = "";

    showTyping();

    try {
        const response = await fetch(`${API}/agent/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ session_id: SESSION_ID, message: text })
        });

        hideTyping();

        if (!response.ok) {
            const err = await response.json();
            addMessage(`⚠️ Error: ${err.detail || "Something went wrong."}`, "bot");
            return;
        }

        const data = await response.json();

        // Show the agent's response
        addMessage(data.response, "bot");

        // Immediately refresh products (stock) and orders (order list)
        getProducts();
        loadOrders();

    } catch (err) {
        hideTyping();
        console.error("Chat error:", err);
        addMessage("⚠️ Could not reach the assistant. Is the server running?", "bot");
    }
}


// ═══════════════════════════════════════════════════════════════════
//  INIT
// ═══════════════════════════════════════════════════════════════════

getProducts();

// Inject welcome message into chat
document.addEventListener("DOMContentLoaded", () => {
    addMessage(
        "👋 Hey there! I'm your **My Store** shopping assistant.\n\n" +
        "I can help you:\n" +
        "🔍 Browse products & check prices\n" +
        "🛒 Place orders for you\n\n" +
        "Just type a message below!",
        "bot"
    );
});
