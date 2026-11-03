async function getProducts() {

    const response = await fetch("http://127.0.0.1:8000/products");

    const products = await response.json();

    const container = document.getElementById("product-container");

    products.forEach(product => {

        const card = document.createElement("div");

        card.className = "product-card";

        card.innerHTML = `
            <img src="http://127.0.0.1:8000${product.image_url}" 
                 alt="${product.name}">

            <h3>${product.name}</h3>

            <p class="price">₹${product.price}</p>

            <p>Available: ${product.quantity}</p>

            <button>Buy Now</button>
        `;

        container.appendChild(card);

    });
}

getProducts();