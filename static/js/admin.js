name=static/js/admin.js

document.addEventListener('DOMContentLoaded', () => {
    loadStatistics();
    loadBookings();
});

async function loadStatistics() {
    try {
        const response = await fetch('/api/admin/statistics');
        const data = await response.json();
        if (data.success) {
            document.getElementById('totalUsers').textContent = data.total_users;
            document.getElementById('totalBookings').textContent = data.total_bookings;
            document.getElementById('confirmedBookings').textContent = data.confirmed_bookings;
        }
    } catch (error) {
        console.error('Error:', error);
    }
}

async function loadBookings() {
    // Bookings are loaded from the template
    console.log('Bookings loaded from template');
}