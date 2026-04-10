name=static/js/booking.js

let currentStep = 1;
let selectedService = null;
let selectedServicePrice = null;
let bookingData = {};

document.addEventListener('DOMContentLoaded', () => {
    loadServices();
    setMinDate();
});

function setMinDate() {
    const dateInput = document.getElementById('date');
    const today = new Date().toISOString().split('T')[0];
    dateInput.min = today;
}

async function loadServices() {
    try {
        const response = await fetch('/api/services');
        const data = await response.json();
        if (data.success) displayServices(data.services);
    } catch (error) {
        console.error('Error:', error);
    }
}

function displayServices(services) {
    const container = document.getElementById('servicesContainer');
    container.innerHTML = '';
    services.forEach(service => {
        const div = document.createElement('div');
        div.className = 'service-option';
        div.innerHTML = `
            <div class="service-info">
                <h4>${service.name}</h4>
                <p>$${service.price} - ${service.duration} mins</p>
            </div>
            <input type="radio" name="service" value="${service.id}" data-price="${service.price}" data-name="${service.name}">
        `;
        div.addEventListener('click', () => selectService(service.id, service.price, service.name));
        container.appendChild(div);
    });
}

function selectService(serviceId, price, name) {
    selectedService = serviceId;
    selectedServicePrice = price;
    bookingData.serviceName = name;
}

document.getElementById('date')?.addEventListener('change', function() {
    loadAvailableSlots(this.value);
});

async function loadAvailableSlots(date) {
    if (!selectedService || !date) return;
    try {
        const response = await fetch(`/api/available-slots?date=${date}&service_id=${selectedService}`);
        const data = await response.json();
        if (data.success) displaySlots(data.slots);
    } catch (error) {
        console.error('Error:', error);
    }
}

function displaySlots(slots) {
    const select = document.getElementById('time');
    select.innerHTML = '<option value="">-- Select --</option>';
    slots.forEach(slot => {
        const option = document.createElement('option');
        option.value = slot;
        option.textContent = slot;
        select.appendChild(option);
    });
}

document.getElementById('nextBtn')?.addEventListener('click', () => {
    if (validateStep()) nextStep();
});

document.getElementById('prevBtn')?.addEventListener('click', prevStep);

function validateStep() {
    if (currentStep === 1 && !selectedService) {
        showMessage('Select a service', 'error');
        return false;
    } else if (currentStep === 2) {
        const date = document.getElementById('date').value;
        const time = document.getElementById('time').value;
        if (!date || !time) {
            showMessage('Select date and time', 'error');
            return false;
        }
        bookingData.date = date;
        bookingData.time = time;
    }
    return true;
}

function nextStep() {
    if (currentStep < 3) {
        if (currentStep === 2) updateSummary();
        document.getElementById(`step${currentStep}`).style.display = 'none';
        currentStep++;
        document.getElementById(`step${currentStep}`).style.display = 'block';
        if (currentStep === 3) {
            document.getElementById('nextBtn').textContent = 'Confirm';
            document.getElementById('nextBtn').onclick = confirmBooking;
        }
        document.getElementById('prevBtn').style.display = 'block';
    }
}

function prevStep() {
    if (currentStep > 1) {
        document.getElementById(`step${currentStep}`).style.display = 'none';
        currentStep--;
        document.getElementById(`step${currentStep}`).style.display = 'block';
        if (currentStep === 1) {
            document.getElementById('prevBtn').style.display = 'none';
            document.getElementById('nextBtn').textContent = 'Next';
            document.getElementById('nextBtn').onclick = null;
        }
    }
}

function updateSummary() {
    document.getElementById('summaryService').textContent = bookingData.serviceName;
    document.getElementById('summaryDate').textContent = bookingData.date;
    document.getElementById('summaryTime').textContent = bookingData.time;
    document.getElementById('summaryPrice').textContent = selectedServicePrice;
}

async function confirmBooking() {
    const messageDiv = document.getElementById('message');
    try {
        const response = await fetch('/booking', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                service_id: selectedService,
                date: bookingData.date,
                time: bookingData.time
            })
        });
        const data = await response.json();
        if (data.success) {
            messageDiv.className = 'message success';
            messageDiv.textContent = data.message;
            setTimeout(() => window.location.href = data.redirect, 1500);
        } else {
            messageDiv.className = 'message error';
            messageDiv.textContent = data.message;
        }
    } catch (error) {
        messageDiv.className = 'message error';
        messageDiv.textContent = 'Error occurred';
    }
}

function showMessage(text, type) {
    const messageDiv = document.getElementById('message');
    messageDiv.className = `message ${type}`;
    messageDiv.textContent = text;
}