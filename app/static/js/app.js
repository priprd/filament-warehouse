/**
 * FILAMENTS WAREHOUSE - Main Application
 * No login required — open warehouse for all.
 */

window.auth = window.auth || {
  getToken() { return null; },
  getUser() { return null; },
  getAuthHeaders(extraHeaders = {}) { return { ...extraHeaders }; },
  isAuthenticated() { return false; },
  clearSession() {},
  setSession() {},
  logout() {}
};

const RAL_COLORS = {
  "RAL 1000": "#CCC28F", "RAL 1001": "#D1BC8A", "RAL 1002": "#D2B26A", "RAL 1003": "#F3A505",
  "RAL 1018": "#F8B800", "RAL 1023": "#F7B500", "RAL 1028": "#FF9900", "RAL 2004": "#E25303",
  "RAL 3000": "#A72920", "RAL 3002": "#9B111E", "RAL 3020": "#C1121C", "RAL 4005": "#83639D",
  "RAL 5002": "#202256", "RAL 5005": "#154889", "RAL 5015": "#007CB0", "RAL 6005": "#2F4538",
  "RAL 6018": "#57A639", "RAL 7016": "#373F43", "RAL 7035": "#C5C7C4", "RAL 8017": "#45322E",
  "RAL 9003": "#F4F4F4", "RAL 9005": "#0E0E10", "RAL 9010": "#F1ECE1", "RAL 9016": "#F6F6F6"
};

function applyTheme(theme) {
  const nextTheme = theme === 'light' ? 'light' : 'dark';
  document.body.setAttribute('data-bs-theme', nextTheme);
  const toggle = document.getElementById('theme-toggle');
  if (!toggle) return;

  const icon = toggle.querySelector('i');
  const label = toggle.querySelector('.theme-label');
  if (icon) {
   icon.className = nextTheme === 'light' ? 'fas fa-sun' : 'fas fa-moon';
  }
  if (label) {
   label.textContent = nextTheme === 'light' ? 'Light' : 'Dark';
  }
  try {
   localStorage.setItem('filament-theme', nextTheme);
  } catch (err) {
   console.warn('Could not persist theme selection.', err);
  }
}

function toggleTheme() {
  const currentTheme = document.body.getAttribute('data-bs-theme') === 'light' ? 'light' : 'dark';
  applyTheme(currentTheme === 'light' ? 'dark' : 'light');
}

class WarehouseApp {
  constructor() {
    this.filaments = [];
    this.currentFilterMaterial = "";
    this.currentSearch = "";
    this.currentLowStockOnly = false;
    this.editingFilamentId = null;
    this.activeFilamentId = null;

    this.init();
  }

  async init() {
    this.bindEvents();
    await this.loadFilaments();
  }

  bindEvents() {
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
      themeToggle.addEventListener('click', toggleTheme);
    }

    const searchInput = document.getElementById('search-input');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        this.currentSearch = e.target.value.trim();
        this.renderFilaments();
      });
    }

    const materialSelect = document.getElementById('material-filter');
    if (materialSelect) {
      materialSelect.addEventListener('change', (e) => {
        this.currentFilterMaterial = e.target.value;
        this.renderFilaments();
      });
    }

    const filamentForm = document.getElementById('filament-form');
    if (filamentForm) {
      filamentForm.addEventListener('submit', (e) => this.handleSaveFilament(e));
    }

    const priceForm = document.getElementById('price-history-form');
    if (priceForm) {
      priceForm.addEventListener('submit', (e) => this.handleAddPriceHistory(e));
    }
  }

  async loadFilaments() {
    try {
      if (auth && auth.authEnabled && !auth.isAuthenticated()) return;
      const headers = auth && auth.getAuthHeaders ? auth.getAuthHeaders() : {};
      const res = await fetch("/api/filaments", { headers });
      if (!res.ok) {
        if (res.status === 401) {
          this.filaments = [];
          this.calculateStats();
          this.renderFilaments();
          return;
        }
        throw new Error("Failed to fetch filaments");
      }
      this.filaments = await res.json();
      this.calculateStats();
      this.renderFilaments();
    } catch (err) {
      console.error(err);
      showToast("Error loading inventory: " + err.message, "danger");
    }
  }

  calculateStats() {
    const totalSpools = this.filaments.length;
    let totalKg = 0;
    let totalValue = 0;
    let lowStockCount = 0;

    this.filaments.forEach(f => {
      totalKg += f.current_weight_kg || 0;
      if (f.latest_price !== null && f.latest_price !== undefined) {
        totalValue += (f.latest_price * (f.current_weight_kg / f.initial_weight_kg));
      }
      if (f.current_weight_kg <= f.initial_weight_kg * 0.2) {
        lowStockCount++;
      }
    });

    const spoolsEl = document.getElementById('stat-total-spools');
    const kgEl = document.getElementById('stat-total-kg');
    const valEl = document.getElementById('stat-total-val');
    const lowEl = document.getElementById('stat-low-stock');

    if (spoolsEl) spoolsEl.textContent = totalSpools;
    if (kgEl) kgEl.textContent = `${totalKg.toFixed(2)} kg`;
    if (valEl) valEl.textContent = `€${totalValue.toFixed(2)}`;
    if (lowEl) lowEl.textContent = lowStockCount;

    const lowStockCard = document.getElementById('stat-low-stock-card');
    if (lowStockCard) {
      if (lowStockCount > 0) lowStockCard.classList.add('red');
      else lowStockCard.classList.remove('red');
    }
  }

  getFilteredFilaments() {
    return this.filaments.filter(f => {
      const matchesMaterial = !this.currentFilterMaterial ||
        f.material_type.toUpperCase() === this.currentFilterMaterial.toUpperCase();
      const matchesSearch = !this.currentSearch ||
        f.name.toLowerCase().includes(this.currentSearch.toLowerCase()) ||
        f.color_name.toLowerCase().includes(this.currentSearch.toLowerCase()) ||
        f.color_hex.toLowerCase().includes(this.currentSearch.toLowerCase()) ||
        (f.vendor_name && f.vendor_name.toLowerCase().includes(this.currentSearch.toLowerCase())) ||
        (f.notes && f.notes.toLowerCase().includes(this.currentSearch.toLowerCase()));
      const matchesLowStock = !this.currentLowStockOnly ||
        (f.current_weight_kg <= f.initial_weight_kg * 0.2);

      return matchesMaterial && matchesSearch && matchesLowStock;
    });
  }

  toggleLowStockFilter() {
    this.currentLowStockOnly = !this.currentLowStockOnly;
    const pill = document.getElementById('low-stock-pill');
    if (pill) {
      if (this.currentLowStockOnly) pill.classList.add('active');
      else pill.classList.remove('active');
    }
    this.renderFilaments();
  }

  parseColorCode(input) {
    if (!input) return "#888";
    const clean = input.trim().toUpperCase();
    if (RAL_COLORS[clean]) return RAL_COLORS[clean];
    if (clean.startsWith("RAL ") && RAL_COLORS[clean]) return RAL_COLORS[clean];
    if (/^\d{4}$/.test(clean) && RAL_COLORS[`RAL ${clean}`]) return RAL_COLORS[`RAL ${clean}`];
    if (clean.startsWith("#")) return clean;
    return `#${clean}`;
  }

  updateColorPreview(val) {
    const hex = this.parseColorCode(val);
    const picker = document.getElementById('field-color-picker');
    if (picker && hex.startsWith('#') && hex.length === 7) picker.value = hex;
  }

  syncColorPicker(hex) {
    document.getElementById('field-color-code').value = hex.toUpperCase();
  }

  renderFilaments() {
    const grid = document.getElementById('filament-grid');
    if (!grid) return;

    const items = this.getFilteredFilaments();
    if (items.length === 0) {
      grid.innerHTML = `
        <div style="grid-column: 1 / -1; text-align: center; padding: 4rem 1.5rem; color: var(--text-muted); background: var(--card-bg); border: 1px dashed var(--card-border); border-radius: var(--radius-lg);">
          <div style="font-size: 3.5rem; margin-bottom: 0.8rem;">🧵</div>
          <h3 style="font-family: var(--font-heading); font-size: 1.5rem; margin-bottom: 0.5rem;">No spools found</h3>
          <p style="margin-bottom: 1.5rem; max-width: 450px; margin-left: auto; margin-right: auto; line-height: 1.5;">
            Your warehouse is empty or no spools match the current filter. Add your first filament spool to get started!
          </p>
          <button class="btn btn-primary btn-lg" onclick="app.openAddModal()" style="margin: 0 auto;">
            <i class="fas fa-plus-circle"></i> Add First Spool
          </button>
        </div>
      `;
      return;
    }

    grid.innerHTML = items.map(f => this.createFilamentCardHTML(f)).join('');
  }

  createFilamentCardHTML(f) {
    const remainingPct = Math.min(100, Math.max(0, (f.current_weight_kg / f.initial_weight_kg) * 100));
    const isLow = remainingPct <= 20;

    const vendorHTML = f.vendor_name
      ? (f.vendor_link
          ? `<a href="${f.vendor_link}" target="_blank" rel="noopener" class="vendor-link"><i class="fas fa-external-link-alt"></i> ${escapeHTML(f.vendor_name)}</a>`
          : `<span>${escapeHTML(f.vendor_name)}</span>`)
      : `<span style="color:var(--text-muted); font-style:italic;">Unknown Vendor</span>`;

    const latestPriceDisplay = (f.latest_price !== null && f.latest_price !== undefined)
      ? `${f.latest_currency === 'USD' ? '$' : f.latest_currency === 'CZK' ? 'Kč ' : '€'}${f.latest_price.toFixed(2)}`
      : 'N/A';

    const priceCount = f.price_history ? f.price_history.length : 0;
    const resolvedHex = this.parseColorCode(f.color_hex);

    const colorStyle = f.color_image_url
      ? `background-image: url('${f.color_image_url}');`
      : `background-color: ${resolvedHex};`;

    const addedDateStr = f.created_at ? new Date(f.created_at).toLocaleDateString() : '';

    return `
      <div class="filament-card" id="filament-card-${f.id}">
        <div>
          <div class="card-header">
            <div class="color-preview" style="${colorStyle}">
              <span class="material-badge">${escapeHTML(f.material_type)}</span>
            </div>
            <div class="filament-title-area">
              <h3 class="filament-name">${escapeHTML(f.name)}</h3>
              <div class="filament-color-name">
                <i class="fas fa-palette" style="color: ${resolvedHex}"></i>
                ${escapeHTML(f.color_name)}
                <span class="hex-chip">${escapeHTML(f.color_hex)}</span>
              </div>
            </div>
          </div>

          <div class="vendor-row">
            <span><i class="fas fa-building"></i> Vendor: ${vendorHTML}</span>
            <span style="font-size:0.75rem; color:var(--text-muted);"><i class="fas fa-calendar-alt"></i> ${addedDateStr}</span>
          </div>

          <div class="weight-section">
            <div class="weight-header">
              <span><i class="fas fa-balance-scale"></i> Weight Remaining:</span>
              <span class="weight-amount ${isLow ? 'text-danger' : ''}">${f.current_weight_kg.toFixed(2)} / ${f.initial_weight_kg.toFixed(2)} kg</span>
            </div>
            <div class="progress-bar-track">
              <div class="progress-bar-fill ${isLow ? 'low' : ''}" style="width: ${remainingPct}%"></div>
            </div>
          </div>
        </div>

        <div class="card-footer-row">
          <div class="price-tag" onclick="app.openPriceHistoryModal(${f.id})" title="Click to view purchase history">
            <span class="label">Latest Price (${priceCount} logged)</span>
            <span class="val">${latestPriceDisplay} <i class="fas fa-history" style="font-size:0.75rem; margin-left:2px;"></i></span>
          </div>

          <div class="card-actions">
            <button class="action-icon-btn" onclick="app.openWeightUpdateModal(${f.id})" title="Update Weight / Scan NFC">
              <i class="fas fa-wifi"></i>
            </button>
            <button class="action-icon-btn" onclick="app.openEditModal(${f.id})" title="Edit Spool">
              <i class="fas fa-edit"></i>
            </button>
            <button class="action-icon-btn" onclick="app.handleDeleteFilament(${f.id})" title="Delete Spool">
              <i class="fas fa-trash-alt"></i>
            </button>
          </div>
        </div>
      </div>
    `;
  }

  populateExistingSelect() {
    const select = document.getElementById('field-existing-select');
    if (!select) return;

    const uniqueMap = new Map();
    this.filaments.forEach(f => {
      if (!uniqueMap.has(f.name)) uniqueMap.set(f.name, f);
    });

    let optionsHTML = `<option value="NEW">+ Create New Filament Product</option>`;
    uniqueMap.forEach((f, name) => {
      optionsHTML += `<option value="${f.id}">Existing: ${escapeHTML(f.name)} (${escapeHTML(f.material_type)} - ${escapeHTML(f.color_name)})</option>`;
    });

    select.innerHTML = optionsHTML;
  }

  handleExistingSelectChange(val) {
    if (val === "NEW") {
      document.getElementById('field-name').value = "";
      document.getElementById('field-material').value = "PLA";
      document.getElementById('field-color-name').value = "";
      document.getElementById('field-color-code').value = "#FFFFFF";
      document.getElementById('field-vendor-name').value = "";
      document.getElementById('field-vendor-link').value = "";
      return;
    }

    const fil = this.filaments.find(f => f.id === parseInt(val));
    if (!fil) return;

    document.getElementById('field-name').value = fil.name;
    document.getElementById('field-material').value = fil.material_type;
    document.getElementById('field-color-name').value = fil.color_name;
    document.getElementById('field-color-code').value = fil.color_hex;
    document.getElementById('field-vendor-name').value = fil.vendor_name || "";
    document.getElementById('field-vendor-link').value = fil.vendor_link || "";
    if (fil.latest_price !== null && fil.latest_price !== undefined) {
      document.getElementById('field-buy-price').value = fil.latest_price;
    }
  }

  openAddModal() {
    this.editingFilamentId = null;
    document.getElementById('filament-modal-title').textContent = "+ Add New Filament Spool";
    document.getElementById('filament-form').reset();
    this.populateExistingSelect();
    const todayStr = new Date().toISOString().split('T')[0];
    document.getElementById('field-bought-at').value = todayStr;
    document.getElementById('field-color-code').value = "#FFFFFF";
    document.getElementById('field-color-picker').value = "#FFFFFF";
    document.getElementById('select-existing-group').style.display = "block";
    document.getElementById('buy-price-group').style.display = "block";
    openModal('filament-modal');
  }

  openEditModal(id) {
    const fil = this.filaments.find(f => f.id === id);
    if (!fil) return;

    this.editingFilamentId = id;
    document.getElementById('filament-modal-title').textContent = "Edit Filament Spool";
    document.getElementById('select-existing-group').style.display = "none";

    document.getElementById('field-name').value = fil.name;
    document.getElementById('field-material').value = fil.material_type;
    document.getElementById('field-color-name').value = fil.color_name;
    document.getElementById('field-color-code').value = fil.color_hex || "#FFFFFF";
    document.getElementById('field-color-image').value = fil.color_image_url || "";
    document.getElementById('field-vendor-name').value = fil.vendor_name || "";
    document.getElementById('field-vendor-link').value = fil.vendor_link || "";
    document.getElementById('field-initial-weight').value = fil.initial_weight_kg;
    document.getElementById('field-current-weight').value = fil.current_weight_kg;
    document.getElementById('field-nfc-uid').value = fil.nfc_tag_uid || "";
    document.getElementById('field-notes').value = fil.notes || "";

    const dateStr = fil.created_at ? new Date(fil.created_at).toISOString().split('T')[0] : new Date().toISOString().split('T')[0];
    document.getElementById('field-bought-at').value = dateStr;
    document.getElementById('buy-price-group').style.display = "block";
    openModal('filament-modal');
  }

  async handleSaveFilament(e) {
    e.preventDefault();

    const boughtAtVal = document.getElementById('field-bought-at').value;
    const boughtAtIso = boughtAtVal ? new Date(boughtAtVal).toISOString() : new Date().toISOString();

    const payload = {
      name: document.getElementById('field-name').value,
      material_type: document.getElementById('field-material').value,
      color_name: document.getElementById('field-color-name').value,
      color_hex: document.getElementById('field-color-code').value,
      color_image_url: document.getElementById('field-color-image').value || null,
      vendor_name: document.getElementById('field-vendor-name').value || null,
      vendor_link: document.getElementById('field-vendor-link').value || null,
      initial_weight_kg: parseFloat(document.getElementById('field-initial-weight').value),
      current_weight_kg: parseFloat(document.getElementById('field-current-weight').value),
      nfc_tag_uid: document.getElementById('field-nfc-uid').value || null,
      notes: document.getElementById('field-notes').value || null,
      bought_at: boughtAtIso
    };

    try {
      let res;
      const headers = auth && auth.getAuthHeaders ? auth.getAuthHeaders({ "Content-Type": "application/json" }) : { "Content-Type": "application/json" };
      if (this.editingFilamentId) {
        res = await fetch(`/api/filaments/${this.editingFilamentId}`, {
          method: "PUT",
          headers,
          body: JSON.stringify(payload)
        });
      } else {
        const rawPrice = document.getElementById('field-buy-price').value;
        payload.buy_price = rawPrice !== "" ? parseFloat(rawPrice) : 0.0;
        payload.currency = document.getElementById('field-currency').value || "EUR";
        res = await fetch("/api/filaments", {
          method: "POST",
          headers,
          body: JSON.stringify(payload)
        });
      }

      const text = await res.text();
      let data = {};
      try { data = text ? JSON.parse(text) : {}; } catch { data = { detail: text || "Save failed" }; }
      if (!res.ok) throw new Error(data.detail || "Save failed");

      showToast("Spool saved successfully!", "success");
      closeModal('filament-modal');
      await this.loadFilaments();
    } catch (err) {
      showToast(err.message, "danger");
    }
  }

  async handleDeleteFilament(id) {
    if (!confirm("Delete this filament spool?")) return;

    try {
      const headers = auth && auth.getAuthHeaders ? auth.getAuthHeaders() : {};
      const res = await fetch(`/api/filaments/${id}`, { method: "DELETE", headers });
      if (!res.ok) throw new Error("Could not delete filament");
      showToast("Spool deleted.", "info");
      await this.loadFilaments();
    } catch (err) {
      showToast(err.message, "danger");
    }
  }

  async openPriceHistoryModal(filamentId) {
    const fil = this.filaments.find(f => f.id === filamentId);
    if (!fil) return;

    this.activeFilamentId = filamentId;
    document.getElementById('price-history-modal-title').textContent = `Price History — ${fil.name}`;

    const todayStr = new Date().toISOString().split('T')[0];
    document.getElementById('hist-bought-at').value = todayStr;

    try {
      const headers = auth && auth.getAuthHeaders ? auth.getAuthHeaders() : {};
      const res = await fetch(`/api/filaments/${filamentId}/prices`, { headers });
      const history = await res.json();

      const listContainer = document.getElementById('price-history-list');
      if (history.length === 0) {
        listContainer.innerHTML = `<p style="color:var(--text-muted); text-align:center;">No price history logged yet.</p>`;
      } else {
        listContainer.innerHTML = history.map(p => `
          <div style="background: rgba(0,0,0,0.3); border:1px solid var(--card-border); border-radius: 8px; padding: 0.8rem; margin-bottom:0.6rem; display:flex; align-items:center; justify-content:space-between;">
            <div>
              <div style="font-weight:700; font-size:1.1rem; color:var(--accent-primary);">
                ${p.currency === 'USD' ? '$' : p.currency === 'CZK' ? 'Kč ' : '€'}${p.price.toFixed(2)}
              </div>
              <div style="font-size:0.8rem; color:var(--text-muted);">
                ${p.store_name ? escapeHTML(p.store_name) + ' • ' : ''}${new Date(p.bought_at).toLocaleDateString()}
              </div>
            </div>
            <div style="font-size:0.85rem; color:var(--text-muted); text-align:right;">
              ${p.quantity_bought} spool(s)
              ${p.notes ? `<div style="font-size:0.75rem; font-style:italic;">${escapeHTML(p.notes)}</div>` : ''}
            </div>
          </div>
        `).join('');
      }

      openModal('price-history-modal');
    } catch (err) {
      showToast("Error loading price history: " + err.message, "danger");
    }
  }

  async handleAddPriceHistory(e) {
    e.preventDefault();
    if (!this.activeFilamentId) return;

    const boughtAtVal = document.getElementById('hist-bought-at').value;
    const boughtAtIso = boughtAtVal ? new Date(boughtAtVal).toISOString() : new Date().toISOString();

    const payload = {
      price: parseFloat(document.getElementById('hist-price').value),
      currency: document.getElementById('hist-currency').value,
      store_name: document.getElementById('hist-store').value || null,
      notes: document.getElementById('hist-notes').value || null,
      bought_at: boughtAtIso
    };

    try {
      const headers = auth && auth.getAuthHeaders ? auth.getAuthHeaders({ "Content-Type": "application/json" }) : { "Content-Type": "application/json" };
      const res = await fetch(`/api/filaments/${this.activeFilamentId}/prices`, {
        method: "POST",
        headers,
        body: JSON.stringify(payload)
      });
      const text = await res.text();
      let data = {};
      try { data = text ? JSON.parse(text) : {}; } catch { data = { detail: text || "Failed to add price record" }; }
      if (!res.ok) throw new Error(data.detail || "Failed to add price record");

      showToast("Price record added!", "success");
      document.getElementById('price-history-form').reset();
      await this.openPriceHistoryModal(this.activeFilamentId);
      await this.loadFilaments();
    } catch (err) {
      showToast(err.message, "danger");
    }
  }

  openWeightUpdateModal(id) {
    const fil = this.filaments.find(f => f.id === id);
    if (!fil) return;

    this.activeFilamentId = id;
    document.getElementById('nfc-sim-tag-input').value = fil.nfc_tag_uid || `NFC-SPOOL-00${fil.id}`;
    document.getElementById('nfc-sim-weight-input').value = fil.current_weight_kg;

    nfcSystem.startNFCScan(async (scanData) => {
      await this.processNFCScan(scanData);
    });
  }

  async processNFCScan(scanData) {
    try {
      const headers = auth && auth.getAuthHeaders ? auth.getAuthHeaders({ "Content-Type": "application/json" }) : { "Content-Type": "application/json" };
      const res = await fetch("/api/nfc/update-weight", {
        method: "POST",
        headers,
        body: JSON.stringify({
          nfc_tag_uid: scanData.tag_uid,
          current_weight_kg: scanData.current_weight_kg
        })
      });
      const text = await res.text();
      let result = {};
      try { result = text ? JSON.parse(text) : {}; } catch { result = { success: false, message: text || "NFC update failed" }; }
      if (result.success) {
        showToast(result.message, "success");
        await this.loadFilaments();
      } else {
        showToast(result.message, "warning");
      }
    } catch (err) {
      showToast("NFC Processing error: " + err.message, "danger");
    }
  }
}

// Helpers
function escapeHTML(str) {
  if (!str) return '';
  return String(str).replace(/[&<>'"]/g,
    tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
  );
}

function openModal(id) {
  const m = document.getElementById(id);
  if (m) m.classList.add('active');
}

function closeModal(id) {
  const m = document.getElementById(id);
  if (m) m.classList.remove('active');
}

function showToast(message, type = "info") {
  const toastContainer = document.getElementById('toast-container');
  if (!toastContainer) return;

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.style.cssText = `
    background: ${type === 'danger' ? '#EF4444' : type === 'success' ? '#10B981' : type === 'warning' ? '#F59E0B' : '#1E88E5'};
    color: #FFF;
    font-family: var(--font-heading);
    font-weight: 600;
    padding: 0.8rem 1.2rem;
    border-radius: 10px;
    margin-top: 0.5rem;
    box-shadow: 0 4px 15px rgba(0,0,0,0.4);
    transition: all 0.3s ease;
  `;
  toast.innerHTML = message;
  toastContainer.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

try {
  const savedTheme = localStorage.getItem('filament-theme') || 'dark';
  applyTheme(savedTheme);
} catch (err) {
  applyTheme('dark');
}

const app = new WarehouseApp();
