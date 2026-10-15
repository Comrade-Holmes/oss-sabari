// AllerGraph Interactive UI Enhancements

document.addEventListener('DOMContentLoaded', () => {
    // 1. Initialize Lucide icons if loaded
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }

    // 2. Auto-dismiss toast notifications after 5 seconds
    const toasts = document.querySelectorAll('.toast');
    toasts.forEach(toast => {
        setTimeout(() => {
            toast.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100%)';
            setTimeout(() => toast.remove(), 400);
        }, 5000);
    });

    // 3. Global Confirmation Modals for Delete / Risky Actions
    const modalBackdrop = document.getElementById('confirmation-modal');
    const modalTitle = document.getElementById('modal-title');
    const modalMessage = document.getElementById('modal-message');
    const modalConfirmBtn = document.getElementById('modal-confirm-btn');
    const modalCancelBtn = document.getElementById('modal-cancel-btn');
    let pendingForm = null;

    document.querySelectorAll('[data-confirm]').forEach(el => {
        el.addEventListener('click', (e) => {
            e.preventDefault();
            const message = el.getAttribute('data-confirm') || 'Are you sure you want to proceed?';
            const title = el.getAttribute('data-confirm-title') || 'Confirm Action';
            
            if (modalBackdrop && modalTitle && modalMessage && modalConfirmBtn) {
                modalTitle.textContent = title;
                modalMessage.textContent = message;
                modalBackdrop.classList.add('active');
                
                if (el.tagName === 'BUTTON' && el.form) {
                    pendingForm = el.form;
                } else if (el.tagName === 'A') {
                    pendingForm = el.getAttribute('href');
                }
            } else {
                if (confirm(message)) {
                    if (el.tagName === 'BUTTON' && el.form) el.form.submit();
                    else if (el.tagName === 'A') window.location.href = el.getAttribute('href');
                }
            }
        });
    });

    if (modalCancelBtn) {
        modalCancelBtn.addEventListener('click', () => {
            if (modalBackdrop) modalBackdrop.classList.remove('active');
            pendingForm = null;
        });
    }

    if (modalConfirmBtn) {
        modalConfirmBtn.addEventListener('click', () => {
            if (modalBackdrop) modalBackdrop.classList.remove('active');
            if (pendingForm) {
                if (typeof pendingForm === 'string') {
                    window.location.href = pendingForm;
                } else {
                    pendingForm.submit();
                }
            }
        });
    }

    // 4. Form Submission Guard (prevent double clicks)
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', (e) => {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn && !submitBtn.hasAttribute('data-no-disable')) {
                submitBtn.disabled = true;
                const originalText = submitBtn.innerHTML;
                submitBtn.innerHTML = `
                    <svg class="animate-spin" style="width: 16px; height: 16px; display: inline-block; animation: spin 1s linear infinite;" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                        <circle cx="12" cy="12" r="10" stroke-width="4" stroke="currentColor" stroke-dasharray="32" stroke-linecap="round"></circle>
                    </svg>
                    <span>Processing...</span>
                `;
            }
        });
    });

    // 5. Global Search Bar Enter Handler
    const globalSearchInput = document.getElementById('global-search-input');
    if (globalSearchInput) {
        globalSearchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                const q = globalSearchInput.value.trim();
                if (q) {
                    window.location.href = `/search?q=${encodeURIComponent(q)}`;
                }
            }
        });
    }
});

// Toast dispatch helper for AJAX interactions
function showToast(message, type = 'success') {
    const container = document.querySelector('.toast-container') || (() => {
        const c = document.createElement('div');
        c.className = 'toast-container';
        document.body.appendChild(c);
        return c;
    })();

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <div style="font-size: 0.875rem; font-weight: 500;">${message}</div>
        <button class="toast-close" onclick="this.parentElement.remove()">&times;</button>
    `;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => toast.remove(), 400);
    }, 4500);
}
