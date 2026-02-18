/**
 * Aquilia CRM — Client-side Utilities
 * Toast notifications, form helpers, and AJAX utilities
 */

// ---- Toast Notifications ----
function showToast(message, type = 'info', duration = 3000) {
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.style.borderLeft = `3px solid var(--${type === 'error' ? 'danger' : type === 'success' ? 'success' : 'accent'})`;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(20px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// ---- Confirm Delete ----
function confirmDelete(entityName, deleteUrl, redirectUrl) {
    if (!confirm(`Are you sure you want to delete this ${entityName}?`)) return;
    apiCall(deleteUrl, 'DELETE').then(res => {
        if (res.ok) {
            showToast(`${entityName} deleted`, 'success');
            setTimeout(() => window.location = redirectUrl, 500);
        } else {
            showToast(res.data.message || 'Delete failed', 'error');
        }
    });
}

// ---- Debounce utility ----
function debounce(fn, delay = 300) {
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => fn(...args), delay);
    };
}

// ---- Responsive sidebar ----
(function() {
    const mq = window.matchMedia('(max-width: 768px)');
    const toggle = document.getElementById('menuToggle');
    if (mq.matches && toggle) toggle.style.display = 'block';
    mq.addEventListener('change', e => {
        if (toggle) toggle.style.display = e.matches ? 'block' : 'none';
    });
})();
