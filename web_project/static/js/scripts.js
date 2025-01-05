// static/js/scripts.js

// Example: Confirmation before deleting a user
document.addEventListener('DOMContentLoaded', function() {
    const deleteButtons = document.querySelectorAll('.delete-button');
    deleteButtons.forEach(function(button) {
        button.addEventListener('click', function(event) {
            const confirmDeletion = confirm('Вы уверены, что хотите удалить этого пользователя?');
            if (!confirmDeletion) {
                event.preventDefault();
            }
        });
    });
});
