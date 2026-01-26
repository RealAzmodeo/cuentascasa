lucide.createIcons();
let currentConfig = {
    taxonomy: {},
    preferred_accounts: ["Germán", "eToro", "Esposa", "Efectivo"]
};
let currentAnalytics = null;
let selectedMonthKey = null;
let selectedAccount = null; // null means "Total"
let charts = {};

const API_BASE = 'http://127.0.0.1:5000';

async function init() {
    // Force hide any persistent loading state on startup
    const proc = document.getElementById('bank-processing');
    if (proc) proc.style.display = 'none';

    // 0. Bootstrap from Cache (Immediate UI)
    bootstrapFromCache();

    // File Upload Listeners
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('bank-file-input');
    if (dropZone && fileInput) {
        dropZone.onclick = () => fileInput.click();
        fileInput.onchange = (e) => { if (e.target.files.length) handleBankFile(e.target.files[0]); };
        dropZone.ondragover = (e) => { e.preventDefault(); dropZone.classList.add('dragover'); };
        dropZone.ondragleave = () => dropZone.classList.remove('dragover');
        dropZone.ondrop = (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
            if (e.dataTransfer.files.length) handleBankFile(e.dataTransfer.files[0]);
        };
    }

    try {
        await refreshConfig();
        await refreshData();
    } catch (e) {
        console.error("Error during initial data fetch:", e);
        // Don't alert if we already have cached data, just log it
        if (!currentAnalytics) alert("Error de conexión. Comprueba que el servidor esté activo.");
    }

    document.getElementById('searchInput').oninput = debounce(search, 300);
    document.getElementById('aiInput').onkeypress = (e) => { if (e.key === 'Enter') sendAI(); };
    fetchInsights();
    lucide.createIcons();
}

function bootstrapFromCache() {
    try {
        const cachedConfig = localStorage.getItem('app_config');
        const cachedAnalytics = localStorage.getItem('app_analytics');
        const cachedSummary = localStorage.getItem('app_summary');
        const cachedPending = localStorage.getItem('app_pending_tx');

        if (cachedConfig) {
            currentConfig = JSON.parse(cachedConfig);
            updateUIWithConfig();
        }
        if (cachedAnalytics && cachedSummary) {
            currentAnalytics = JSON.parse(cachedAnalytics);
            const summary = JSON.parse(cachedSummary);
            updateUIWithData(summary, currentAnalytics);
        }
        if (cachedPending) {
            const data = JSON.parse(cachedPending);
            pendingTransactions = data.transactions;
            renderBankPreview(pendingTransactions, data.account);
        }
    } catch (e) { console.warn("Cache bootstrap failed:", e); }
}

function updateUIWithConfig() {
    // Update input categories
    const selCat = document.getElementById('in-cat');
    if (selCat) {
        selCat.innerHTML = '';
        Object.keys(currentConfig.taxonomy).forEach(c => {
            const opt = document.createElement('option'); opt.value = c; opt.textContent = c;
            selCat.appendChild(opt);
        });
    }

    // Update account selectors
    const accounts = currentConfig.preferred_accounts || ["Germán", "eToro", "Esposa", "Efectivo"];
    ['in-acc', 'ai-acc'].forEach(id => {
        const sel = document.getElementById(id);
        if (!sel) return;
        sel.innerHTML = accounts.map(acc => `<option value="${acc}">${acc}</option>`).join('') + '<option value="new">+ Nueva...</option>';
        sel.onchange = (e) => {
            if (e.target.value === 'new') {
                const name = prompt("Nombre de la nueva cuenta:");
                if (name) {
                    const opt = document.createElement('option');
                    opt.value = name; opt.textContent = name;
                    sel.insertBefore(opt, sel.lastElementChild);
                    sel.value = name;
                } else sel.selectedIndex = 0;
            }
        };
    });
}

async function apiFetch(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, options);
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (e) {
        console.error("Fetch error:", e);
        if (e.message.includes('fetch')) {
            throw new Error("Error de conexión con el servidor. Asegúrate de que Flask esté ejecutándose.");
        }
        throw e;
    }
}

async function refreshConfig() {
    try {
        currentConfig = await apiFetch('/config');
        localStorage.setItem('app_config', JSON.stringify(currentConfig));
        updateUIWithConfig();
    } catch (e) { console.error("refreshConfig error:", e); }
}

async function refreshData() {
    const accParam = selectedAccount ? `?account=${encodeURIComponent(selectedAccount)}` : '';
    try {
        const [summary, analytics] = await Promise.all([
            apiFetch(`/summary${accParam}`),
            apiFetch(`/analytics${accParam}`)
        ]);
        currentAnalytics = analytics;
        localStorage.setItem('app_analytics', JSON.stringify(analytics));
        localStorage.setItem('app_summary', JSON.stringify(summary));
        updateUIWithData(summary, analytics);
    } catch (e) {
        console.error("refreshData error:", e);
    }
}

function updateUIWithData(summary, analytics) {
    if (!selectedMonthKey) {
        selectedMonthKey = analytics.current_month_key;
    }

    // Update selectors
    populateMonthSelectors();

    // Home Updates: Header card should show Monthly performance
    const currentMonthData = analytics.months[selectedMonthKey] || { total: 0, income: 0, categories: {} };
    const homeBalance = document.getElementById('home-balance');
    if (homeBalance) homeBalance.textContent = `€${summary.savings.toLocaleString('es-ES')}`;

    const homeIncome = document.getElementById('home-income');
    if (homeIncome) homeIncome.textContent = `+€${(currentMonthData.income || 0).toLocaleString('es-ES')}`;

    const homeExpense = document.getElementById('home-expense');
    if (homeExpense) homeExpense.textContent = `-€${(currentMonthData.total || 0).toLocaleString('es-ES')}`;

    // Add "Mes" labels to avoid confusion
    if (homeIncome) homeIncome.innerHTML = `<span style="font-size:0.6rem; opacity:0.7; display:block;">INGRESOS MES</span>+€${(currentMonthData.income || 0).toLocaleString('es-ES')}`;
    if (homeExpense) homeExpense.innerHTML = `<span style="font-size:0.6rem; opacity:0.7; display:block;">GASTOS MES</span>-€${(currentMonthData.total || 0).toLocaleString('es-ES')}`;

    // Timeline Updates
    const tBalance = document.getElementById('timeline-balance');
    if (tBalance) {
        tBalance.textContent = `€${summary.savings.toLocaleString('es-ES')}`;
        document.getElementById('timeline-income').textContent = `+€${summary.total_income.toLocaleString('es-ES')}`;
        document.getElementById('timeline-expense').textContent = `-€${summary.total_expense.toLocaleString('es-ES')}`;
    }

    renderBudgets();
    renderCategoryFilters();
    renderAccountFilters();

    // Re-render active views
    if (document.getElementById('view-search').classList.contains('active')) search();
    if (document.getElementById('view-home').classList.contains('active')) renderBudgets();
    if (document.getElementById('view-analytics').classList.contains('active')) renderAnalytics();
    if (document.getElementById('view-comparisons').classList.contains('active')) renderComparisons();
}

function renderAccountFilters() {
    if (!currentConfig) return;
    const filterContainers = [
        'home-account-filters',
        'timeline-account-filters',
        'analytics-account-filters',
        'comparisons-account-filters'
    ];

    const accounts = currentConfig.preferred_accounts || ["Germán"];

    filterContainers.forEach(id => {
        const container = document.getElementById(id);
        if (!container) return;

        const isHome = id === 'home-account-filters';
        let html = `<div class="filter-chip ${!selectedAccount ? 'active' : ''}" onclick="setAccountFilter(null, this)">${isHome ? 'Total' : 'Todas'}</div>` +
            accounts.map(acc => `
                <div class="filter-chip ${selectedAccount === acc ? 'active' : ''}" onclick="setAccountFilter('${acc}', this)">
                    ${acc}
                </div>
            `).join('') +
            `<div class="filter-chip btn-add-acc" onclick="openAccountModal()"><i data-lucide="plus" size="14"></i> Agregar Cuenta</div>`;

        if (accounts.length === 0 && isHome) {
            html = `<div class="filter-chip btn-add-acc" style="width:100%; justify-content:center; border-style:solid; background:rgba(229, 75, 75, 0.05); color:var(--vhs-red); padding: 12px;" onclick="openAccountModal()">
                <i data-lucide="plus-circle" size="16"></i> Crea tu primera cuenta para empezar
            </div>`;
        }

        container.innerHTML = html;
    });

    const balLabel = document.getElementById('balance-label');
    const accPill = document.getElementById('account-pill');
    if (selectedAccount) {
        if (balLabel) balLabel.textContent = "Balance de Cuenta";
        if (accPill) {
            accPill.innerHTML = `<span>${selectedAccount.toUpperCase()}</span><i data-lucide="edit-3" size="12" style="margin-left:4px; opacity:0.7;"></i>`;
            accPill.style.display = 'inline-flex';
            accPill.style.padding = '6px 14px';
            accPill.style.borderRadius = '50px';
            accPill.style.background = 'rgba(255,255,255,0.15)';
            accPill.style.border = '1px solid rgba(255,255,255,0.25)';
            accPill.style.fontSize = '0.7rem';
            accPill.style.fontWeight = '700';
            accPill.style.letterSpacing = '0.5px';
            accPill.onclick = () => openAccountModal(selectedAccount);
            accPill.style.cursor = 'pointer';
            lucide.createIcons();
        }
    } else {
        if (balLabel) balLabel.textContent = "Balance Total";
        if (accPill) accPill.style.display = 'none';
        // When total is selected, also make sure we use 'Total' as the label if multiple accounts exist
    }
}

function setAccountFilter(acc, el) {
    selectedAccount = acc;
    renderAccountFilters();
    refreshData();
}

function populateMonthSelectors() {
    const selectors = ['month-selector', 'month-selector-ana'];
    selectors.forEach(id => {
        const sel = document.getElementById(id);
        if (!sel) return;
        sel.innerHTML = '';
        currentAnalytics.sorted_months.forEach(m => {
            const opt = document.createElement('option');
            opt.value = m;
            opt.textContent = formatMonthKey(m);
            if (m === selectedMonthKey) opt.selected = true;
            sel.appendChild(opt);
        });
    });
}

function formatMonthKey(key) {
    const [y, m] = key.split('-');
    const d = new Date(y, m - 1);
    return d.toLocaleDateString('es-ES', { month: 'long', year: 'numeric' }).toUpperCase();
}

function changeMonth(m) {
    selectedMonthKey = m;
    const s1 = document.getElementById('month-selector');
    const s2 = document.getElementById('month-selector-ana');
    if (s1) s1.value = m;
    if (s2) s2.value = m;
    refreshData();
}

let activeFilters = { category: null, minAmount: 0 };

function renderCategoryFilters() {
    const container = document.getElementById('category-filters');
    if (!container) return;
    const currentCat = activeFilters.category;
    container.innerHTML = `<div class="filter-chip ${!currentCat ? 'active' : ''}" onclick="setCategoryFilter(null, this)">Todas</div>`;

    Object.keys(currentConfig.taxonomy).forEach(cat => {
        const chip = document.createElement('div');
        chip.className = `filter-chip ${currentCat === cat ? 'active' : ''}`;
        chip.textContent = cat;
        chip.onclick = () => setCategoryFilter(cat, chip);
        container.appendChild(chip);
    });
}

function setCategoryFilter(cat, el) {
    document.querySelectorAll('#category-filters .filter-chip').forEach(c => c.classList.remove('active'));
    el.classList.add('active');
    activeFilters.category = cat;
    search();
}

function renderBudgets() {
    const list = document.getElementById('budget-list');
    if (!list) return;
    list.innerHTML = '';
    const currentMonthData = currentAnalytics.months[selectedMonthKey] || { categories: {}, top_transactions: {} };
    const cats = currentMonthData.categories;

    Object.entries(currentConfig.taxonomy).forEach(([name, cfg]) => {
        if (cfg.budget === 0 || name === 'Ingresos') return;
        const spent = cats[name] || 0;
        const perc = Math.min((spent / cfg.budget * 100), 100).toFixed(0);
        const isExceeded = spent > cfg.budget;

        const div = document.createElement('div');
        div.className = 'budget-row';
        div.style.cursor = 'pointer';
        div.onclick = () => {
            const details = div.querySelector('.budget-details');
            if (details) details.style.display = details.style.display === 'block' ? 'none' : 'block';
        };

        const topExp = currentMonthData.top_transactions[name] || [];

        div.innerHTML = `
            <div class="budget-header">
                <div class="m-icon-bank" style="width:32px; height:32px; background:var(--bg-cream); color:var(--text-charcoal)">
                    <i data-lucide="${getIcon(name)}" size="16"></i>
                </div>
                <div style="flex:1;">
                    <div class="cat-name">${name}</div>
                    <div style="font-size:0.6rem; color:var(--text-muted);">
                       Gasto actual: €${spent.toFixed(0)} / €${cfg.budget}
                    </div>
                </div>
                <div class="budget-stats">
                    <span class="spent-amount" style="color:${isExceeded ? 'var(--vhs-red)' : 'inherit'}">${perc}%</span>
                </div>
            </div>
            <div class="progress-container">
                <div class="progress-segment" style="width:${perc}%; background:${isExceeded ? 'var(--vhs-red)' : 'var(--sage-green)'};"></div>
            </div>
            <div class="budget-details">
                <div style="font-size: 0.65rem; font-weight: 800; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">Desglose de Gastos</div>
                ${topExp.map(t => `
                    <div class="detailed-expense">
                        <div class="exp-info">
                            <span class="exp-date">${t.fecha}</span>
                            <span>${t.detalle}</span>
                        </div>
                        <div class="exp-amount">€${t.monto.toLocaleString('es-ES', { minimumFractionDigits: 2 })}</div>
                    </div>
                `).join('')}
            </div>
        `;
        list.appendChild(div);
    });
    lucide.createIcons();
}

async function fetchInsights() {
    const banner = document.getElementById('ai-insight');
    const txt = document.getElementById('insight-text');
    if (!banner || !txt) return;
    banner.style.display = 'flex';
    txt.textContent = "Analizando tus finanzas...";
    try {
        const data = await apiFetch('/insights');
        txt.textContent = data.insight;
    } catch (e) {
        txt.textContent = "No hay consejos disponibles ahora.";
    }
}

function switchTab(tabId, el) {
    document.querySelectorAll('.app-view').forEach(v => v.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    const target = document.getElementById('view-' + tabId);
    if (target) target.classList.add('active');
    el.classList.add('active');

    if (tabId === 'analytics') renderAnalytics();
    if (tabId === 'comparisons') renderComparisons();
    if (tabId === 'search') search();
    lucide.createIcons();
}

function renderAnalytics() {
    const currentMonthData = currentAnalytics.months[selectedMonthKey] || { categories: {} };
    const cats = Object.entries(currentMonthData.categories).sort((a, b) => b[1] - a[1]);
    const total = Object.values(currentMonthData.categories).reduce((a, b) => a + b, 0);

    const ctx = document.getElementById('anaChart').getContext('2d');
    if (charts.ana) charts.ana.destroy();
    charts.ana = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: cats.map(c => c[0]),
            datasets: [{
                data: cats.map(c => c[1]),
                backgroundColor: ['#E54B4B', '#F78C58', '#E8B059', '#889E81', '#5D737E', '#2C2C2C'],
                borderWidth: 0
            }]
        },
        options: { cutout: '75%', plugins: { legend: { display: false } } }
    });

    const list = document.getElementById('ana-list');
    list.innerHTML = '';
    cats.forEach(([name, val], i) => {
        const perc = total > 0 ? (val / total * 100).toFixed(0) : 0;
        const div = document.createElement('div');
        div.className = 'm-item';
        div.innerHTML = `
            <div class="m-icon" style="color:white; background:${['#E54B4B', '#F78C58', '#E8B059', '#889E81', '#5D737E', '#2C2C2C'][i % 6]}"><i data-lucide="${getIcon(name)}"></i></div>
            <div class="m-info">
                <div class="m-title">${name}</div>
                <div class="m-sub">${perc}% del gasto total</div>
            </div>
            <div class="m-amount">€${val.toLocaleString('es-ES')}</div>
        `;
        list.appendChild(div);
    });
    lucide.createIcons();
}

function renderComparisons() {
    const hist = currentAnalytics.history;
    const ctx = document.getElementById('historyChart').getContext('2d');
    if (charts.hist) charts.hist.destroy();
    charts.hist = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: hist.map(h => h.month),
            datasets: [{
                data: hist.map(h => h.total),
                backgroundColor: hist.map((_, i) => i === hist.length - 1 ? 'var(--vhs-red)' : 'var(--slate-blue)'),
                borderRadius: 8
            }]
        },
        options: { plugins: { legend: { display: false } }, scales: { y: { display: false }, x: { grid: { display: false } } } }
    });

    const advice = document.getElementById('comp-advice');
    const latest = hist[hist.length - 1];
    const mom = latest ? latest.growth : 0;
    advice.innerHTML = `
        <div style="font-weight:700; font-size:1.2rem; color:${mom > 0 ? 'var(--vhs-red)' : 'var(--sage-green)'}">
            ${mom > 0 ? '↑' : '↓'} ${Math.abs(mom).toFixed(1)}% vs mes pasado
        </div>
        <div style="font-size:0.85rem; color:var(--text-muted); margin-top:5px;">
            ${mom > 0 ? 'Tus gastos han subido. Revisa tus presupuestos.' : '¡Genial! Estás gastando menos que el mes pasado.'}
        </div>
    `;

    // Render 3-color comparison bars
    const list = document.getElementById('comp-budget-list');
    if (!list) return;
    list.innerHTML = '';

    if (!currentConfig || !currentConfig.taxonomy) {
        list.innerHTML = '<div style="text-align:center; padding:20px; color:var(--text-muted);">Cargando presupuestos...</div>';
        return;
    }

    const currentMonthData = currentAnalytics.months[selectedMonthKey] || { categories: {} };
    const cats = currentMonthData.categories;
    const months = currentAnalytics.sorted_months;
    const idx = months.indexOf(selectedMonthKey);
    const prevMonthKey = idx > 0 ? months[idx - 1] : null;
    const prevMonthData = prevMonthKey ? currentAnalytics.months[prevMonthKey] : null;

    Object.entries(currentConfig.taxonomy).forEach(([name, cfg]) => {
        if (cfg.budget === 0 || name === 'Ingresos') return;
        const spent = cats[name] || 0;
        const prevSpent = prevMonthData ? (prevMonthData.categories[name] || 0) : 0;

        const maxLimit = Math.max(spent, cfg.budget, prevSpent);
        if (maxLimit === 0) return;

        const greenWidth = (Math.min(spent, cfg.budget) / maxLimit * 100).toFixed(1);
        let orangeWidth = 0;
        if (spent > cfg.budget) {
            orangeWidth = (Math.min(spent - cfg.budget, Math.max(0, prevSpent - cfg.budget)) / maxLimit * 100).toFixed(1);
        }
        let redWidth = 0;
        if (spent > prevSpent && spent > cfg.budget) {
            redWidth = ((spent - Math.max(cfg.budget, prevSpent)) / maxLimit * 100).toFixed(1);
        }

        const div = document.createElement('div');
        div.className = 'budget-row';
        div.innerHTML = `
            <div class="budget-header">
                <div class="m-icon-bank" style="width:32px; height:32px; background:var(--bg-cream); color:var(--text-charcoal)">
                    <i data-lucide="${getIcon(name)}" size="16"></i>
                </div>
                <div style="flex:1;">
                    <div class="cat-name">${name}</div>
                    <div style="font-size:0.6rem; color:var(--text-muted);">
                       €${spent.toFixed(0)} actual | €${cfg.budget} ppto | €${prevSpent.toFixed(0)} mes pas.
                    </div>
                </div>
            </div>
            <div class="progress-container">
                <div class="progress-segment" style="width:${greenWidth}%; background:var(--sage-green);"></div>
                <div class="progress-segment" style="width:${orangeWidth}%; background:var(--mustard);"></div>
                <div class="progress-segment" style="width:${redWidth}%; background:var(--vhs-red);"></div>
            </div>
        `;
        list.appendChild(div);
    });
    lucide.createIcons();
}

async function search() {
    const q = document.getElementById('searchInput').value.trim();
    const container = document.getElementById('search-results');
    if (!container) return;

    try {
        let data = [];
        if (!q) {
            const currentMonthData = currentAnalytics.months[selectedMonthKey];
            if (currentMonthData && currentMonthData.transactions) {
                data = [...currentMonthData.transactions];
            } else {
                container.innerHTML = '<div style="text-align:center; padding:40px; color:var(--text-muted);"><i data-lucide="info" size="32"></i> No hay movimientos.</div>';
                lucide.createIcons(); return;
            }
        } else {
            const accParam = selectedAccount ? `&account=${encodeURIComponent(selectedAccount)}` : '';
            data = await apiFetch(`/search?q=${encodeURIComponent(q)}${accParam}`);
        }

        if (selectedAccount) data = data.filter(m => m.cuenta === selectedAccount);
        if (activeFilters.category) data = data.filter(m => m.categoria === activeFilters.category);

        container.innerHTML = '';
        data.sort((a, b) => new Date(b.fecha) - new Date(a.fecha));

        const tree = {};
        data.forEach(m => {
            const date = new Date(m.fecha);
            const monthKey = date.toLocaleDateString('es-ES', { month: 'long', year: 'numeric' });
            if (!tree[monthKey]) tree[monthKey] = {};
            if (!tree[monthKey][m.fecha]) tree[monthKey][m.fecha] = [];
            tree[monthKey][m.fecha].push(m);
        });

        Object.keys(tree).forEach(month => {
            const mHeader = document.createElement('div');
            mHeader.className = 'month-header';
            mHeader.textContent = month;
            container.appendChild(mHeader);

            Object.keys(tree[month]).forEach(date => {
                const groupHeader = document.createElement('div');
                groupHeader.className = 'timeline-date-group';
                groupHeader.textContent = formatDateHuman(date);
                container.appendChild(groupHeader);

                tree[month][date].forEach(m => {
                    const div = document.createElement('div');
                    div.className = 'timeline-item';
                    div.style.gridTemplateColumns = '40px 1fr auto auto';
                    div.innerHTML = `
                        <div class="m-icon-bank"><i data-lucide="${getIcon(m.categoria)}"></i></div>
                        <div class="m-info">
                            <div style="display:flex; align-items:center; gap:8px;">
                                <div class="m-title" style="font-size:0.85rem;">${m.tienda || m.detalle}</div>
                                ${!selectedAccount ? `<span class="badge" style="font-size:0.5rem; padding:1px 4px;">${m.cuenta}</span>` : ''}
                            </div>
                            <div class="m-sub" style="font-size:0.65rem;">${m.categoria}</div>
                        </div>
                        <div class="m-amount" style="font-size:1rem; color:${m.tipo.toLowerCase() === 'gasto' ? 'inherit' : 'var(--sage-green)'}">
                            ${m.tipo.toLowerCase() === 'gasto' ? '-' : '+'}${m.monto.toLocaleString('es-ES')}€
                        </div>
                        <div class="btn-radial-edit" onclick="openEditModal(${JSON.stringify(m).replace(/"/g, '&quot;')})">
                            <i data-lucide="edit-3" size="14"></i>
                        </div>
                    `;
                    container.appendChild(div);
                });
            });
        });
        lucide.createIcons();
    } catch (e) {
        container.innerHTML = `<div style="text-align:center; padding:20px; color:var(--vhs-red);">Error al cargar resultados.</div>`;
    }
}

function formatDateHuman(dateStr) {
    const date = new Date(dateStr);
    const today = new Date();
    const yesterday = new Date();
    yesterday.setDate(today.getDate() - 1);
    if (date.toDateString() === today.toDateString()) return 'Hoy';
    if (date.toDateString() === yesterday.toDateString()) return 'Ayer';
    const options = { weekday: 'long', day: 'numeric', month: 'long' };
    let formatted = date.toLocaleDateString('es-ES', options);
    return formatted.charAt(0).toUpperCase() + formatted.slice(1);
}

// Bank Upload Logic
let pendingTransactions = [];

async function handleBankFile(file) {
    const proc = document.getElementById('bank-processing');
    const preview = document.getElementById('bank-preview');
    const drop = document.getElementById('drop-zone');
    if (proc) proc.style.display = 'block';
    if (preview) preview.style.display = 'none';
    if (drop) drop.style.display = 'none';

    const formData = new FormData();
    formData.append('file', file);

    try {
        const data = await apiFetch('/bank/process', { method: 'POST', body: formData });
        if (data.status === 'success') {
            data.transactions.forEach(t => t.selected = (t.status === 'new'));
            renderBankPreview(data.transactions, data.account_detected);
        } else {
            alert('Error: ' + data.message); resetBank();
        }
    } catch (e) {
        alert('Error: ' + e.message); resetBank();
    } finally {
        if (proc) proc.style.display = 'none';
    }
}

function renderBankPreview(transactions, detectedAccount) {
    pendingTransactions = transactions;
    // Cache pending state for snappiness
    localStorage.setItem('app_pending_tx', JSON.stringify({ transactions, account: detectedAccount }));

    const preview = document.getElementById('bank-preview');
    if (preview) preview.style.display = 'flex';

    renderIngestAccountSelector(detectedAccount);

    const list = document.getElementById('bank-new-list');
    list.innerHTML = ''; // Clear previous movements but keep the selector if it was there

    const categories = Object.keys(currentConfig.taxonomy);

    transactions.forEach((t, i) => {
        const div = document.createElement('div');
        div.className = 'bank-move-card';
        div.innerHTML = `
            <div class="bank-move-main">
                <div class="bank-move-header">
                    <span class="bank-move-title">${t.tienda || t.detalle}</span>
                    <span class="bank-move-amount">€${t.monto.toLocaleString('es-ES')}</span>
                </div>
                <div class="bank-move-footer">
                    <span class="bank-move-date">${formatDateHuman(t.fecha)}</span>
                    <div class="filter-chip" style="font-size:0.7rem; height:26px; padding:0 12px; border-radius:14px; flex:1; justify-content:flex-start; background:rgba(247, 140, 88, 0.05); color:var(--retro-orange); border-style:dashed;" 
                            onclick="openCatPicker(${i})">
                        ${t.categoria || "Otros"} > ${t.subcategoria || 'Varios'}
                    </div>
                    <input type="checkbox" style="width:20px; height:20px; cursor:pointer;" ${t.selected ? 'checked' : ''} 
                            onchange="toggleBankTransaction(${i}, this.checked)">
                </div>
            </div>
        `;
        list.appendChild(div);
    });
    lucide.createIcons();
}

function renderIngestAccountSelector(selectedAcc = null) {
    const list = document.getElementById('bank-new-list');
    if (!list) return;

    const accounts = currentConfig.preferred_accounts || ["Germán"];

    let selectorDiv = document.getElementById('ingest-account-container');
    if (!selectorDiv) {
        selectorDiv = document.createElement('div');
        selectorDiv.id = 'ingest-account-container';
        selectorDiv.style = "padding: 12px; background: rgba(93, 115, 126, 0.05); border-radius: 12px; margin-bottom: 16px;";
        list.parentNode.insertBefore(selectorDiv, list);
    }

    selectorDiv.innerHTML = `
        <div style="font-size:0.75rem; color:var(--text-muted); margin-bottom:12px; font-weight:700;">ASIGNAR A CUENTA:</div>
        <div class="filter-bar" style="justify-content:flex-start; margin-bottom: 0;">
            ${accounts.map(acc => `
                <div class="filter-chip ${selectedAcc === acc ? 'active' : ''}" 
                     onclick="updateIngestAccount('${acc}')">${acc}</div>
            `).join('')}
            <div class="filter-chip btn-add-acc" onclick="openAccountModal()"><i data-lucide="plus" size="14"></i> Agregar Cuenta</div>
        </div>
    `;

    if (selectedAcc) {
        pendingTransactions.forEach(t => t.cuenta = selectedAcc);
    }
}

let activePickerTransactionIdx = null;
let currentBrowseCategory = null;

function openCatPicker(idx) {
    activePickerTransactionIdx = idx;
    currentBrowseCategory = null;
    const modal = document.getElementById('cat-picker-modal');
    modal.classList.add('active');
    modal.style.display = 'flex';

    document.getElementById('cat-search-input').value = '';
    document.getElementById('cat-search-input').focus();
    renderPickerOptions('');
}

function closeCatPicker() {
    const modal = document.getElementById('cat-picker-modal');
    modal.classList.remove('active');
    modal.style.display = 'none';
}

function renderPickerOptions(query = '') {
    const container = document.getElementById('picker-results');
    const breadcrumbs = document.getElementById('picker-breadcrumbs');
    container.innerHTML = '';
    const taxonomy = currentConfig.taxonomy;

    if (query) {
        currentBrowseCategory = null;
        breadcrumbs.textContent = 'Resultados de búsqueda:';
        const q = query.toLowerCase();
        Object.entries(taxonomy).forEach(([cat, cfg]) => {
            if (cat.toLowerCase().includes(q)) {
                addPickerItem(container, cat, null, cat);
            }
            cfg.subcategories.forEach(sub => {
                if (sub.toLowerCase().includes(q) || cat.toLowerCase().includes(q)) {
                    addPickerItem(container, cat, sub, `${cat} > ${sub}`);
                }
            });
        });
    } else if (currentBrowseCategory) {
        breadcrumbs.textContent = `Explorar: ${currentBrowseCategory}`;
        const back = document.createElement('div');
        back.className = 'btn-picker-back';
        back.onclick = () => { currentBrowseCategory = null; renderPickerOptions(''); };
        back.innerHTML = `<i data-lucide="chevron-left" size="16"></i> Volver`;
        container.appendChild(back);

        taxonomy[currentBrowseCategory].subcategories.forEach(sub => {
            addPickerItem(container, currentBrowseCategory, sub, sub);
        });
    } else {
        breadcrumbs.textContent = 'Explorar Categorías:';
        Object.keys(taxonomy).forEach(cat => {
            const div = document.createElement('div');
            div.className = 'picker-item';
            div.onclick = () => { currentBrowseCategory = cat; renderPickerOptions(''); };
            div.innerHTML = `<span>${cat}</span><i data-lucide="chevron-right" size="16"></i>`;
            container.appendChild(div);
        });
    }
    lucide.createIcons();
}

function addPickerItem(container, cat, sub, label) {
    const div = document.createElement('div');
    div.className = 'picker-item';
    div.onclick = () => selectPickerOption(cat, sub || 'Varios');
    div.innerHTML = `<span>${label}</span><i data-lucide="check" size="16"></i>`;
    container.appendChild(div);
}

function selectPickerOption(cat, sub) {
    updateRowCategory(activePickerTransactionIdx, cat, sub);
    closeCatPicker();
}

function updateRowCategory(idx, newCat, newSub = "Varios") {
    const t = pendingTransactions[idx];
    const store = t.tienda;
    const detail = t.detalle;

    t.categoria = newCat;
    t.subcategoria = newSub;

    // Propagate
    let count = 0;
    pendingTransactions.forEach((other, i) => {
        if (i === idx) return;
        const matchesStore = store && store !== "Desconocido" && other.tienda === store;
        const matchesDetail = other.detalle === detail;

        if (matchesStore || matchesDetail) {
            other.categoria = newCat;
            other.subcategoria = newSub;
            count++;
        }
    });

    renderBankPreview(pendingTransactions, t.cuenta);
}

async function confirmBankIngest() {
    const btn = document.getElementById('btn-confirm-ingest');
    const toAdd = pendingTransactions.filter(t => t.selected);
    if (!toAdd.length) return alert('No hay seleccionados');

    const mapped = toAdd.map(t => ({
        fecha: t.fecha, monto: t.monto, categoria: t.categoria || "Otros",
        subcategoria: t.subcategoria || "Varios", detalle: t.detalle,
        tipo: t.tipo, tienda: t.tienda, cuenta: t.cuenta,
        intent: t.intent || "regular"
    }));

    if (btn) {
        btn.disabled = true;
        btn.textContent = 'CARGANDO...';
        btn.style.opacity = '0.5';
    }

    try {
        console.log("Confirming ingest of", mapped.length, "transactions");
        const res = await apiFetch('/ingest_data', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ transactions: mapped })
        });
        console.log("Ingest result:", res);
        alert('¡Hecho! ' + (res.added || 0) + ' movimientos cargados.');
        localStorage.removeItem('app_pending_tx');
        closeBank();
        await refreshData();
    } catch (e) {
        console.error("Ingest error:", e);
        alert('Error al confirmar carga: ' + e.message);
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.textContent = 'CONFIRMAR CARGA';
            btn.style.opacity = '1';
        }
    }
}

function updateIngestAccount(val) {
    if (val === 'new') {
        openAccountModal();
    } else {
        pendingTransactions.forEach(t => t.cuenta = val);
        renderIngestAccountSelector(val);
    }
}

function resetBank() {
    localStorage.removeItem('app_pending_tx');
    const preview = document.getElementById('bank-preview');
    const drop = document.getElementById('drop-zone');
    if (preview) preview.style.display = 'none';
    if (drop) drop.style.display = 'block';

    const selectorCont = document.getElementById('ingest-account-container');
    if (selectorCont) selectorCont.remove();
}

function closeBank() { resetBank(); pendingTransactions = []; }

// Settings & Config
function openSettings() {
    const el = document.getElementById('view-settings');
    if (el) el.classList.add('active');
    renderSettings();
}
function closeSettings() {
    const el = document.getElementById('view-settings');
    if (el) el.classList.remove('active');
    refreshConfig(); refreshData();
}

function renderSettings() {
    const list = document.getElementById('settings-cat-list');
    if (!list) return;
    list.innerHTML = '';
    Object.entries(currentConfig.taxonomy).forEach(([name, cfg]) => {
        const div = document.createElement('div');
        div.className = 'cat-config-item';
        div.innerHTML = `
            <div class="cat-header">
                <div style="flex: 1;">
                    <span class="budget-label">Nombre de Categoría</span>
                    <input type="text" value="${name}" class="form-input" 
                        style="font-weight:700; border:none; padding:0; background:transparent; font-size:1.1rem; color:var(--text-charcoal);" 
                        onchange="updateCatName('${name}', this.value)">
                </div>
                <div style="display:flex; align-items:center; gap:16px;">
                    <div style="text-align: right;">
                        <label class="budget-label">Presupuesto</label>
                        <div style="display:flex; align-items:center; gap:4px; background:var(--bg-cream); padding:4px 10px; border-radius:8px;">
                            <span style="font-size:0.8rem; font-weight:800; color:var(--text-muted);">€</span>
                            <input type="number" value="${cfg.budget}" class="form-input" 
                                style="width:70px; padding:0; border:none; background:transparent; font-weight:700; text-align:right;" 
                                onchange="updateCatBudget('${name}', this.value)">
                        </div>
                    </div>
                    <button onclick="deleteCat('${name}')" style="background:rgba(229, 75, 75, 0.1); border:none; color:var(--vhs-red); width:32px; height:32px; border-radius:8px; display:flex; align-items:center; justify-content:center; cursor:pointer;">
                        <i data-lucide="trash-2" size="14"></i>
                    </button>
                </div>
            </div>
            <div id="subs-${name}" style="margin-top:10px;">
                <span class="budget-label" style="margin-bottom:8px;">Subcategorías</span>
                <div style="display:flex; flex-wrap:wrap; gap:4px;">
                    ${cfg.subcategories.map(s => `
                        <span class="sub-tag">
                            ${s} 
                            <i data-lucide="x" size="12" onclick="deleteSub('${name}','${s}')"></i>
                        </span>
                    `).join('')}
                    <input type="text" class="form-input" 
                        style="font-size:0.75rem; padding:6px 14px; width:110px; height:32px; border-style:dashed; border-radius:8px;" 
                        placeholder="+ Añadir" onkeypress="if(event.key==='Enter') addSub('${name}', this)">
                </div>
            </div>
        `;
        list.appendChild(div);
    });
    lucide.createIcons();
    renderRules();
}

async function renderRules() {
    const list = document.getElementById('settings-rules-list');
    if (!list) return;
    try {
        const rules = await apiFetch('/rules/list');
        list.innerHTML = rules.length === 0 ? '<p style="font-size:0.75rem; color:var(--text-muted); padding: 10px;">No hay reglas aprendidas aún.</p>' : '';
        rules.forEach(r => {
            const div = document.createElement('div');
            div.className = 'timeline-item';
            div.style.padding = '12px';
            div.style.display = 'grid';
            div.style.gridTemplateColumns = '1fr auto';
            div.style.alignItems = 'center';
            div.style.background = 'white';
            div.style.marginBottom = '8px';
            div.style.borderRadius = '12px';
            div.innerHTML = `
                <div>
                    <div style="font-weight:700; font-size:0.85rem;">${r.pattern}</div>
                    <div style="font-size:0.7rem; color:var(--text-muted);">${r.category} > ${r.subcategory} (${r.type || 'Gasto'})</div>
                </div>
                <button onclick="deleteRule('${r.pattern}', '${r.type || 'Gasto'}')" style="background:none; border:none; color:var(--vhs-red); cursor:pointer; padding: 10px;">
                    <i data-lucide="trash-2" size="14"></i>
                </button>
            `;
            list.appendChild(div);
        });
        lucide.createIcons();
    } catch (e) {
        list.innerHTML = '<p style="color:var(--vhs-red); font-size:0.75rem;">Error al cargar reglas.</p>';
    }
}

async function deleteRule(pattern, type) {
    if (!confirm(`¿Eliminar regla para ${pattern}?`)) return;
    try {
        await apiFetch('/rules/delete', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ pattern, type }) });
        renderRules();
    } catch (e) { alert(e.message); }
}

async function saveConfig() {
    try {
        await apiFetch('/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(currentConfig)
        });
        renderSettings();
    } catch (e) {
        alert('Error al guardar configuración: ' + e.message);
    }
}

function updateCatName(oldName, newName) {
    if (newName && newName !== oldName) {
        currentConfig.taxonomy[newName] = currentConfig.taxonomy[oldName];
        delete currentConfig.taxonomy[oldName];
        saveConfig();
    }
}

function updateCatBudget(name, val) { currentConfig.taxonomy[name].budget = parseFloat(val); saveConfig(); }
function deleteCat(name) {
    if (confirm(`¿Borrar ${name}?`)) {
        delete currentConfig.taxonomy[name];
        saveConfig();
    }
}
function addSub(name, el) { const val = el.value.trim(); if (val) { currentConfig.taxonomy[name].subcategories.push(val); saveConfig(); } }
function deleteSub(name, sub) { currentConfig.taxonomy[name].subcategories = currentConfig.taxonomy[name].subcategories.filter(s => s !== sub); saveConfig(); }

async function debugClearActivity() {
    if (!confirm("⚠️ ¡PELIGRO! ¿Seguro que quieres borrar TODA tu actividad? Esta acción no se puede deshacer.")) return;
    try {
        const r = await apiFetch('/debug/clear-activity', { method: 'POST' });
        alert(r.message);
        closeSettings();
        await refreshData();
    } catch (e) {
        alert(e.message);
    }
}

async function addCategory() {
    const name = prompt("Nombre de la nueva categoría:");
    if (name) {
        if (currentConfig.taxonomy[name]) {
            alert("Esa categoría ya existe.");
            return;
        }
        currentConfig.taxonomy[name] = { subcategories: ["Varios"], budget: 0 };
        await saveConfig();
    }
}

// Movements Manual/AI
function openAddModal() {
    document.getElementById('addModal').style.display = 'flex';
    setEntryType('Gasto', 'add');
}
function closeAddModal() { document.getElementById('addModal').style.display = 'none'; }
function setAddTab(tab) {
    document.getElementById('pane-manual').style.display = tab === 'manual' ? 'block' : 'none';
    document.getElementById('pane-ai').style.display = tab === 'ai' ? 'block' : 'none';
    document.getElementById('tab-manual').style.background = tab === 'manual' ? 'white' : 'transparent';
    document.getElementById('tab-manual').style.color = tab === 'manual' ? 'black' : 'var(--text-muted)';
    document.getElementById('tab-ai').style.background = tab === 'ai' ? 'white' : 'transparent';
    document.getElementById('tab-ai').style.color = tab === 'ai' ? 'black' : 'var(--text-muted)';
}

async function saveMovement() {
    const amount = document.getElementById('in-amount').value;
    const desc = document.getElementById('in-desc').value;
    const cat = document.getElementById('in-cat').value;
    const acc = document.getElementById('in-acc').value;
    const type = document.querySelector('#add-type-toggle .type-toggle-btn.active').getAttribute('data-type');

    if (!amount || !desc) return alert("Faltan datos");
    try {
        await apiFetch('/ingest', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: `${type}: ${desc} ${amount} en ${cat}`, account_override: acc })
        });
        closeAddModal(); await refreshData();
    } catch (e) { alert(e.message); }
}

function setEntryType(type, context, selectedCat = null) {
    const parentId = context === 'add' ? 'add-type-toggle' : 'edit-type-toggle';
    const selectId = context === 'add' ? 'in-cat' : 'edit-cat';

    // Update visual buttons
    const btns = document.querySelectorAll(`#${parentId} .type-toggle-btn`);
    btns.forEach(b => {
        if (b.getAttribute('data-type') === type) b.classList.add('active');
        else b.classList.remove('active');
    });

    // Filter categories based on type
    const sel = document.getElementById(selectId);
    if (!sel) return;

    let options = "";
    if (type === 'Ingreso') {
        options = `<option value="Ingresos" ${'Ingresos' === selectedCat ? 'selected' : ''}>Ingresos</option>`;
    } else {
        const taxonomy = currentConfig.taxonomy || {};
        options = Object.keys(taxonomy)
            .filter(c => c !== 'Ingresos')
            .map(c => `<option value="${c}" ${c === selectedCat ? 'selected' : ''}>${c}</option>`)
            .join('');
    }
    sel.innerHTML = options;

    // Update subcategories for the new default/selected category
    if (context === 'edit') updateEditSubOptions(sel.value);
}

async function sendAI() {
    const input = document.getElementById('aiInput');
    const acc = document.getElementById('ai-acc').value;
    const text = input.value.trim();
    if (!text) return;

    addChatMsg('user', text);
    input.value = '';

    try {
        const r = await apiFetch('/ingest', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text: text,
                account_override: acc
            })
        });
        if (r.status === 'success') {
            addChatMsg('ai', "¡Gasto registrado con éxito!");
            await refreshData();
        } else addChatMsg('ai', "Error: " + r.message);
    } catch (e) {
        addChatMsg('ai', "Error de conexión con el servidor. Asegúrate de que Flask esté ejecutándose.");
    }
}

function openEditModal(m) {
    document.getElementById('edit-id').value = m.id;
    document.getElementById('edit-date').value = m.fecha;
    document.getElementById('edit-amount').value = m.monto;
    document.getElementById('edit-desc').value = m.tienda || m.detalle;

    // Set type toggle
    setEntryType(m.tipo || 'Gasto', 'edit', m.categoria);

    const accSel = document.getElementById('edit-acc');
    const accounts = currentConfig.preferred_accounts || ["Germán", "eToro", "Esposa", "Efectivo"];
    accSel.innerHTML = accounts.map(acc => `<option value="${acc}" ${acc === m.cuenta ? 'selected' : ''}>${acc}</option>`).join('');

    const catSel = document.getElementById('edit-cat');
    catSel.value = m.categoria;

    updateEditSubOptions(m.categoria, m.subcategoria);
    document.getElementById('editModal').style.display = 'flex';
}

function closeEditModal() { document.getElementById('editModal').style.display = 'none'; }

function updateEditSubOptions(cat, selectedSub = null) {
    const subSel = document.getElementById('edit-subcat');
    const subs = currentConfig.taxonomy[cat]?.subcategories || ["Varios"];
    subSel.innerHTML = subs.map(s => `<option value="${s}" ${s === selectedSub ? 'selected' : ''}>${s}</option>`).join('');
}

let lastEditedTransaction = null;

async function saveTransactionEdit() {
    const id = document.getElementById('edit-id').value;
    const date = document.getElementById('edit-date').value;
    const amount = document.getElementById('edit-amount').value;
    const desc = document.getElementById('edit-desc').value;
    const cat = document.getElementById('edit-cat').value;
    const subcat = document.getElementById('edit-subcat').value;
    const acc = document.getElementById('edit-acc').value;
    const type = document.querySelector('#edit-type-toggle .type-toggle-btn.active').getAttribute('data-type');

    try {
        const res = await apiFetch('/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id, fecha: date, monto: amount, detalle: desc, categoria: cat, subcategoria: subcat, cuenta: acc, tipo: type })
        });

        if (res.status === 'success') {
            closeEditModal();
            await refreshData();

            // Check for learning opportunity
            if (desc && desc.length > 2) {
                const confirmLearn = confirm(`¿Quieres que la app aprenda que "${desc}" siempre pertenece a ${cat} > ${subcat}?`);
                if (confirmLearn) {
                    await apiFetch('/rules/learn', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ pattern: desc, category: cat, subcategory: subcat })
                    });
                    alert("¡Aprendido! Las próximas cargas serán automáticas.");
                }
            }
        } else alert(res.message);
    } catch (e) { alert(e.message); }
}

async function deleteTransactionFromEdit() {
    const id = document.getElementById('edit-id').value;
    if (!confirm("¿Seguro que quieres eliminar este movimiento?")) return;
    try {
        const res = await apiFetch('/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id })
        });
        if (res.status === 'success') {
            closeEditModal();
            await refreshData();
        } else alert(res.message);
    } catch (e) { alert(e.message); }
}

function addChatMsg(role, txt) {
    const box = document.getElementById('chat-box');
    if (!box) return;
    const d = document.createElement('div');
    d.style.padding = '12px';
    d.style.borderRadius = '12px';
    d.style.alignSelf = role === 'user' ? 'flex-end' : 'flex-start';
    d.style.background = role === 'user' ? 'var(--vhs-red)' : 'var(--border)';
    d.style.color = role === 'user' ? 'white' : 'black';
    d.style.fontSize = '0.9rem';
    d.textContent = txt;
    box.appendChild(d);
    box.scrollTop = box.scrollHeight;
}

function toggleBankTransaction(idx, checked) {
    pendingTransactions[idx].selected = checked;
    saveBankToCache();
}

function toggleAllTransactions(checked) {
    if (!pendingTransactions) return;
    pendingTransactions.forEach(t => t.selected = checked);
    const checks = document.querySelectorAll('#bank-new-list input[type="checkbox"]');
    checks.forEach(c => c.checked = checked);
    saveBankToCache();
}

function saveBankToCache() {
    if (pendingTransactions.length > 0) {
        localStorage.setItem('app_pending_tx', JSON.stringify({
            transactions: pendingTransactions,
            account: pendingTransactions[0]?.cuenta || "Germán"
        }));
    } else {
        localStorage.removeItem('app_pending_tx');
    }
}

// Utils
function debounce(f, ms) { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => f.apply(this, a), ms); }; }
function getIcon(cat) {
    const map = { "Hijos": "baby", "Entretenimiento": "tv", "Diario": "shopping-cart", "Salud": "heart-pulse", "Hogar": "home", "Seguros": "shield-check", "Transporte": "car", "Viajes": "plane", "Servicios": "zap", "Ingresos": "trending-up", "Otros": "tag", "Other": "help-circle" };
    return map[cat] || "tag";
}

// Account Management
function openAccountModal(name = null) {
    const modal = document.getElementById('accountModal');
    const title = modal.querySelector('h3');
    const delBtn = document.getElementById('btn-delete-acc');

    if (name) {
        title.textContent = "Editar Cuenta";
        document.getElementById('acc-old-name').value = name;
        document.getElementById('acc-name').value = name;
        // Search in taxonomy for metadata if we decide to store type/currency
        delBtn.style.display = 'block';
    } else {
        title.textContent = "Nueva Cuenta";
        document.getElementById('acc-old-name').value = "";
        document.getElementById('acc-name').value = "";
        delBtn.style.display = 'none';
    }
    modal.style.display = 'flex';
}

function closeAccountModal() { document.getElementById('accountModal').style.display = 'none'; }

async function saveAccount() {
    const oldName = document.getElementById('acc-old-name').value;
    const newName = document.getElementById('acc-name').value.trim();
    const type = document.getElementById('acc-type').value;
    const curr = document.getElementById('acc-currency').value;

    if (!newName) return alert("El nombre es obligatorio");
    if (newName === oldName) {
        // Just update metadata if name didn't change
        if (!currentConfig.account_details) currentConfig.account_details = {};
        currentConfig.account_details[newName] = { type, currency: curr };
        await saveConfig();
        closeAccountModal();
        return;
    }

    if (oldName) {
        // Full rename (Config + Database)
        try {
            const res = await apiFetch('/account/rename', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ old_name: oldName, new_name: newName })
            });
            selectedAccount = newName; // Auto select renamed account
        } catch (e) {
            return alert("Error al renombrar cuenta: " + e.message);
        }
    } else {
        // New account Creation
        if (!currentConfig.preferred_accounts.includes(newName)) {
            currentConfig.preferred_accounts.push(newName);
        }
        if (!currentConfig.account_details) currentConfig.account_details = {};
        currentConfig.account_details[newName] = { type, currency: curr };
        await saveConfig();
        selectedAccount = newName;
    }

    closeAccountModal();
    await refreshConfig();
    await refreshData();

    if (document.getElementById('view-bank').classList.contains('active')) {
        renderIngestAccountSelector(newName);
    }
}

async function deleteAccount() {
    const name = document.getElementById('acc-old-name').value;
    if (!name) return;
    if (!confirm(`¿Seguro que quieres eliminar la cuenta "${name}"? Los movimientos no se borrarán pero dejarán de estar asociados a esta cuenta.`)) return;

    currentConfig.preferred_accounts = currentConfig.preferred_accounts.filter(a => a !== name);
    if (currentConfig.account_details) delete currentConfig.account_details[name];

    await saveConfig();
    closeAccountModal();
    selectedAccount = null;
    refreshData();
}

// Filter Modal
function openFilterModal() {
    const modal = document.getElementById('filterModal');
    const accSel = document.getElementById('filter-acc');
    const catSel = document.getElementById('filter-cat');

    const accounts = ["Todas las Cuentas", ...(currentAnalytics.accounts || [])];
    accSel.innerHTML = accounts.map(a => `<option value="${a === 'Todas las Cuentas' ? '' : a}" ${selectedAccount === (a === 'Todas las Cuentas' ? null : a) ? 'selected' : ''}>${a}</option>`).join('');

    const cats = ["Todas las Categorías", ...Object.keys(currentConfig.taxonomy)];
    catSel.innerHTML = cats.map(c => `<option value="${c === 'Todas las Categorías' ? '' : c}" ${activeFilters.category === (c === 'Todas las Categorías' ? null : c) ? 'selected' : ''}>${c}</option>`).join('');

    modal.style.display = 'flex';
}

function closeFilterModal() { document.getElementById('filterModal').style.display = 'none'; }

function applyAdvFilters() {
    const acc = document.getElementById('filter-acc').value || null;
    const cat = document.getElementById('filter-cat').value || null;

    selectedAccount = acc;
    activeFilters.category = cat;

    closeFilterModal();
    refreshData();
}

function clearAdvFilters() {
    selectedAccount = null;
    activeFilters.category = null;
    closeFilterModal();
    refreshData();
}

// Init
window.onload = init;
