// Enterprise ATS Client Script Manager

document.addEventListener('DOMContentLoaded', function() {
    // 0. MOBILE SIDEBAR TOGGLE SYSTEM
    const sidebarWrapper = document.getElementById('sidebarWrapper');
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebarClose = document.getElementById('sidebarClose');
    const sidebarOverlay = document.getElementById('sidebarOverlay');

    function openSidebar() {
        if (sidebarWrapper) sidebarWrapper.classList.add('sidebar-show');
        if (sidebarOverlay) sidebarOverlay.classList.add('active');
        document.body.style.overflow = 'hidden';
    }

    function closeSidebar() {
        if (sidebarWrapper) sidebarWrapper.classList.remove('sidebar-show');
        if (sidebarOverlay) sidebarOverlay.classList.remove('active');
        document.body.style.overflow = '';
    }

    if (sidebarToggle) sidebarToggle.addEventListener('click', openSidebar);
    if (sidebarClose) sidebarClose.addEventListener('click', closeSidebar);
    if (sidebarOverlay) sidebarOverlay.addEventListener('click', closeSidebar);

    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeSidebar();
        }
    });

    window.addEventListener('resize', function() {
        if (window.innerWidth >= 768) {
            closeSidebar();
        }
    });

    // 1. THEME SELECTION SYSTEM
    const themeDots = document.querySelectorAll('.theme-dot, .theme-dot-select');
    
    themeDots.forEach(dot => {
        dot.addEventListener('click', function(e) {
            e.preventDefault();
            const theme = this.getAttribute('data-theme');
            setTheme(theme);
        });
    });

    function setTheme(themeName) {
        // Remove existing theme classes
        document.body.className = '';
        
        // Add new theme class
        document.body.classList.add(themeName);
        
        // Update active class on dots
        themeDots.forEach(dot => {
            if (dot.getAttribute('data-theme') === themeName) {
                dot.classList.add('active');
            } else {
                dot.classList.remove('active');
            }
        });
        
        // Sync with backend
        fetch('/save-theme', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ theme: themeName })
        })
        .then(response => response.json())
        .catch(() => console.log('Theme saved locally.'));
    }

    // 2. DARK MODE TOGGLE
    const darkModeBtn = document.getElementById('darkModeToggle');
    if (darkModeBtn) {
        darkModeBtn.addEventListener('click', function() {
            fetch('/toggle-dark-mode', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    // Instantly set body theme and classes
                    document.body.className = '';
                    document.body.classList.add(data.theme);
                    
                    // Switch icon state
                    const icon = darkModeBtn.querySelector('i');
                    if (data.dark_mode) {
                        icon.className = 'fa-solid fa-sun';
                        darkModeBtn.title = 'Switch to Light Mode';
                    } else {
                        icon.className = 'fa-solid fa-moon';
                        darkModeBtn.title = 'Switch to Dark Mode';
                    }
                    
                    // Update active dot indicators
                    themeDots.forEach(dot => {
                        if (dot.getAttribute('data-theme') === data.theme) {
                            dot.classList.add('active');
                        } else {
                            dot.classList.remove('active');
                        }
                    });
                    
                    showToast('success', 'Theme preference updated.');
                }
            })
            .catch(() => showToast('danger', 'Failed to toggle dark mode.'));
        });
    }

    // 3. DRAG AND DROP RESUME UPLOAD
    const dropzone = document.getElementById('uploadDropzone');
    const fileInput = document.getElementById('resumeFile');
    const uploadForm = document.getElementById('uploadForm');

    if (dropzone && fileInput) {
        dropzone.addEventListener('click', () => fileInput.click());

        ['dragenter', 'dragover'].forEach(eventName => {
            dropzone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropzone.classList.add('dragover');
            }, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropzone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropzone.classList.remove('dragover');
            }, false);
        });

        dropzone.addEventListener('drop', (e) => {
            const dt = e.dataTransfer;
            const files = dt.files;
            if (files.length) {
                fileInput.files = files;
                handleFileSelection(files[0]);
            }
        });

        fileInput.addEventListener('change', function() {
            if (this.files.length) {
                handleFileSelection(this.files[0]);
            }
        });
    }

    function handleFileSelection(file) {
        const allowedExtensions = /(\.pdf|\.docx)$/i;
        const maxSize = 5 * 1024 * 1024;
        
        const fileNameElement = document.getElementById('selectedFileName');
        const errorElement = document.getElementById('uploadError');
        const submitBtn = document.getElementById('submitUploadBtn');
        
        if (errorElement) errorElement.classList.add('d-none');
        if (fileNameElement) fileNameElement.textContent = '';
        if (submitBtn) submitBtn.disabled = true;

        if (!allowedExtensions.exec(file.name)) {
            if (errorElement) {
                errorElement.textContent = 'Invalid file format. Only PDF and DOCX files are allowed.';
                errorElement.classList.remove('d-none');
            }
            return;
        }

        if (file.size > maxSize) {
            if (errorElement) {
                errorElement.textContent = 'Maximum upload size is 5MB.';
                errorElement.classList.remove('d-none');
            }
            return;
        }

        if (fileNameElement) {
            fileNameElement.textContent = `Selected: ${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`;
        }
        if (submitBtn) {
            submitBtn.disabled = false;
        }
    }

    if (uploadForm) {
        uploadForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const file = fileInput.files[0];
            if (!file) return;

            const formData = new FormData(uploadForm);
            const xhr = new XMLHttpRequest();
            
            const progressContainer = document.getElementById('progressContainer');
            const progressBar = document.getElementById('progressBar');
            const progressPercent = document.getElementById('progressPercent');
            const submitBtn = document.getElementById('submitUploadBtn');

            if (progressContainer) progressContainer.classList.remove('d-none');
            if (submitBtn) submitBtn.disabled = true;

            xhr.upload.addEventListener('progress', function(e) {
                if (e.lengthComputable) {
                    const percentComplete = Math.round((e.loaded / e.total) * 100);
                    if (progressBar) progressBar.style.width = percentComplete + '%';
                    if (progressPercent) progressPercent.textContent = percentComplete + '%';
                }
            });

            xhr.addEventListener('load', function() {
                if (xhr.status === 200) {
                    const res = JSON.parse(xhr.responseText);
                    if (res.success) {
                        if (progressPercent) progressPercent.innerHTML = '✅ Processing complete! Redirecting...';
                        setTimeout(() => {
                            window.location.href = res.redirect || '/candidate';
                        }, 1200);
                    } else {
                        showToast('danger', res.error || 'Upload failed.');
                        if (submitBtn) submitBtn.disabled = false;
                    }
                } else {
                    showToast('danger', 'An error occurred during upload.');
                    if (submitBtn) submitBtn.disabled = false;
                }
            });

            xhr.open('POST', uploadForm.action, true);
            xhr.send(formData);
        });
    }

    // 4. ADVANCED MULTI-PARAMETER SEARCH & FILTER DRAWER
    const gSearch = document.getElementById('globalSearch');
    const roleFil = document.getElementById('roleFilter');
    const scoreFil = document.getElementById('scoreFilter');
    const statusFil = document.getElementById('statusFilter');
    const expFil = document.getElementById('experienceFilter');
    
    if (gSearch || roleFil || scoreFil || statusFil || expFil) {
        const triggerScreenFilter = () => {
            const query = gSearch ? gSearch.value.toLowerCase() : '';
            const role = roleFil ? roleFil.value.toLowerCase() : '';
            const scoreRange = scoreFil ? scoreFil.value : '';
            const status = statusFil ? statusFil.value.toLowerCase() : '';
            const exp = expFil ? expFil.value : '';
            
            const rows = document.querySelectorAll('.candidate-row');
            
            rows.forEach(row => {
                const rName = row.getAttribute('data-name').toLowerCase();
                const rEmail = row.getAttribute('data-email').toLowerCase();
                const rRole = row.getAttribute('data-role').toLowerCase();
                const rScore = parseFloat(row.getAttribute('data-score')) || 0;
                const rStatus = row.getAttribute('data-status') ? row.getAttribute('data-status').toLowerCase() : '';
                const rExp = parseFloat(row.getAttribute('data-experience')) || 0;
                
                let matchSearch = rName.includes(query) || rEmail.includes(query);
                let matchRole = role === '' || rRole === role;
                let matchStatus = status === '' || rStatus === status;
                
                let matchScore = true;
                if (scoreRange !== '') {
                    const [min, max] = scoreRange.split('-').map(Number);
                    if (max) {
                        matchScore = rScore >= min && rScore <= max;
                    } else {
                        matchScore = rScore >= min;
                    }
                }
                
                let matchExp = true;
                if (exp !== '') {
                    const [min, max] = exp.split('-').map(Number);
                    if (max) {
                        matchExp = rExp >= min && rExp <= max;
                    } else {
                        matchExp = rExp >= min;
                    }
                }
                
                if (matchSearch && matchRole && matchStatus && matchScore && matchExp) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        };

        [gSearch, roleFil, scoreFil, statusFil, expFil].forEach(el => {
            if (el) el.addEventListener('input', triggerScreenFilter);
            if (el) el.addEventListener('change', triggerScreenFilter);
        });
    }

    // 5. GLOBAL NAVBAR SEARCH FILTER
    const navSearch = document.getElementById('globalNavSearch');
    if (navSearch) {
        navSearch.addEventListener('input', function() {
            const query = this.value.trim().toLowerCase();
            const items = document.querySelectorAll('.candidate-row, .job-card, .notif-item');
            if (items.length > 0) {
                items.forEach(item => {
                    const text = item.innerText.toLowerCase();
                    if (!query || text.includes(query)) {
                        item.style.display = '';
                    } else {
                        item.style.display = 'none';
                    }
                });
            }
        });
    }
});

// Toast system
function showToast(type, message) {
    const container = document.getElementById('toastContainer');
    if (!container) return;
    
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0 show animate-fade-in`;
    toast.role = 'alert';
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}
