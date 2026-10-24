// FileGuard FIM - Main JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert:not(.alert-info):not(.alert-warning)');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // Sidebar toggle for mobile
    const sidebarToggle = document.querySelector('.navbar-toggler');
    const sidebar = document.getElementById('sidebarMenu');

    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', function() {
            sidebar.classList.toggle('show');
        });
    }

    // Confirm before destructive actions
    const deleteButtons = document.querySelectorAll('[data-confirm]');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirm(this.getAttribute('data-confirm'))) {
                e.preventDefault();
            }
        });
    });

    // Format file sizes
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    }

    // Add file size formatting to elements with data-filesize
    const fileSizeElements = document.querySelectorAll('[data-filesize]');
    fileSizeElements.forEach(el => {
        const bytes = parseInt(el.getAttribute('data-filesize'));
        el.textContent = formatFileSize(bytes);
    });

    // Relative time formatting
    function timeAgo(date) {
        const seconds = Math.floor((new Date() - date) / 1000);

        let interval = seconds / 31536000;
        if (interval > 1) return Math.floor(interval) + ' years ago';

        interval = seconds / 2592000;
        if (interval > 1) return Math.floor(interval) + ' months ago';

        interval = seconds / 86400;
        if (interval > 1) return Math.floor(interval) + ' days ago';

        interval = seconds / 3600;
        if (interval > 1) return Math.floor(interval) + ' hours ago';

        interval = seconds / 60;
        if (interval > 1) return Math.floor(interval) + ' minutes ago';

        return Math.floor(seconds) + ' seconds ago';
    }

    // Add relative time to elements with data-timestamp
    const timestampElements = document.querySelectorAll('[data-timestamp]');
    timestampElements.forEach(el => {
        const timestamp = new Date(el.getAttribute('data-timestamp'));
        el.setAttribute('title', timestamp.toLocaleString());
        el.textContent = timeAgo(timestamp);
    });

    // Refresh timestamps every minute
    setInterval(() => {
        timestampElements.forEach(el => {
            const timestamp = new Date(el.getAttribute('data-timestamp'));
            el.textContent = timeAgo(timestamp);
        });
    }, 60000);
});

// CSRF token helper for AJAX requests
function getCsrfToken() {
    const metaTag = document.querySelector('meta[name="csrf-token"]');
    return metaTag ? metaTag.getAttribute('content') : null;
}

// Auto-attach CSRF token to fetch requests
const _originalFetch = window.fetch;
window.fetch = function(url, options = {}) {
    const method = (options.method || 'GET').toUpperCase();
    if (['POST', 'PUT', 'DELETE', 'PATCH'].includes(method)) {
        options.headers = options.headers || {};
        const token = getCsrfToken();
        if (token) {
            if (options.headers instanceof Headers) {
                if (!options.headers.has('X-CSRFToken')) {
                    options.headers.append('X-CSRFToken', token);
                }
            } else if (!options.headers['X-CSRFToken'] && !options.headers['x-csrftoken']) {
                options.headers['X-CSRFToken'] = token;
            }
        }
    }
    return _originalFetch(url, options);
};

// Generic AJAX helper
async function apiRequest(url, method = 'GET', data = null) {
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json',
        },
    };

    const csrfToken = getCsrfToken();
    if (csrfToken) {
        options.headers['X-CSRFToken'] = csrfToken;
    }

    if (data) {
        options.body = JSON.stringify(data);
    }

    try {
        const response = await fetch(url, options);
        return await response.json();
    } catch (error) {
        console.error('API request failed:', error);
        throw error;
    }
}

// Show loading spinner
function showLoading(message = 'Processing...') {
    // Could implement a loading overlay here
    console.log('Loading:', message);
}

// Hide loading spinner
function hideLoading() {
    // Could hide the loading overlay here
    console.log('Loading complete');
}

// Toast notification helper (Bootstrap 5)
function showToast(message, type = 'info') {
    // This could be enhanced with actual Bootstrap toast component
    console.log(`[${type.toUpperCase()}]`, message);
}

console.log('FileGuard FIM initialized');
