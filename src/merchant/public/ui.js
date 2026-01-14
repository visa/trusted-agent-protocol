import van from 'https://cdn.jsdelivr.net/npm/vanjs-core/+esm'

const { div, h2, p, button } = van.tags;

const ProductCard = (product) => {
    return div({ class: "product-card" },
        h2(product.name),
        p(product.description),
        p({ class: "price" }, "$" + product.price.toFixed(2)),
        button({ onclick: () => alert("Added " + product.name) }, "Add to Cart")
    );
};

const App = () => {
    const container = div("Loading products...");

    fetch('/api/products')
        .then(res => {
            if (!res.ok) throw new Error("Failed to fetch products");
            return res.json();
        })
        .then(products => {
            container.innerHTML = "";
            van.add(container, products.map(ProductCard));
        })
        .catch(e => {
            container.innerHTML = "";
            van.add(container, div({ style: "color: red" }, "Error loading products: " + e.message));
        });

    return container;
};

// Mount
const root = document.getElementById("app");
root.innerHTML = "";
van.add(root, App());