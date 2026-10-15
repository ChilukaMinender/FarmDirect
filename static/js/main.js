document.addEventListener("DOMContentLoaded", () => {
    const searchInput = document.getElementById("productSearch");
    const productCards = [...document.querySelectorAll(".product-card")];
    const categoryButtons = [...document.querySelectorAll(".category-card")];
    const noResults = document.getElementById("noResults");

    let selectedCategory = "";

    function filterProducts() {
        const query = searchInput.value.trim().toLowerCase();
        let visibleCount = 0;

        productCards.forEach(card => {
            const name = card.dataset.name || "";
            const category = card.dataset.category || "";

            const matchesName = name.includes(query);
            const matchesCategory =
                !selectedCategory || category === selectedCategory;

            const visible = matchesName && matchesCategory;

            card.hidden = !visible;

            if (visible) visibleCount++;
        });

        noResults.hidden = visibleCount > 0;
    }

    searchInput.addEventListener("input", filterProducts);

    categoryButtons.forEach(button => {
        button.addEventListener("click", () => {
            const category = button.dataset.category;

            selectedCategory =
                selectedCategory === category ? "" : category;

            categoryButtons.forEach(item => {
                item.classList.toggle(
                    "active",
                    item.dataset.category === selectedCategory
                );
            });

            filterProducts();

            document.getElementById("products").scrollIntoView({
                behavior: "smooth"
            });
        });
    });
});

let toastTimer;

function showProductMessage(productName) {
    const toast = document.getElementById("toast");

    toast.textContent =
        `${productName} selected. Product details and ordering are coming next.`;

    toast.classList.add("show");

    clearTimeout(toastTimer);

    toastTimer = setTimeout(() => {
        toast.classList.remove("show");
    }, 3000);
}