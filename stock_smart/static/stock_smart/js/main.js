function showToast(title, message) {
    // Implementar según necesidad
    console.log(`${title}: ${message}`);
}

function updateCartCounter(count) {
    const counter = document.getElementById('cart-counter');
    if (counter) {
        counter.textContent = count;
    }
}