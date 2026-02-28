// DonxEra - Custom JavaScript

// Show alert function
function showAlert(message, type = 'info') {
    const alertsContainer = document.getElementById('alerts');
    const alertId = 'alert-' + Date.now();
    const alertHtml = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert" id="${alertId}">
            <i class="bi bi-${getAlertIcon(type)}"></i> ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;
    alertsContainer.innerHTML = alertHtml;
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        const alertElement = document.getElementById(alertId);
        if (alertElement) {
            const alert = new bootstrap.Alert(alertElement);
            alert.close();
        }
    }, 5000);
}

function getAlertIcon(type) {
    const icons = {
        'success': 'check-circle-fill',
        'danger': 'exclamation-triangle-fill',
        'warning': 'exclamation-circle-fill',
        'info': 'info-circle-fill'
    };
    return icons[type] || 'info-circle-fill';
}

// Sync inventory function
function syncInventory() {
    showAlert('Starting inventory sync...', 'info');
    
    fetch('/sync', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            showAlert('Inventory sync completed successfully!', 'success');
            setTimeout(() => window.location.reload(), 2000);
        } else {
            showAlert('Sync failed: ' + data.message, 'danger');
        }
    })
    .catch(error => {
        showAlert('Sync error: ' + error.message, 'danger');
    });
}

// Upload CSV function
function uploadCSV() {
    const fileInput = document.getElementById('csvFile');
    const file = fileInput.files[0];
    
    if (!file) {
        showAlert('Please select a file to upload.', 'warning');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    showAlert('Uploading file...', 'info');
    
    fetch('/ingest-csv', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            showAlert('File uploaded and processed successfully!', 'success');
            bootstrap.Modal.getInstance(document.getElementById('uploadModal')).hide();
            fileInput.value = '';
            setTimeout(() => window.location.reload(), 2000);
        } else {
            showAlert('Upload failed: ' + data.message, 'danger');
        }
    })
    .catch(error => {
        showAlert('Upload error: ' + error.message, 'danger');
    });
}

// Animated number counter
function animateNumber(element, target) {
    const duration = 1500;
    const start = 0;
    const increment = target / (duration / 16);
    let current = start;
    
    const timer = setInterval(() => {
        current += increment;
        if (current >= target) {
            element.textContent = Math.round(target);
            clearInterval(timer);
        } else {
            element.textContent = Math.round(current);
        }
    }, 16);
}

// Initialize number animations on page load
document.addEventListener('DOMContentLoaded', () => {
    const metricNumbers = document.querySelectorAll('.card-title.mb-0');
    metricNumbers.forEach(element => {
        const target = parseInt(element.textContent) || 0;
        element.textContent = '0';
        animateNumber(element, target);
    });
    
    // Add fade-in to cards
    const cards = document.querySelectorAll('.card');
    cards.forEach((card, index) => {
        card.style.opacity = '0';
        setTimeout(() => {
            card.style.transition = 'opacity 0.6s ease';
            card.style.opacity = '1';
        }, index * 100);
    });
});

// Export inventory to CSV
function exportInventory() {
    window.location.href = '/export-inventory';
    showAlert('Exporting inventory...', 'info');
}

// Export low stock to CSV
function exportLowStock() {
    window.location.href = '/export-low-stock';
    showAlert('Exporting low stock items...', 'info');
}

// Table sorting with animation
let sortDirection = {};

function sortTable(table, column, dataType = 'text') {
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    // Toggle sort direction
    if (!sortDirection[column]) sortDirection[column] = 'asc';
    else sortDirection[column] = sortDirection[column] === 'asc' ? 'desc' : 'asc';
    
    rows.sort((a, b) => {
        let aVal = a.querySelector(`[data-column="${column}"]`)?.textContent || a.cells[getColumnIndex(table, column)]?.textContent || '';
        let bVal = b.querySelector(`[data-column="${column}"]`)?.textContent || b.cells[getColumnIndex(table, column)]?.textContent || '';
        
        if (dataType === 'number') {
            aVal = parseFloat(aVal.replace(/[^0-9.-]/g, '')) || 0;
            bVal = parseFloat(bVal.replace(/[^0-9.-]/g, '')) || 0;
        }
        
        if (sortDirection[column] === 'asc') {
            return aVal > bVal ? 1 : -1;
        } else {
            return aVal < bVal ? 1 : -1;
        }
    });
    
    // Animate row reordering
    rows.forEach((row, index) => {
        row.style.transition = 'transform 0.3s ease';
        tbody.appendChild(row);
    });
}

function getColumnIndex(table, column) {
    const headers = table.querySelectorAll('thead th');
    for (let i = 0; i < headers.length; i++) {
        if (headers[i].getAttribute('data-column') === column) {
            return i;
        }
    }
    return 0;
}

// Search functionality with highlight
function searchTable(searchInput, table) {
    const filter = searchInput.value.toUpperCase();
    const tbody = table.querySelector('tbody');
    const rows = tbody.querySelectorAll('tr');
    
    rows.forEach(row => {
        const text = row.textContent.toUpperCase();
        if (text.indexOf(filter) > -1) {
            row.style.display = '';
            row.style.animation = 'fadeIn 0.3s ease';
        } else {
            row.style.display = 'none';
        }
    });
}

// Filter functionality
function filterTable(filterValue, table, attribute) {
    const tbody = table.querySelector('tbody');
    const rows = tbody.querySelectorAll('tr');
    
    rows.forEach(row => {
        if (!filterValue) {
            row.style.display = '';
            return;
        }
        
        const value = row.getAttribute(attribute);
        if (value === filterValue || filterValue === 'all') {
            row.style.display = '';
            row.style.animation = 'fadeIn 0.3s ease';
        } else {
            row.style.display = 'none';
        }
    });
}

// Smooth scroll to top
function scrollToTop() {
    window.scrollTo({
        top: 0,
        behavior: 'smooth'
    });
}

// Add scroll to top button
document.addEventListener('DOMContentLoaded', () => {
    const scrollBtn = document.createElement('button');
    scrollBtn.innerHTML = '<i class="bi bi-arrow-up"></i>';
    scrollBtn.className = 'btn btn-primary position-fixed bottom-0 end-0 m-4 rounded-circle';
    scrollBtn.style.width = '50px';
    scrollBtn.style.height = '50px';
    scrollBtn.style.display = 'none';
    scrollBtn.style.zIndex = '1000';
    scrollBtn.onclick = scrollToTop;
    document.body.appendChild(scrollBtn);
    
    window.addEventListener('scroll', () => {
        if (window.pageYOffset > 300) {
            scrollBtn.style.display = 'block';
            scrollBtn.style.animation = 'fadeIn 0.3s ease';
        } else {
            scrollBtn.style.display = 'none';
        }
    });
});
