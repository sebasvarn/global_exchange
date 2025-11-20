// ui-helpers.js
// Funciones comunes de UI para simuladores y otras páginas

// Actualiza el reloj en vivo en la interfaz (si existe el elemento)
function updateTime() {
    const now = new Date();
    const timeString = now.toLocaleTimeString();
    const dateString = now.toLocaleDateString();
    const timeElement = document.getElementById('current-time');
    if (timeElement) timeElement.textContent = `${dateString} ${timeString}`;
}
setInterval(updateTime, 1000);
updateTime();

// Efecto visual para botones de acciones rápidas
function setupQuickActionCards() {
    const quickActionCards = document.querySelectorAll('.btn-outline-primary, .btn-outline-info, .btn-outline-success, .btn-outline-warning');
    quickActionCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-2px)';
            this.style.boxShadow = '0 4px 8px rgba(0,0,0,0.1)';
        });
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
            this.style.boxShadow = 'none';
        });
    });
}

// ===== Animación para las tarjetas de estadísticas =====
const cards = document.querySelectorAll('.card');
cards.forEach((card, index) => {
    card.style.opacity = '0';
    card.style.transform = 'translateY(20px)';
    setTimeout(() => {
    card.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
    card.style.opacity = '1';
    card.style.transform = 'translateY(0)';
    }, index * 100);
});
// Ejecutar al cargar el DOM
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setupQuickActionCards);
} else {
    setupQuickActionCards();
}
