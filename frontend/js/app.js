/**
 * CineWave — Frontend Application (SPA)
 * =======================================
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
 *   8. Admin Panel (User List, Ban)
 */

const API_BASE = ''; // Same origin — no CORS needed

// =========================================================================
// 1. STATE & DOM REFERENCES
// =========================================================================

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
    admin: false
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
    adminUsersTbody: document.getElementById('admin-users-tbody')
};


// =========================================================================
// 2. INITIALIZATION & EVENT BINDING
// =========================================================================

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
}


// =========================================================================
// 3. UI STATE TOGGLES
// =========================================================================

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
}


// =========================================================================
// 4. AUTHENTICATION
// =========================================================================

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
    currentToken = null;
    currentUsername = null;
    el.authForm.reset();
    showAuth();
}


// =========================================================================
// 5. API HELPERS
// =========================================================================

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


// =========================================================================
// 6. DATA FETCHING
// =========================================================================

/**
 * Fetch and render the user's tracked movies into the "My Movies" grid.
 * Preserves the existing DOM until new data arrives to prevent flicker.
 */
async function loadWatchedMovies() {
    el.loadingWatched.classList.remove('hidden');
    
    try {
        const res = await fetchWithAuth(`/movies/${currentUsername}/watched`);
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
                    <h4>${m.title}</h4>
                    <div class="meta">
                        <span>TMDB #${m.tmdb_id || '?'}</span>
                        <span class="muted">Added ${dateRaw}</span>
                    </div>
                    <p class="desc-line">${m.overview || 'No description available for this title.'}</p>
                    <button class="btn-delete" onclick="deleteMovie('${m.title.replace(/'/g, "\\'")}')"  >Remove</button>
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
    
    try {
        const res = await fetchWithAuth(`/movies/recommendations/${currentUsername}`);
        const result = await res.json();
        
        el.recsGrid.innerHTML = '';
        const recs = result.data.recommendations || [];
        dataLoaded.recs = true;
        
        if (recs.length === 0) {
            el.recsGrid.innerHTML = `<p class="color-text-muted">Track more movies to get personalized recommendations!</p>`;
        } else {
            recs.forEach(m => {
                const card = document.createElement('div');
                card.className = 'movie-card';
                card.innerHTML = `
                    <h4>${m.title}</h4>
                    <div class="meta">
                        <span>Rating: ${m.vote_average || 'N/A'}</span>
                    </div>
                    <p class="desc-line">${m.overview || 'No description available for this title.'}</p>
                    <button class="btn btn-outline w-100 rec-btn" onclick="quickTrack(this, '${m.title.replace(/'/g, "\\'") }')">+ Track Now</button>
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


// =========================================================================
// 7. MOVIE ACTIONS
// =========================================================================

/**
 * Core tracking function — sends a POST to add a movie by title.
 * On success, invalidates caches and switches to the "My Movies" tab.
 *
 * @param {string} query — Movie title to search on TMDB.
 */
async function performMovieTracking(query) {
    el.addMsg.classList.remove('hidden');
    el.addMsg.className = 'msgbox';
    el.addMsg.innerHTML = "Searching and applying...";
    
    try {
        const res = await fetchWithAuth(`/movies/${currentUsername}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query })
        });
        
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Failed to add movie");
        
        el.addMsg.innerHTML = `<span class="success-msg">Movie tracked successfully!</span>`;
        el.movieQuery.value = '';
        
        // Invalidate both caches so fresh data is fetched on next visit
        dataLoaded.watched = false;
        dataLoaded.recs = false;
        
        // Navigate to My Movies and force a refresh
        switchTab('tab-watched');
        loadWatchedMovies();
    } catch (err) {
        el.addMsg.innerHTML = `<span class="error-msg">${err.message}</span>`;
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
 * Shows a brief "Submitting..." state on the button before processing.
 *
 * @param {HTMLElement} btnElement — The clicked button (for visual feedback).
 * @param {string}      title     — Movie title to track.
 */
window.quickTrack = function(btnElement, title) {
    el.movieQuery.value = title;
    btnElement.innerText = "Submitting...";
    btnElement.classList.add('btn-processing');
    
    // Small delay for visual feedback before navigating away
    setTimeout(() => {
        switchTab('tab-add');
        performMovieTracking(title);
    }, 200);
}

/**
 * Remove a tracked movie after user confirmation.
 * Invalidates caches and refreshes the My Movies grid.
 *
 * @param {string} title — Title of the movie to delete.
 */
window.deleteMovie = async function(title) {
    if (!confirm(`Are you sure you want to remove '${title}'?`)) return;
    
    try {
        const res = await fetchWithAuth(`/movies/${currentUsername}/${encodeURIComponent(title)}`, {
            method: 'DELETE'
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail);
        
        // Invalidate caches — the movie list and recs are now stale
        dataLoaded.watched = false;
        dataLoaded.recs = false;
        
        loadWatchedMovies();
    } catch (err) {
        alert("Failed to delete: " + err.message);
    }
}


// =========================================================================
// 8. ADMIN PANEL
// =========================================================================

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
                <td>#${u.id}</td>
                <td>
                    <strong>${u.username}</strong><br>
                    <span style="color:var(--text-muted); font-size:0.8rem;">${u.email}</span>
                </td>
                <td>
                    <span class="badge">${u.os}</span><br>
                    <span style="color:var(--text-muted); font-size:0.8rem;">${u.city}, ${u.country}</span>
                </td>
                <td>${date}</td>
                <td>
                    <button class="btn-delete" style="width:auto; padding:0.3rem 0.6rem;" onclick="adminDeleteUser('${u.username}')">Ban</button>
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
    if (username === 'admin') { alert("Cannot delete admin."); return; }
    if (!confirm(`Are you absolutely sure you want to permanently delete user ${username}?`)) return;
    
    try {
        const res = await fetchWithAuth(`/users/${username}`, {
            method: 'DELETE'
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail);
        
        // Refresh the admin table
        loadAdminUsers();
    } catch (err) {
        alert("Failed to delete user: " + err.message);
    }
}


// =========================================================================
// BOOTSTRAP
// =========================================================================
init();
