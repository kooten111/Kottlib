export function tooltip(node, { content, placement = 'right' }) {
    let tooltipComponent;

    function handleMouseOver(event) {
        if (!content) return;

        // Create tooltip element
        tooltipComponent = document.createElement('div');
        tooltipComponent.textContent = content;
        tooltipComponent.className = 'fixed-tooltip';
        document.body.appendChild(tooltipComponent);

        // Position it
        updatePosition();

        // Add event listener to update position or handle removal
        node.addEventListener('mousemove', updatePosition);
        node.addEventListener('mouseleave', handleMouseLeave);
    }

    function handleMouseLeave() {
        if (tooltipComponent) {
            tooltipComponent.remove();
            tooltipComponent = null;
        }
        node.removeEventListener('mousemove', updatePosition);
        node.removeEventListener('mouseleave', handleMouseLeave);
    }

    function updatePosition(event) {
        if (!tooltipComponent) return;

        const rect = node.getBoundingClientRect();
        // Default to right side
        let top = rect.top + (rect.height / 2) - (tooltipComponent.offsetHeight / 2);
        let left = rect.right + 10;

        // Boundary checks (basic)
        if (left + tooltipComponent.offsetWidth > window.innerWidth) {
            left = rect.left - tooltipComponent.offsetWidth - 10;
        }

        // Prevent going off-screen vertically
        if (top < 0) top = 10;
        if (top + tooltipComponent.offsetHeight > window.innerHeight) top = window.innerHeight - tooltipComponent.offsetHeight - 10;

        tooltipComponent.style.top = `${top}px`;
        tooltipComponent.style.left = `${left}px`;
    }

    node.addEventListener('mouseenter', handleMouseOver);

    return {
        update({ content: newContent }) {
            content = newContent;
            if (tooltipComponent) {
                tooltipComponent.textContent = content;
            }
        },
        destroy() {
            if (tooltipComponent) {
                tooltipComponent.remove();
            }
            node.removeEventListener('mouseenter', handleMouseOver);
            node.removeEventListener('mouseleave', handleMouseLeave);
            node.removeEventListener('mousemove', updatePosition);
        }
    };
}
