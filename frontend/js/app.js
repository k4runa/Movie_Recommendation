/**
 * CineWave — Frontend Application (SPA)
 * 
 * A vanilla JavaScript single-page application that communicates with
 * the CineWave REST API.  No frameworks, no build step — just clean,
 * modular ES5+ code served as a static asset via FastAPI's StaticFiles.
 *
 * Architecture:
 *   • State is held in module-level variables (currentToken, currentUsername).
 *   • JWT tokens and the username are persisted to localStorage for session
 *     continuity across page reloads.
 *   • All API calls go through `fetchWithAuth()`, which injects the Bearer
 *     token and handles 401/403 by logging the user out.
 *   • Tab data is loaded lazily and cached via the `dataLoaded` flags to
 *     prevent redundant network requests and DOM flicker.
 *
 * Sections:
 *   1. State & DOM References
 *   2. Initialization & Event Binding
 *   3. UI State Toggles (Auth ↔ Dashboard)
 *   4. Authentication (Login / Register)
 *   5. API Helpers
 *   6. Data Fetching (Watched, Recommendations)
 *   7. Movie Actions (Track, Delete)
 *   7. Movie Actions (Track, Delete)
 *   8. Admin Panel (User List, Ban)
 */

/** Simple HTML escaping to prevent XSS when using .innerHTML */
const esc = (str) => {
    if (!str) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
};

const API_BASE = ''; // Same origin — no CORS needed

// 1. STATE & DOM REFERENCES

/** JWT access token — persisted to localStorage for session continuity. */
let currentToken = localStorage.getItem('access_token');

/** Authenticated username — used in API paths and UI greeting. */
let currentUsername = localStorage.getItem('username');

/** Tracks whether the auth form is in login (true) or register (false) mode. */
let isLoginMode = true;

/**
 * Cache flags for each tab's data.
 * When true, the tab's content is already rendered and won't re-fetch.
 * Invalidated on mutations (add/delete movie) to ensure fresh data.
 */
let dataLoaded = {
    watched: false,
    recs: false,
    admin: false,
    settings: false
};

/**
 * Centralized DOM element references.
 * Queried once at load time to avoid repeated getElementById calls.
 */
const el = {
    // Navigation
    navActions: document.getElementById('nav-actions'),
    userGreeting: document.getElementById('user-greeting'),
    btnLogout: document.getElementById('btn-logout'),
    btnRefresh: document.getElementById('btn-refresh'),
    
    // View containers
    viewAuth: document.getElementById('view-auth'),
    viewDashboard: document.getElementById('view-dashboard'),
    
    // Auth form
    authTitle: document.getElementById('auth-title'),
    authSubtitle: document.getElementById('auth-subtitle'),
    authForm: document.getElementById('auth-form'),
    usernameInput: document.getElementById('username'),
    emailGroup: document.getElementById('email-group'),
    emailInput: document.getElementById('email'),
    passwordInput: document.getElementById('password'),
    btnSubmit: document.getElementById('btn-submit'),
    authSwitchLink: document.getElementById('auth-switch-link'),
    authSwitchText: document.getElementById('auth-switch-text'),
    authError: document.getElementById('auth-error'),

    // Tab navigation
    tabBtns: document.querySelectorAll('.tab-btn'),
    tabContents: document.querySelectorAll('.tab-content'),
    
    // Watched movies tab
    watchedGrid: document.getElementById('watched-grid'),
    recsGrid: document.getElementById('recs-grid'),
    loadingWatched: document.getElementById('loading-watched'),
    loadingRecs: document.getElementById('loading-recs'),
    
    // Add movie tab
    addMovieForm: document.getElementById('add-movie-form'),
    movieQuery: document.getElementById('movie-query'),
    addMsg: document.getElementById('add-msg'),
    
    // Admin tab
    btnAdminTab: document.getElementById('btn-admin-tab'),
    loadingAdmin: document.getElementById('loading-admin'),
    adminUsersTbody: document.getElementById('admin-users-tbody'),

    // AI Components
    aiInsightsContainer: document.getElementById('ai-insights-container'),
    
    // Settings tab
    aiToggle: document.getElementById('ai-toggle'),
    formUpdateEmail: document.getElementById('form-update-email'),
    inputNewEmail: document.getElementById('input-new-email'),
    inputEmailVerifyPassword: document.getElementById('input-email-verify-password'),
    formUpdatePassword: document.getElementById('form-update-password'),
    inputPassCurrent: document.getElementById('input-pass-current'),
    inputNewPassword: document.getElementById('input-new-password'),
    inputNewPasswordConfirm: document.getElementById('input-new-password-confirm'),
    settingsMsg: document.getElementById('settings-msg'),
    
    // Settings Views
    btnGotoEmail: document.getElementById('btn-goto-email'),
    btnGotoPassword: document.getElementById('btn-goto-password'),
    settingsViews: document.querySelectorAll('.settings-view'),
    msgEmail: document.getElementById('msg-email'),
    msgPassword: document.getElementById('msg-password'),
    msgUsername: document.getElementById('msg-username'),
    inputMaxToasts: document.getElementById('input-max-toasts'),
    formUpdateUsername: document.getElementById('form-update-username'),
    inputNewUsername: document.getElementById('input-new-username'),
    inputUsernameVerifyPassword: document.getElementById('input-username-verify-password'),
};


// 2. INITIALIZATION & EVENT BINDING

/**
 * Bootstrap the application.
 * Checks localStorage for an existing session and routes to
 * either the dashboard or the auth form accordingly.
 */
function init() {
    if (currentToken && currentUsername) {
        showDashboard();
    } else {
        showAuth();
    }
    attachListeners();
}

/**
 * Bind all event listeners.
 * Called once during init — delegates tab clicks, form submissions,
 * and the auth mode toggle.
 */
function attachListeners() {
    el.authSwitchLink.addEventListener('click', toggleAuthMode);
    el.authForm.addEventListener('submit', handleAuthSubmit);
    el.btnLogout.addEventListener('click', logout);
    
    el.tabBtns.forEach(btn => {
        btn.addEventListener('click', () => switchTab(btn.dataset.target));
    });
    
    el.addMovieForm.addEventListener('submit', handleAddMovie);
    
    if(el.aiToggle) {
        el.aiToggle.addEventListener('change', handleToggleAI);
    }
    
    if(el.btnRefresh) {
        el.btnRefresh.addEventListener('click', handleRefresh);
    }

    if(el.formUpdateEmail) {
        el.formUpdateEmail.addEventListener('submit', handleUpdateEmail);
    }

    if(el.formUpdatePassword) {
        el.formUpdatePassword.addEventListener('submit', handleUpdatePassword);
    }
    if(el.formUpdateUsername) {
        el.formUpdateUsername.addEventListener('submit', handleUpdateUsername);
    }
    if(el.inputMaxToasts) {
        el.inputMaxToasts.addEventListener('change', handleUpdateMaxToasts);
    }

    if(el.btnGotoEmail) el.btnGotoEmail.addEventListener('click', () => showSettingsView('settings-email'));
    if(el.btnGotoPassword) el.btnGotoPassword.addEventListener('click', () => showSettingsView('settings-password'));
}

// 2.5 TOAST, CONFIRM & SETTINGS NAVIGATION LOGIC
window.showSettingsView = function(viewId) {
    el.settingsViews.forEach(v => v.classList.add('hidden'));
    const target = document.getElementById(viewId);
    if (target) target.classList.remove('hidden');
};

window.openSettingsModal = function(modalId) {
    const modal = document.getElementById(modalId);
    if (!modal) return;
    
    // Clear any previous messages
    if (el.msgEmail) { el.msgEmail.classList.add('hidden'); el.msgEmail.textContent = ''; }
    if (el.msgPassword) { el.msgPassword.classList.add('hidden'); el.msgPassword.textContent = ''; }
    if (el.msgUsername) { el.msgUsername.classList.add('hidden'); el.msgUsername.textContent = ''; }
    
    modal.classList.remove('hidden');
    const box = modal.querySelector('.modal-box');
    setTimeout(() => {
        modal.classList.add('show');
        if (box) box.classList.add('show');
    }, 10);
};

window.showMessage = function(element, text, type = 'error') {
    if (!element) return;
    element.textContent = text;
    element.className = `msgbox ${type}`;
    element.classList.remove('hidden');
};

window.closeSettingsModal = function(modalId) {
    const modal = document.getElementById(modalId);
    if (!modal) return;
    modal.classList.remove('show');
    const box = modal.querySelector('.modal-box');
    if (box) box.classList.remove('show');
    setTimeout(() => modal.classList.add('hidden'), 300);
};

window.showToast = function(message, type = 'success') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    // Apply max toasts limit
    const maxToasts = parseInt(localStorage.getItem('max_toasts')) || 5;
    while (container.children.length >= maxToasts) {
        container.removeChild(container.firstChild);
    }
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    let icon = 'info';
    if (type === 'success') icon = 'check-circle';
    if (type === 'error') icon = 'warning-circle';
    
    toast.innerHTML = `<i class="ph ph-${icon}" style="font-size: 1.25rem;"></i> <span>${esc(message)}</span>`;
    container.appendChild(toast);
    
    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 400);
    }, 3000);
};

window.showConfirm = function(message) {
    return new Promise((resolve) => {
        const overlay = document.createElement('div');
        overlay.className = 'modal-overlay';
        
        const modal = document.createElement('div');
        modal.className = 'modal-box';
        
        modal.innerHTML = `
            <div class="modal-icon"><i class="ph ph-warning-circle"></i></div>
            <p class="modal-msg">${esc(message)}</p>
            <div class="modal-actions">
                <button class="btn btn-outline" id="btn-cancel">Cancel</button>
                <button class="btn btn-danger" id="btn-confirm">Remove</button>
            </div>
        `;
        
        overlay.appendChild(modal);
        document.body.appendChild(overlay);
        
        // Trigger entrance animation
        setTimeout(() => {
            overlay.classList.add('show');
            modal.classList.add('show');
        }, 10);
        
        const closeModal = () => {
            overlay.classList.remove('show');
            modal.classList.remove('show');
            setTimeout(() => overlay.remove(), 300);
        };
        
        modal.querySelector('#btn-cancel').addEventListener('click', () => {
            closeModal();
            resolve(false);
        });
        
        modal.querySelector('#btn-confirm').addEventListener('click', () => {
            closeModal();
            resolve(true);
        });
    });
};

async function handleRefresh() {
    const icon = el.btnRefresh.querySelector('i');
    if(icon) icon.classList.add('spin');
    
    // Invalidate caches
    dataLoaded.watched = false;
    dataLoaded.recs = false;
    dataLoaded.admin = false;
    
    const activeTabBtn = document.querySelector('.dock-item.active');
    if (activeTabBtn) {
        const targetId = activeTabBtn.dataset.target;
        if (targetId === 'tab-watched') await loadWatchedMovies();
        if (targetId === 'tab-recommend') await loadRecommendations();
        if (targetId === 'tab-admin') await loadAdminUsers();
        if (targetId === 'tab-settings') await loadUserSettings();
    }
    
    if(icon) icon.classList.remove('spin');
    showToast("Data refreshed successfully", "success");
}


// 3. UI STATE TOGGLES

/** Show the authentication form and hide the dashboard. */
function showAuth() {
    el.viewAuth.classList.remove('hidden');
    el.viewDashboard.classList.add('hidden');
    el.navActions.classList.add('hidden');
}

/**
 * Show the dashboard and hide the auth form.
 * Also conditionally reveals the Admin tab if the user is 'admin'.
 */
function showDashboard() {
    el.viewAuth.classList.add('hidden');
    el.viewDashboard.classList.remove('hidden');
    el.navActions.classList.remove('hidden');
    el.userGreeting.innerText = `Hi, ${currentUsername}`;
    
    // Only the 'admin' user sees the admin panel tab
    if (currentUsername.toLowerCase() === 'admin') {
        el.btnAdminTab.classList.remove('hidden');
    } else {
        el.btnAdminTab.classList.add('hidden');
    }
    
    // Load the default tab's data
    loadWatchedMovies();
}

/**
 * Toggle the auth form between Login and Register modes.
 * Swaps the title, button text, and shows/hides the email field.
 */
function toggleAuthMode() {
    isLoginMode = !isLoginMode;
    el.authError.classList.add('hidden');
    
    if (isLoginMode) {
        el.authTitle.innerText = "Welcome Back";
        el.authSubtitle.innerText = "Enter your details to dive into your movies.";
        el.btnSubmit.innerText = "Sign In";
        el.emailGroup.classList.add('hidden');
        el.emailInput.removeAttribute('required');
        el.authSwitchText.innerHTML = `New to CineWave? <span id="auth-switch-link" class="gradient-text cursor-pointer">Create Account</span>`;
    } else {
        el.authTitle.innerText = "Join CineWave";
        el.authSubtitle.innerText = "Craft your personalized AI movie journey.";
        el.btnSubmit.innerText = "Sign Up";
        el.emailGroup.classList.remove('hidden');
        el.emailInput.setAttribute('required', 'true');
        el.authSwitchText.innerHTML = `Already have an account? <span id="auth-switch-link" class="gradient-text cursor-pointer">Sign In</span>`;
    }
    // Re-attach the listener since innerHTML replaced the element
    document.getElementById('auth-switch-link').addEventListener('click', toggleAuthMode);
}

/**
 * Switch the active dashboard tab and lazy-load its data.
 * Data is only fetched if it hasn't been loaded yet (cache flags).
 * 
 * @param {string} targetId — The DOM id of the tab section to activate.
 */
function switchTab(targetId) {
    // Update tab button active states
    el.tabBtns.forEach(btn => btn.classList.remove('active'));
    document.querySelector(`.tab-btn[data-target="${targetId}"]`).classList.add('active');
    
    // Show/hide tab content sections
    el.tabContents.forEach(content => content.classList.add('hidden'));
    document.getElementById(targetId).classList.remove('hidden');
    
    // Lazy-load data only when the cache is invalidated
    if (targetId === 'tab-watched' && !dataLoaded.watched) loadWatchedMovies();
    if (targetId === 'tab-recommend' && !dataLoaded.recs) loadRecommendations();
    if (targetId === 'tab-admin' && !dataLoaded.admin) loadAdminUsers();
    if (targetId === 'tab-settings' && !dataLoaded.settings) loadUserSettings();
}


// 4. AUTHENTICATION

/**
 * Handle the auth form submission.
 * In login mode:    POST /login with form-encoded credentials.
 * In register mode: POST /users with JSON body, then auto-login.
 */
async function handleAuthSubmit(e) {
    e.preventDefault();
    el.authError.classList.add('hidden');
    el.btnSubmit.innerText = "Please wait...";
    
    const payload = {
        username: el.usernameInput.value,
        password: el.passwordInput.value
    };
    
    try {
        if (isLoginMode) {
            // FastAPI's OAuth2PasswordBearer expects form-encoded data
            const formData = new URLSearchParams();
            formData.append('username', payload.username);
            formData.append('password', payload.password);
            
            const res = await fetch(`${API_BASE}/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: formData.toString()
            });
            const data = await res.json();
            
            if (!res.ok) throw new Error(data.detail || "Login failed");
            
            saveSession(data.access_token, payload.username);
            showDashboard();
            
        } else {
            // Registration: send JSON, then auto-login on success
            payload.email = el.emailInput.value;
            const res = await fetch(`${API_BASE}/users`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            
            if (!res.ok) throw new Error(data.detail || "Registration failed");
            
            // Seamlessly log in the newly registered user
            isLoginMode = true;
            handleAuthSubmit(e);
        }
    } catch (err) {
        el.authError.innerText = err.message;
        el.authError.classList.remove('hidden');
    } finally {
        el.btnSubmit.innerText = isLoginMode ? "Sign In" : "Sign Up";
    }
}

/**
 * Persist session credentials to localStorage.
 * @param {string} token    — JWT access token.
 * @param {string} username — Authenticated username.
 */
function saveSession(token, username) {
    localStorage.setItem('access_token', token);
    localStorage.setItem('username', username);
    currentToken = token;
    currentUsername = username;
}

/** Clear session data and return to the auth screen. */
function logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('username');
    localStorage.removeItem('max_toasts');
    currentToken = null;
    currentUsername = null;
    el.authForm.reset();
    showAuth();
}


// 5. API HELPERS

/**
 * Wrapper around fetch() that injects the JWT Bearer token.
 * Automatically logs the user out on 401/403 responses.
 *
 * @param {string} url     — API path (relative to API_BASE).
 * @param {object} options — Standard fetch options (method, headers, body).
 * @returns {Response}
 */
async function fetchWithAuth(url, options = {}) {
    if (!options.headers) options.headers = {};
    options.headers['Authorization'] = `Bearer ${currentToken}`;
    
    const res = await fetch(API_BASE + url, options);
    if (res.status === 401 || res.status === 403) {
        logout();
        throw new Error("Session expired. Please login again.");
    }
    return res;
}


// 6. DATA FETCHING

/**
 * Fetch and render the user's tracked movies into the "My Movies" grid.
 * Preserves the existing DOM until new data arrives to prevent flicker.
 */
async function loadWatchedMovies() {
    el.loadingWatched.classList.remove('hidden');
    
    try {
        const res = await fetchWithAuth(`/movies/${currentUsername}/watched?limit=100`);
        const result = await res.json();
        
        // Clear grid only after data arrives (prevents white flash)
        el.watchedGrid.innerHTML = '';
        const movies = result.data.watched_movies || [];
        dataLoaded.watched = true;
        
        if (movies.length === 0) {
            el.watchedGrid.innerHTML = `<p class="color-text-muted">You haven't tracked any movies yet.</p>`;
        } else {
            movies.forEach(m => {
                const dateRaw = new Date(m.watched_at || new Date()).toLocaleDateString();
                const card = document.createElement('div');
                card.className = 'movie-card';
                card.innerHTML = `
                    <h4>${esc(m.title)}</h4>
                    <div class="meta">
                        <span>TMDB #${esc(m.tmdb_id || '?')}</span>
                        <span class="muted">Added ${dateRaw}</span>
                    </div>
                    <p class="desc-line">${esc(m.overview || 'No description available for this title.')}</p>
                    <button class="btn-delete" onclick="deleteMovie(${m.id}, '${esc(m.title)}')">Remove</button>
                `;
                el.watchedGrid.appendChild(card);
            });
        }
    } catch (err) {
        el.watchedGrid.innerHTML = `<p class="error-msg">${err.message}</p>`;
    } finally {
        el.loadingWatched.classList.add('hidden');
    }
}

/**
 * Fetch and render personalized recommendations into the "For You" grid.
 * Already-tracked movies are filtered out server-side.
 */
async function loadRecommendations() {
    el.loadingRecs.classList.remove('hidden');
    el.aiInsightsContainer.classList.add('hidden');
    
    try {
        // Parallel fetch for speed
        const [recsRes, insightsRes] = await Promise.all([
            fetchWithAuth(`/movies/recommendations/${currentUsername}`),
            fetchWithAuth(`/movies/ai-insights/${currentUsername}`)
        ]);

        const result = await recsRes.json();
        const insightsResult = await insightsRes.json();
        
        el.recsGrid.innerHTML = '';
        const recs = result.data.recommendations || [];
        dataLoaded.recs = true;

        // Render AI Insights Profile
        if (insightsResult.success && insightsResult.data.insight) {
            el.aiInsightsContainer.innerHTML = `<strong>AI Movie Personality:</strong> ${esc(insightsResult.data.insight)}`;
            el.aiInsightsContainer.classList.remove('hidden');
        }

        if (recs.length === 0) {
            el.recsGrid.innerHTML = `<p class="color-text-muted">Track more movies to get personalized recommendations!</p>`;
        } else {
            recs.forEach(m => {
                const card = document.createElement('div');
                card.className = 'movie-card';
                
                const aiReasonHtml = m.ai_reason 
                    ? `<div class="ai-reason">✨ <strong>AI Insight:</strong> ${esc(m.ai_reason)}</div>` 
                    : '';

                card.innerHTML = `
                    <h4>${esc(m.title)}</h4>
                    <div class="meta">
                        <span>Rating: ${esc(m.vote_average) || 'N/A'}</span>
                    </div>
                    <p class="desc-line">${esc(m.overview) || 'No description available for this title.'}</p>
                    ${aiReasonHtml}
                    <button class="btn btn-outline w-100 rec-btn" onclick="quickTrack(this, '${esc(m.title)}')">+ Track Now</button>
                `;
                el.recsGrid.appendChild(card);
            });
        }
    } catch (err) {
        el.recsGrid.innerHTML = `<p class="error-msg">${err.message}</p>`;
    } finally {
        el.loadingRecs.classList.add('hidden');
    }
}


// 7. MOVIE ACTIONS

/**
 * Core tracking function — sends a POST to add a movie by title.
 * On success, invalidates caches and switches to the "My Movies" tab.
 *
 * @param {string} query — Movie title to search on TMDB.
 */
async function performMovieTracking(query) {
    showToast("Searching and applying...", "info");
    
    try {
        const res = await fetchWithAuth(`/movies/${currentUsername}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query })
        });
        
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Failed to add movie");
        
        el.movieQuery.value = '';
        
        // Invalidate both caches so fresh data is fetched on next visit
        dataLoaded.watched = false;
        dataLoaded.recs = false;
        
        // Navigate to My Movies and force a refresh
        switchTab('tab-watched');
        loadWatchedMovies();
        showToast("Movie tracked successfully!", "success");
    } catch (err) {
        showToast(err.message, "error");
    }
}

/**
 * Form submit handler for the "Add Movie" tab.
 * Prevents default form behavior and delegates to performMovieTracking.
 */
async function handleAddMovie(e) {
    e.preventDefault();
    const query = el.movieQuery.value.trim();
    if (!query) return;
    await performMovieTracking(query);
}

/**
 * Quick-track a movie directly from the Recommendations tab.
 * Makes the API call inline and updates the button state on success.
 *
 * @param {HTMLElement} btnElement — The clicked button (for visual feedback).
 * @param {string}      title     — Movie title to track.
 */
window.quickTrack = async function(btnElement, title) {
    btnElement.innerText = "Submitting...";
    btnElement.classList.add('btn-processing');
    
    try {
        const res = await fetchWithAuth(`/movies/${currentUsername}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: title })
        });
        
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Failed to add movie");
        
        // Success feedback directly on the button
        btnElement.innerText = "✓ Tracked";
        btnElement.style.backgroundColor = "rgba(46, 204, 113, 0.2)";
        btnElement.style.borderColor = "rgba(46, 204, 113, 0.5)";
        btnElement.style.color = "#2ecc71";
        
        // Invalidate watched cache so it refreshes next time the user visits it
        dataLoaded.watched = false;
        showToast("Movie tracked successfully!", "success");
        
    } catch (err) {
        btnElement.innerText = "Error (Try Again)";
        btnElement.classList.remove('btn-processing');
        showToast("Failed to track movie: " + err.message, "error");
    }
}

/**
 * Remove a tracked movie after user confirmation.
 * Invalidates caches and refreshes the My Movies grid.
 *
 * @param {number} movieId — Database primary key of the movie to delete.
 * @param {string} title — Title of the movie (for display in confirmation/toast).
 */
window.deleteMovie = async function(movieId, title) {
    const confirmed = await showConfirm(`Are you sure you want to remove '${title}'?`);
    if (!confirmed) return;
    
    try {
        const res = await fetchWithAuth(`/movies/${currentUsername}/${movieId}`, {
            method: 'DELETE'
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail);
        
        // Invalidate caches — the movie list and recs are now stale
        dataLoaded.watched = false;
        dataLoaded.recs = false;
        
        loadWatchedMovies();
        showToast(`'${title}' removed successfully.`, "success");
    } catch (err) {
        showToast("Failed to delete: " + err.message, "error");
    }
}


// 8. ADMIN PANEL

/**
 * Fetch all registered users and render them in the admin table.
 * Only accessible to users with the 'admin' role (enforced server-side).
 */
async function loadAdminUsers() {
    el.adminUsersTbody.innerHTML = '';
    el.loadingAdmin.classList.remove('hidden');
    
    try {
        const res = await fetchWithAuth('/users');
        const result = await res.json();
        
        let users = result.data.users || [];
        users.forEach(u => {
            const tr = document.createElement('tr');
            const date = new Date(u.created_at || new Date()).toLocaleDateString();
            tr.innerHTML = `
                <td>#${esc(u.id.toString())}</td>
                <td>
                    <strong>${esc(u.username)}</strong><br>
                    <span style="color:var(--text-muted); font-size:0.8rem;">${esc(u.email)}</span>
                </td>
                <td>
                    <span class="badge">${esc(u.os || 'N/A')}</span><br>
                    <span style="color:var(--text-muted); font-size:0.8rem;">${esc(u.city || 'Unknown')}, ${esc(u.country || 'Unknown')}</span>
                </td>
                <td>${esc(date)}</td>
                <td>
                    <button class="btn-delete" style="width:auto; padding:0.3rem 0.6rem;" onclick="adminDeleteUser('${esc(u.username)}')">Ban</button>
                </td>
            `;
            el.adminUsersTbody.appendChild(tr);
        });
    } catch (err) {
        el.adminUsersTbody.innerHTML = `<tr><td colspan="5" class="error-msg">${err.message}</td></tr>`;
    } finally {
        el.loadingAdmin.classList.add('hidden');
    }
}

/**
 * Permanently ban (soft-delete) a user from the admin panel.
 * The 'admin' account itself is protected from deletion.
 *
 * @param {string} username — Username of the account to ban.
 */
window.adminDeleteUser = async function(username) {
    if (username === 'admin') { 
        showToast("Cannot delete admin.", "error"); 
        return; 
    }
    
    const confirmed = await showConfirm(`Are you absolutely sure you want to permanently delete user ${username}?`);
    if (!confirmed) return;
    
    try {
        const res = await fetchWithAuth(`/users/${username}`, {
            method: 'DELETE'
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail);
        
        // Refresh the admin table
        loadAdminUsers();
        showToast(`User ${username} banned.`, "success");
    } catch (err) {
        showToast("Failed to delete user: " + err.message, "error");
    }
}


// 9. SETTINGS & PROFILE

/**
 * Fetch the user's profile to populate the settings tab.
 */
async function loadUserSettings() {
    try {
        const res = await fetchWithAuth(`/users/${currentUsername}`);
        const result = await res.json();
        
        if (!res.ok) throw new Error(result.detail || "Failed to load settings");
        
        const data = result.data.user;
        el.aiToggle.checked = data.ai_enabled;
        
        // Only the 'admin' user sees the admin panel tab
        if (data.role === 'admin') {
            el.btnAdminTab.classList.remove('hidden');
        }
        
        // Update local settings state
        if (data.max_toasts) {
            localStorage.setItem('max_toasts', data.max_toasts);
            if (el.inputMaxToasts) el.inputMaxToasts.value = data.max_toasts;
        }

        dataLoaded.settings = true;
    } catch (err) {
        showToast(err.message, "error");
    }
}

/**
 * Handle toggling the AI feature and updating the backend.
 */
async function handleToggleAI(e) {
    const isEnabled = e.target.checked;
    el.aiToggle.disabled = true;
    
    try {
        const res = await fetchWithAuth(`/users/${currentUsername}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ field: 'ai_enabled', value: isEnabled.toString() })
        });
        
        const result = await res.json();
        if (!res.ok) throw new Error(result.detail || "Failed to update setting");
        
        dataLoaded.recs = false;
        showToast("Settings updated successfully.", "success");
    } catch (err) {
        el.aiToggle.checked = !isEnabled;
        showToast(err.message, "error");
    } finally {
        el.aiToggle.disabled = false;
    }
}

async function handleUpdateEmail(e) {
    e.preventDefault();
    const newEmail = el.inputNewEmail.value;
    const currentPass = el.inputEmailVerifyPassword.value;
    
    // Hide previous messages
    el.msgEmail.classList.add('hidden');

    try {
        const res = await fetchWithAuth(`/users/${currentUsername}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                field: 'email', 
                value: newEmail,
                current_password: currentPass
            })
        });
        
        const result = await res.json();
        if (!res.ok) throw new Error(result.detail || "Failed to update email");
        
        el.inputNewEmail.value = '';
        el.inputEmailVerifyPassword.value = '';
        showToast("Email updated successfully.", "success");
        closeSettingsModal('modal-update-email');
    } catch (err) {
        showMessage(el.msgEmail, err.message, "error");
    }
}

async function handleUpdatePassword(e) {
    e.preventDefault();
    const currentPass = el.inputPassCurrent.value;
    const newPassword = el.inputNewPassword.value;
    const confirmPassword = el.inputNewPasswordConfirm.value;

    // Hide previous messages
    el.msgPassword.classList.add('hidden');

    if (newPassword !== confirmPassword) {
        showMessage(el.msgPassword, "New passwords do not match.", "error");
        return;
    }

    if (newPassword === currentPass) {
        showMessage(el.msgPassword, "New password must be different from the current one.", "error");
        return;
    }
    
    try {
        const res = await fetchWithAuth(`/users/${currentUsername}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                field: 'password', 
                value: newPassword,
                current_password: currentPass
            })
        });
        
        const result = await res.json();
        if (!res.ok) throw new Error(result.detail || "Failed to update password");
        
        el.inputPassCurrent.value = '';
        el.inputNewPassword.value = '';
        el.inputNewPasswordConfirm.value = '';
        showToast("Password updated successfully.", "success");
        closeSettingsModal('modal-update-password');
    } catch (err) {
        showMessage(el.msgPassword, err.message, "error");
    }
}


// 10. THREE.JS BACKGROUND (Dotted Surface)

function initThreeJSBackground() {
    const container = document.getElementById('canvas-container');
    if (!container || typeof THREE === 'undefined') return;

    const SEPARATION = 150;
    const AMOUNTX = 40;
    const AMOUNTY = 60;

    const scene = new THREE.Scene();
    scene.fog = new THREE.Fog(0x0a0a0a, 2000, 10000); // Matches var(--bg-dark)

    const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 1, 10000);
    camera.position.set(0, 355, 1220);

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setClearColor(scene.fog.color, 0);

    container.appendChild(renderer.domElement);

    const positions = [];
    const colors = [];
    const geometry = new THREE.BufferGeometry();

    for (let ix = 0; ix < AMOUNTX; ix++) {
        for (let iy = 0; iy < AMOUNTY; iy++) {
            const x = ix * SEPARATION - (AMOUNTX * SEPARATION) / 2;
            const y = 0;
            const z = iy * SEPARATION - (AMOUNTY * SEPARATION) / 2;

            positions.push(x, y, z);
            // Pure neutral gray particles for dark theme
            colors.push(0.35, 0.35, 0.35);
        }
    }

    geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
    geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));

    const material = new THREE.PointsMaterial({
        size: 8,
        vertexColors: true,
        transparent: true,
        opacity: 0.6,
        sizeAttenuation: true,
    });

    const points = new THREE.Points(geometry, material);
    scene.add(points);

    let count = 0;
    let mouseX = 0;
    let mouseY = 0;
    let windowHalfX = window.innerWidth / 2;
    let windowHalfY = window.innerHeight / 2;

    document.addEventListener('mousemove', (event) => {
        mouseX = event.clientX - windowHalfX;
        mouseY = event.clientY - windowHalfY;
    });

    function animate() {
        requestAnimationFrame(animate);

        const positionAttribute = geometry.attributes.position;
        const posArray = positionAttribute.array;

        let i = 0;
        for (let ix = 0; ix < AMOUNTX; ix++) {
            for (let iy = 0; iy < AMOUNTY; iy++) {
                const index = i * 3;
                posArray[index + 1] = Math.sin((ix + count) * 0.3) * 50 + Math.sin((iy + count) * 0.5) * 50;
                i++;
            }
        }

        positionAttribute.needsUpdate = true;

        // Interactive Parallax Effect
        camera.position.x += (mouseX * 0.8 - camera.position.x) * 0.05;
        camera.position.y += (-mouseY * 0.5 + 355 - camera.position.y) * 0.05;
        camera.lookAt(scene.position);

        renderer.render(scene, camera);
        count += 0.1;
    }

    window.addEventListener('resize', () => {
        windowHalfX = window.innerWidth / 2;
        windowHalfY = window.innerHeight / 2;
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    });

    animate();
}


// BOOTSTRAP
init();
initThreeJSBackground();
