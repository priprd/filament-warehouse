/**
 * AUTHENTICATION SYSTEM
 * Handles JWT token storage, session persistence, Login/Register, Google OAuth
 */

class AuthManager {
  constructor() {
    this.tokenKey = "warehouse_jwt";
    this.userKey = "warehouse_user";
    this.currentUser = this.getUser();
    this.authEnabled = true;

    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", () => this.updateUIState());
    } else {
      this.updateUIState();
    }
    this.loadProviders();
    this.loadAuthStatus();
  }

  async loadAuthStatus() {
    try {
      const response = await fetch('/api/auth/status');
      this.authEnabled = (await response.json()).auth_enabled;
    } catch {
      this.authEnabled = true;
    }
    this.updateUIState();
  }

  async loadProviders() {
    const list = document.getElementById('oauth-provider-list');
    if (!list) return;
    try {
      const providers = await fetch('/api/auth/providers').then(response => response.json());
      list.innerHTML = providers.map(provider => `<a class="btn btn-outline-dark" href="/api/auth/${encodeURIComponent(provider.name)}/authorize"><i class="fab fa-${provider.name}"></i> Continue with ${provider.label}</a>`).join('');
    } catch {
      list.innerHTML = '<span class="text-secondary small">Social sign-in is not configured.</span>';
    }
  }

  getToken() {
    const token = localStorage.getItem(this.tokenKey);
    if (!token || token === "null" || token === "undefined" || token.trim() === "") {
      return null;
    }
    return token;
  }

  getAuthHeaders(extraHeaders = {}) {
    const token = this.getToken();
    return {
      ...extraHeaders,
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    };
  }

  getUser() {
    const raw = localStorage.getItem(this.userKey);
    try {
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  }

  isAuthenticated() {
    return !!(this.getToken() && this.currentUser);
  }

  setSession(token, user) {
    if (token) localStorage.setItem(this.tokenKey, token);
    if (user) localStorage.setItem(this.userKey, JSON.stringify(user));
    this.currentUser = user || this.getUser();
    this.updateUIState();
  }

  clearSession() {
    localStorage.removeItem(this.tokenKey);
    localStorage.removeItem(this.userKey);
    this.currentUser = null;
    this.updateUIState();
  }

  logout() {
    this.clearSession();
    closeModal('auth-modal');
    showToast("Logged out successfully.", "info");
    if (typeof app !== 'undefined' && app.handleLogout) {
      app.handleLogout();
    }
  }

  switchAuthTab(tab) {
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    const loginBtn = document.getElementById('tab-login-btn');
    const registerBtn = document.getElementById('tab-register-btn');

    if (tab === 'register') {
      if (loginForm) loginForm.style.display = 'none';
      if (registerForm) registerForm.style.display = 'block';
      if (loginBtn) loginBtn.className = 'btn btn-secondary';
      if (registerBtn) registerBtn.className = 'btn btn-primary';
    } else {
      if (loginForm) loginForm.style.display = 'block';
      if (registerForm) registerForm.style.display = 'none';
      if (loginBtn) loginBtn.className = 'btn btn-primary';
      if (registerBtn) registerBtn.className = 'btn btn-secondary';
    }
  }

  async login(usernameOrEmail, password) {
    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username_or_email: usernameOrEmail.trim(), password: password })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Login failed");

      this.setSession(data.access_token, data.user);
      showToast(`Welcome back, ${data.user.username}!`, "success");
      closeModal('auth-modal');

      const loginForm = document.getElementById('login-form');
      if (loginForm) loginForm.reset();

      if (typeof app !== 'undefined' && app.loadFilaments) {
        await app.loadFilaments();
      }
    } catch (err) {
      showToast(err.message, "danger");
    }
  }

  async register(username, email, password) {
    try {
      const res = await fetch("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: username.trim(), email: email.trim(), password: password })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Registration failed");

      this.setSession(data.access_token, data.user);
      showToast(`Welcome, ${data.user.username}! Account created.`, "success");
      closeModal('auth-modal');

      const registerForm = document.getElementById('register-form');
      if (registerForm) registerForm.reset();

      if (typeof app !== 'undefined' && app.loadFilaments) {
        await app.loadFilaments();
      }
    } catch (err) {
      showToast(err.message, "danger");
    }
  }

  async handleGoogleCallback(response) {
    try {
      const res = await fetch("/api/auth/google", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ credential: response.credential })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Google Login failed");

      this.setSession(data.access_token, data.user);
      showToast(`Signed in as ${data.user.username}.`, "success");
      closeModal('auth-modal');
      if (typeof app !== 'undefined' && app.loadFilaments) {
        await app.loadFilaments();
      }
    } catch (err) {
      showToast("Google Auth Error: " + err.message, "danger");
    }
  }

  updateUIState() {
    const user = this.currentUser;
    const isAuth = !this.authEnabled || !!(user && this.getToken());

    const userLabel = document.getElementById('user-username-label');
    const avatarImg = document.getElementById('nav-avatar-img');
    const loggedInView = document.getElementById('auth-logged-in-view');
    const formsView = document.getElementById('auth-forms-view');
    const modalTitle = document.getElementById('auth-modal-title');
    const modalUserName = document.getElementById('modal-user-name');
    const modalUserEmail = document.getElementById('modal-user-email');
    const modalUserAvatar = document.getElementById('modal-user-avatar');
    const authOpenBtn = document.getElementById('auth-open-btn');
    const adminTools = document.getElementById('admin-tools');

    const btnNavNfc = document.getElementById('btn-nav-nfc');
    const btnNavAdd = document.getElementById('btn-nav-add');
    const statsContainer = document.getElementById('stats-container');
    const toolbarContainer = document.getElementById('toolbar-container');
    const filamentGrid = document.getElementById('filament-grid');
    const unauthenticatedView = document.getElementById('unauthenticated-view');

    if (isAuth) {
      const displayUser = this.authEnabled ? user : null;
      if (userLabel) userLabel.textContent = displayUser ? displayUser.username : 'Open Access';
      if (avatarImg && displayUser?.avatar_url) avatarImg.src = displayUser.avatar_url;
      if (loggedInView) loggedInView.style.display = displayUser ? 'block' : 'none';
      if (formsView) formsView.style.display = 'none';
      if (modalTitle) modalTitle.textContent = displayUser ? `Signed in as ${displayUser.username}` : 'Open Access';
      if (modalUserName && displayUser) modalUserName.textContent = displayUser.username;
      if (modalUserEmail && displayUser) modalUserEmail.textContent = displayUser.email || '';
      if (modalUserAvatar && displayUser?.avatar_url) modalUserAvatar.src = displayUser.avatar_url;
      if (authOpenBtn) authOpenBtn.classList.replace('btn-outline-info', 'btn-info');
      if (!this.authEnabled && authOpenBtn) {
        authOpenBtn.removeAttribute('data-bs-toggle');
        authOpenBtn.removeAttribute('data-bs-target');
      }
      if (adminTools) adminTools.classList.toggle('d-none', !displayUser || displayUser.role !== 'admin');
      if (displayUser?.role === 'admin') { this.loadUsers(); this.loadAudit(); }

      if (btnNavNfc) btnNavNfc.style.display = 'inline-flex';
      if (btnNavAdd) btnNavAdd.style.display = 'inline-flex';
      if (statsContainer) statsContainer.style.display = 'grid';
      if (toolbarContainer) toolbarContainer.style.display = 'flex';
      if (filamentGrid) filamentGrid.style.display = 'grid';
      if (unauthenticatedView) unauthenticatedView.style.display = 'none';
    } else {
      if (userLabel) userLabel.textContent = "Log In";
      if (avatarImg) avatarImg.src = "https://api.dicebear.com/7.x/bottts/svg?seed=warehouse";
      if (loggedInView) loggedInView.style.display = 'none';
      if (formsView) formsView.style.display = 'block';
      if (modalTitle) modalTitle.textContent = "Log in to the warehouse";
      if (authOpenBtn) authOpenBtn.classList.replace('btn-info', 'btn-outline-info');
      if (authOpenBtn) {
        authOpenBtn.setAttribute('data-bs-toggle', 'modal');
        authOpenBtn.setAttribute('data-bs-target', '#auth-modal');
      }

      if (btnNavNfc) btnNavNfc.style.display = 'inline-flex';
      if (btnNavAdd) btnNavAdd.style.display = 'inline-flex';
      if (statsContainer) statsContainer.style.display = 'grid';
      if (toolbarContainer) toolbarContainer.style.display = 'flex';
      if (filamentGrid) filamentGrid.style.display = 'grid';
      if (unauthenticatedView) unauthenticatedView.style.display = 'none';
    }
  }

  async loadUsers() {
    const list = document.getElementById('user-list');
    if (!list || !this.isAuthenticated() || this.currentUser.role !== 'admin') return;
    const response = await fetch('/api/auth/users', { headers: this.getAuthHeaders() });
    if (!response.ok) return;
    const users = await response.json();
    list.innerHTML = users.map(user => `<div class="border rounded p-2 d-flex align-items-center justify-content-between gap-2"><div><strong>${user.username}</strong><small class="d-block text-secondary">${user.email} · ${user.role}${user.is_blocked ? ' · blocked' : ''}</small></div><div class="btn-group btn-group-sm"><button class="btn btn-outline-warning" onclick="auth.toggleBlock(${user.id}, ${!user.is_blocked})">${user.is_blocked ? 'Unblock' : 'Block'}</button><button class="btn btn-outline-danger" onclick="auth.deleteUser(${user.id})">Delete</button></div></div>`).join('');
  }

  async loadAudit() {
    const list = document.getElementById('audit-list');
    if (!list) return;
    const response = await fetch('/api/auth/audit', { headers: this.getAuthHeaders() });
    if (!response.ok) return;
    const entries = await response.json();
    list.innerHTML = entries.map(entry => `<tr><td><span class="badge text-bg-secondary">${entry.action}</span></td><td>${entry.details || entry.entity_type}</td><td>${entry.actor_username || 'system'}</td><td>${new Date(entry.created_at).toLocaleString()}</td></tr>`).join('');
  }

  async toggleBlock(userId, isBlocked) {
    await fetch(`/api/auth/users/${userId}`, { method: 'PATCH', headers: { ...this.getAuthHeaders(), 'Content-Type': 'application/json' }, body: JSON.stringify({ is_blocked: isBlocked }) });
    this.loadUsers();
  }

  async deleteUser(userId) {
    if (!window.confirm('Delete this user account?')) return;
    await fetch(`/api/auth/users/${userId}`, { method: 'DELETE', headers: this.getAuthHeaders() });
    this.loadUsers();
  }
}

window.auth = new AuthManager();

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('auth-open-btn')?.addEventListener('click', event => {
    if (!auth.authEnabled) return;
    const modal = window.bootstrap?.Modal.getOrCreateInstance(document.getElementById('auth-modal'));
    modal?.show();
  });
  document.getElementById('login-form')?.addEventListener('submit', event => { event.preventDefault(); auth.login(document.getElementById('login-identity').value, document.getElementById('login-password').value); });
  document.getElementById('register-form')?.addEventListener('submit', event => { event.preventDefault(); auth.register(document.getElementById('register-username').value, document.getElementById('register-email').value, document.getElementById('register-password').value); });
  document.getElementById('refresh-users-btn')?.addEventListener('click', () => auth.loadUsers());
});
