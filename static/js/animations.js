document.addEventListener('DOMContentLoaded', function() {
    // Анимация карточек
    const cards = document.querySelectorAll('.card');
    cards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.animation = 'fadeIn 0.8s ease-out forwards';
        card.style.animationDelay = `${index * 0.15}s`;
    });
    
    // Эффекты при наведении
    const hoverElements = document.querySelectorAll('.hover-effect');
    hoverElements.forEach(el => {
        el.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-3px)';
        });
        el.addEventListener('mouseleave', function() {
            this.style.transform = '';
        });
    });
});