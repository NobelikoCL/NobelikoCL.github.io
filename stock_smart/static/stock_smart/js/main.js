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

function addToCart(productId) {
    // Obtener el token CSRF
    const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;

    // Realizar la petición AJAX
    fetch('/add_to_cart/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken
        },
        body: JSON.stringify({
            'product_id': productId
        })
    })
    .then(response => response.json())
    .then(data => {
        if(data.success) {
            // Actualizar el contador del carrito
            document.getElementById('cart-count').textContent = data.cart_count;
            // Mostrar mensaje de éxito
            alert('Producto agregado al carrito');
        } else {
            alert('Error al agregar al carrito');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error al agregar al carrito');
    });
}