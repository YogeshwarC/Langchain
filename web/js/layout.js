// layout.js
// Handles the 3-column draggable layout logic

document.addEventListener('DOMContentLoaded', () => {
    const grid = document.getElementById('workspace-grid');

    // Initialize SortableJS
    // We allow sorting of the columns within the main grid
    new Sortable(grid, {
        animation: 150,
        handle: '.drag-handle', // Restrict drag to header
        ghostClass: 'sortable-ghost',
        dragClass: 'sortable-drag',
        easing: "cubic-bezier(1, 0, 0, 1)",
        onEnd: function (evt) {
            // Optional: Save new order to functionality (localStorage)
            console.log('Layout reordered');
        }
    });

    // Handle Textarea Auto-resize
    const textarea = document.getElementById('user-input');
    textarea.addEventListener('input', function () {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
        if (this.value === '') this.style.height = 'auto';
    });
});
