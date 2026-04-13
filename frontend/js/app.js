const API_BASE = ''; // Same origin

// State
let currentToken = localStorage.getItem('access_token');
let currentUsername = localStorage.getItem('username');
let isLoginMode = true;

// DOM Elements
const el = {
    navActions: document.getElementById('nav-actions'),
    userGreeting: document.getElementById('user-greeting'),
    btnLogout: document.getElementById('btn-logout'),
    
    viewAuth: document.getElementById('view-auth'),
    viewDashboard: document.getElementById('view-dashboard'),
    
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

    tabBtns: document.querySelectorAll('.tab-btn'),
    tabContents: document.querySelectorAll('.tab-content'),
    
    watchedGrid: document.getElementById('watched-grid'),
    recsGrid: document.getElementById('recs-grid'),
    loadingWatched: document.getElementById('loading-watched'),
    loadingRecs: document.getElementById('loading-recs'),
    
    addMovieForm: document.getElementById('add-movie-form'),
    movieQuery: document.getElementById('movie-query'),
    addMsg: document.getElementById('add-msg')
};

// Initialize
function init() {
    if (currentToken && currentUsername) {
        showDashboard();
    } else {
        showAuth();
    }
    attachListeners();
}

// Listeners
function attachListeners() {
    el.authSwitchLink.addEventListener('click', toggleAuthMode);
    el.authForm.addEventListener('submit', handleAuthSubmit);
    el.btnLogout.addEventListener('click', logout);
    
    el.tabBtns.forEach(btn => {
        btn.addEventListener('click', () => switchTab(btn.dataset.target));
    });
    
    el.addMovieForm.addEventListener('submit', handleAddMovie);
}

// UI State Toggles
function showAuth() {
    el.viewAuth.classList.remove('hidden');
    el.viewDashboard.classList.add('hidden');
    el.navActions.classList.add('hidden');
}

function showDashboard() {
    el.viewAuth.classList.add('hidden');
    el.viewDashboard.classList.remove('hidden');
    el.navActions.classList.remove('hidden');
    el.userGreeting.innerText = `Hi, ${currentUsername}`;
    
    // Load initial data
    loadWatchedMovies();
}

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
    document.getElementById('auth-switch-link').addEventListener('click', toggleAuthMode);
}

function switchTab(targetId) {
    el.tabBtns.forEach(btn => btn.classList.remove('active'));
    document.querySelector(`.tab-btn[data-target="${targetId}"]`).classList.add('active');
    
    el.tabContents.forEach(content => content.classList.add('hidden'));
    document.getElementById(targetId).classList.remove('hidden');
    
    // Lazy load logic
    if (targetId === 'tab-watched') loadWatchedMovies();
    if (targetId === 'tab-recommend') loadRecommendations();
}

// Auth Actions
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
            // FastAPI uses form data for OAuth2
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
            // Register
            payload.email = el.emailInput.value;
            const res = await fetch(`${API_BASE}/users`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            
            if (!res.ok) throw new Error(data.detail || "Registration failed");
            
            // Auto Login after registration
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

function saveSession(token, username) {
    localStorage.setItem('access_token', token);
    localStorage.setItem('username', username);
    currentToken = token;
    currentUsername = username;
}

function logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('username');
    currentToken = null;
    currentUsername = null;
    el.authForm.reset();
    showAuth();
}

// API Helpers
async function fetchWithAuth(url, options = {}) {
    if (!options.headers) options.headers = {};
    options.headers['Authorization'] = `Bearer ${currentToken}`;
    
    const res = await fetch(API_BASE + url, options);
    if (res.status === 401 || res.status === 403) {
        logout(); // Token expired or malicious access
        throw new Error("Session expired. Please login again.");
    }
    return res;
}

// Data Fetching
async function loadWatchedMovies() {
    el.watchedGrid.innerHTML = '';
    el.loadingWatched.classList.remove('hidden');
    
    try {
        const res = await fetchWithAuth(`/movies/${currentUsername}/watched`);
        const result = await res.json();
        
        const movies = result.data.watched_movies || [];
        if (movies.length === 0) {
            el.watchedGrid.innerHTML = `<p class="color-text-muted">You haven't tracked any movies yet.</p>`;
        } else {
            movies.forEach(m => {
                const dateRaw = new Date(m.watched_at).toLocaleDateString();
                const card = document.createElement('div');
                card.className = 'movie-card';
                card.innerHTML = `
                    <h4>${m.title}</h4>
                    <div class="meta">
                        <span>TMDB #${m.tmdb_id || '?'}</span>
                        <span>Tracked on ${dateRaw}</span>
                    </div>
                    <p style="font-size:0.9rem; color:#a1a1aa; margin-bottom:1rem; height:40px; overflow:hidden;">${m.overview || 'No description available'}</p>
                    <button class="btn-delete" onclick="deleteMovie('${m.title}')">✖ Remove</button>
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

async function loadRecommendations() {
    el.recsGrid.innerHTML = '';
    el.loadingRecs.classList.remove('hidden');
    
    try {
        const res = await fetchWithAuth(`/movies/recommendations/${currentUsername}`);
        const result = await res.json();
        
        const recs = result.data.recommendations || [];
        if (recs.length === 0) {
            el.recsGrid.innerHTML = `<p class="color-text-muted">Track more movies to get personalized recommendations!</p>`;
        } else {
            recs.forEach(m => {
                const card = document.createElement('div');
                card.className = 'movie-card';
                card.style.background = 'rgba(138, 43, 226, 0.05)';
                card.innerHTML = `
                    <h4>${m.title}</h4>
                    <div class="meta">
                        <span>⭐ ${m.vote_average || 'N/A'}</span>
                        <span>Release: ${m.release_date || 'Unknown'}</span>
                    </div>
                    <p style="font-size:0.9rem; color:#a1a1aa; margin-bottom:1rem; height:60px; overflow:hidden; text-overflow:ellipsis;">${m.overview || 'No description'}</p>
                    <button class="btn btn-outline" style="width:100%; border-color:var(--primary); color:var(--primary)" onclick="quickTrack('${m.title}')">+ Track Now</button>
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

async function handleAddMovie(e) {
    e.preventDefault();
    const query = el.movieQuery.value.trim();
    if (!query) return;
    
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
        
        // Refresh watched list silently
        loadWatchedMovies();
    } catch (err) {
        el.addMsg.innerHTML = `<span class="error-msg">${err.message}</span>`;
    }
}

window.quickTrack = function(title) {
    el.movieQuery.value = title;
    switchTab('tab-add');
    el.addMsg.innerHTML = "Submitting...";
    el.addMovieForm.dispatchEvent(new Event('submit'));
}

window.deleteMovie = async function(title) {
    if (!confirm(`Are you sure you want to remove '${title}'?`)) return;
    
    try {
        const res = await fetchWithAuth(`/movies/${currentUsername}/${encodeURIComponent(title)}`, {
            method: 'DELETE'
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail);
        
        // Reload silently
        loadWatchedMovies();
    } catch (err) {
        alert("Failed to delete: " + err.message);
    }
}

// Start
init();
