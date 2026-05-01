/* ========== STATE ========== */
let token = localStorage.getItem('sd_token') || null;
let currentUser = null;
let casesData = [];
let currentCase = null;
let currentCaseSkins = [];
let isSpinning = false;
let selectedDepositMethod = null;
let currentTicketId = null;

const WEAPON_EMOJIS = {
    'AK-47': '🔫', 'M4A4': '🔫', 'M4A1-S': '🔫', 'AWP': '🎯',
    'Desert Eagle': '🔫', 'USP-S': '🔫', 'Glock-18': '🔫',
    'P250': '🔫', 'Five-SeveN': '🔫', 'Tec-9': '🔫', 'CZ75-Auto': '🔫',
    'P2000': '🔫', 'Dual Berettas': '🔫', 'R8 Revolver': '🔫',
    'MP9': '💨', 'MP7': '💨', 'UMP-45': '💨', 'P90': '💨',
    'MAC-10': '💨', 'PP-Bizon': '💨', 'MP5-SD': '💨',
    'FAMAS': '🔫', 'Galil AR': '🔫', 'SG 553': '🔫', 'AUG': '🔫',
    'SSG 08': '🎯', 'G3SG1': '🎯', 'SCAR-20': '🎯',
    'Nova': '💥', 'XM1014': '💥', 'Sawed-Off': '💥', 'MAG-7': '💥',
    'Negev': '⚡', 'M249': '⚡',
    'Karambit': '🗡️', 'Butterfly Knife': '🦋', 'M9 Bayonet': '🗡️',
    'Bayonet': '🗡️', 'Flip Knife': '🗡️', 'Gut Knife': '🗡️',
    'Huntsman Knife': '🗡️', 'Falchion Knife': '🗡️', 'Shadow Daggers': '🗡️',
    'Stiletto Knife': '🗡️', 'Talon Knife': '🗡️', 'Ursus Knife': '🗡️',
    'Navaja Knife': '🗡️', 'Paracord Knife': '🗡️', 'Classic Knife': '🗡️',
    'Nomad Knife': '🗡️', 'Skeleton Knife': '🗡️', 'Survival Knife': '🗡️',
    'Kukri Knife': '🗡️', 'Gloves': '🧤',
};

const CASE_EMOJIS = {
    'Shadow Phantom': '👻', "Dragon's Fury": '🐉', 'Neon Strike': '⚡',
    'Arctic Ops': '❄️', 'Crimson Elite': '🔴', 'Spectrum Shift': '🌈',
    'Tactical Ops': '🎖️', 'Gold Rush': '💎', 'Pistol Mania': '🔫',
    'AWP Legends': '🎯', 'AK-47 Collection': '🔥', 'Knife Paradise': '🗡️',
    'Budget Blitz': '💰', 'M4 Masters': '⭐', 'Glove Case': '🧤',
    'Midnight Ops': '🌙',
};

const RARITY_NAMES = {
    consumer: 'Consumer', industrial: 'Industrial', mil_spec: 'Mil-Spec',
    restricted: 'Restricted', classified: 'Classified', covert: 'Covert',
    extraordinary: '★ Extraordinary',
};

/* ========== API ========== */
async function api(path, options = {}) {
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    try {
        const resp = await fetch(path, { ...options, headers });
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.detail || 'Ошибка сервера');
        return data;
    } catch (e) {
        if (e.message === 'Требуется авторизация' || e.message === 'Невалидный или просроченный токен') {
            logout();
        }
        throw e;
    }
}

/* ========== NOTIFICATIONS ========== */
function notify(text, type = 'info') {
    const el = document.getElementById('notification');
    const textEl = document.getElementById('notification-text');
    textEl.textContent = text;
    el.className = 'notification ' + type;
    el.classList.remove('hidden');
    setTimeout(() => el.classList.add('hidden'), 3500);
}

/* ========== NAVIGATION ========== */
function navigateTo(page) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
    const target = document.getElementById('page-' + page);
    if (target) target.classList.add('active');
    const navLink = document.querySelector(`.nav-link[data-page="${page}"]`);
    if (navLink) navLink.classList.add('active');
    window.scrollTo(0, 0);

    if (page === 'home') loadCases();
    if (page === 'profile') loadProfile();
    if (page === 'deposit') loadPaymentMethods();
    if (page === 'support') loadSupport();
}

/* ========== AUTH ========== */
function showModal(type) {
    closeModal();
    document.getElementById('modal-overlay').classList.remove('hidden');
    document.getElementById('modal-' + type).classList.remove('hidden');
}

function closeModal() {
    document.getElementById('modal-overlay').classList.add('hidden');
    document.querySelectorAll('.modal').forEach(m => m.classList.add('hidden'));
    document.querySelectorAll('.form-error').forEach(e => e.classList.add('hidden'));
}

async function registerUser() {
    const username = document.getElementById('reg-username').value.trim();
    const email = document.getElementById('reg-email').value.trim();
    const password = document.getElementById('reg-password').value;
    const password2 = document.getElementById('reg-password2').value;
    const errEl = document.getElementById('reg-error');

    if (password !== password2) {
        errEl.textContent = 'Пароли не совпадают';
        errEl.classList.remove('hidden');
        return;
    }
    try {
        const data = await api('/api/auth/register', {
            method: 'POST', body: JSON.stringify({ username, email, password })
        });
        token = data.token;
        localStorage.setItem('sd_token', token);
        currentUser = data.user;
        updateUI();
        closeModal();
        notify('Добро пожаловать, ' + currentUser.username + '! Вам начислено 1000 ₽', 'success');
    } catch (e) {
        errEl.textContent = e.message;
        errEl.classList.remove('hidden');
    }
}

async function loginUser() {
    const username = document.getElementById('login-username').value.trim();
    const password = document.getElementById('login-password').value;
    const errEl = document.getElementById('login-error');
    try {
        const data = await api('/api/auth/login', {
            method: 'POST', body: JSON.stringify({ username, password })
        });
        token = data.token;
        localStorage.setItem('sd_token', token);
        currentUser = data.user;
        updateUI();
        closeModal();
        notify('С возвращением, ' + currentUser.username + '!', 'success');
    } catch (e) {
        errEl.textContent = e.message;
        errEl.classList.remove('hidden');
    }
}

function logout() {
    token = null;
    currentUser = null;
    localStorage.removeItem('sd_token');
    updateUI();
    navigateTo('home');
}

async function loadUser() {
    if (!token) return;
    try {
        currentUser = await api('/api/auth/me');
        updateUI();
    } catch {
        logout();
    }
}

function updateUI() {
    const authSection = document.getElementById('auth-section');
    const userSection = document.getElementById('user-section');
    if (currentUser) {
        authSection.classList.add('hidden');
        userSection.classList.remove('hidden');
        document.getElementById('user-balance').textContent = currentUser.balance.toFixed(2);
        document.getElementById('user-avatar-letter').textContent = currentUser.username[0].toUpperCase();
        document.getElementById('username-display').textContent = currentUser.username;
    } else {
        authSection.classList.remove('hidden');
        userSection.classList.add('hidden');
    }
}

/* ========== CASES ========== */
async function loadCases() {
    try {
        casesData = await api('/api/cases/');
        renderCases(casesData);
    } catch (e) {
        notify('Ошибка загрузки кейсов: ' + e.message, 'error');
    }
}

function renderCases(cases) {
    const grid = document.getElementById('cases-grid');
    grid.innerHTML = cases.map(c => `
        <div class="case-card" onclick="openCasePage(${c.id})">
            <div class="case-card-image">
                <span class="case-emoji">${CASE_EMOJIS[c.name] || '📦'}</span>
            </div>
            <div class="case-card-body">
                <div class="case-card-name">${escapeHtml(c.name)}</div>
                <div class="case-card-desc">${escapeHtml(c.description)}</div>
                <div class="case-card-footer">
                    <span class="case-card-price">${c.price.toFixed(2)} ₽</span>
                    <span class="case-card-badge badge-${c.category}">${c.category}</span>
                </div>
            </div>
        </div>
    `).join('');
}

function filterCases(category) {
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    document.querySelector(`.filter-btn[data-filter="${category}"]`).classList.add('active');
    if (category === 'all') {
        renderCases(casesData);
    } else {
        renderCases(casesData.filter(c => c.category === category));
    }
}

async function openCasePage(caseId) {
    try {
        const data = await api(`/api/cases/${caseId}`);
        currentCase = data;
        currentCaseSkins = data.skins;
        document.getElementById('case-name').textContent = data.name;
        document.getElementById('case-description').textContent = data.description;
        document.getElementById('case-price-display').textContent = data.price.toFixed(2);
        document.getElementById('won-skin-display').classList.add('hidden');
        renderCaseSkins(data.skins);
        buildRouletteStrip(data.skins);
        navigateTo('case');
    } catch (e) {
        notify('Ошибка: ' + e.message, 'error');
    }
}

function renderCaseSkins(skins) {
    const grid = document.getElementById('case-skins-grid');
    grid.innerHTML = skins.map(s => `
        <div class="skin-card border-${s.rarity} bg-${s.rarity}">
            <div class="skin-card-icon">${WEAPON_EMOJIS[s.weapon] || '🔫'}</div>
            <div class="skin-card-name">${escapeHtml(s.name)}</div>
            <div class="skin-card-price rarity-${s.rarity}">${s.price.toFixed(2)} ₽</div>
            <span class="skin-card-rarity rarity-${s.rarity}">${RARITY_NAMES[s.rarity] || s.rarity}</span>
        </div>
    `).join('');
}

/* ========== ROULETTE ========== */
function buildRouletteStrip(skins) {
    const strip = document.getElementById('roulette-strip');
    const items = [];
    for (let i = 0; i < 60; i++) {
        const s = skins[Math.floor(Math.random() * skins.length)];
        items.push(s);
    }
    strip.style.transition = 'none';
    strip.style.transform = 'translateX(0) translateY(-50%)';
    strip.innerHTML = items.map(s => `
        <div class="roulette-item border-${s.rarity} bg-${s.rarity}">
            <span class="skin-icon">${WEAPON_EMOJIS[s.weapon] || '🔫'}</span>
            <span class="skin-name">${escapeHtml(s.name.split(' | ')[1] || s.name)}</span>
            <span class="skin-price rarity-${s.rarity}">${s.price.toFixed(2)} ₽</span>
        </div>
    `).join('');
}

async function openCase() {
    if (isSpinning) return;
    if (!currentUser) { showModal('login'); return; }
    if (!currentCase) return;
    if (currentUser.balance < currentCase.price) {
        notify('Недостаточно средств! Пополните баланс.', 'error');
        return;
    }

    isSpinning = true;
    document.getElementById('btn-open-case').disabled = true;
    document.getElementById('won-skin-display').classList.add('hidden');

    try {
        const result = await api(`/api/cases/${currentCase.id}/open`, { method: 'POST' });
        currentUser.balance = result.new_balance;
        updateUI();

        const wonSkin = result.won_skin;
        const strip = document.getElementById('roulette-strip');
        const items = [];
        const winIndex = 45;

        for (let i = 0; i < 60; i++) {
            if (i === winIndex) {
                items.push(wonSkin);
            } else {
                items.push(currentCaseSkins[Math.floor(Math.random() * currentCaseSkins.length)]);
            }
        }

        strip.style.transition = 'none';
        strip.style.transform = 'translateX(0) translateY(-50%)';
        strip.innerHTML = items.map(s => `
            <div class="roulette-item border-${s.rarity} bg-${s.rarity}">
                <span class="skin-icon">${WEAPON_EMOJIS[s.weapon] || '🔫'}</span>
                <span class="skin-name">${escapeHtml(s.name.split(' | ')[1] || s.name)}</span>
                <span class="skin-price rarity-${s.rarity}">${s.price.toFixed(2)} ₽</span>
            </div>
        `).join('');

        await new Promise(r => setTimeout(r, 50));

        const container = document.getElementById('roulette-container');
        const containerWidth = container.offsetWidth;
        const itemWidth = 128; // 120 + 8 gap
        const targetOffset = winIndex * itemWidth - containerWidth / 2 + itemWidth / 2;
        const randomOffset = (Math.random() - 0.5) * 40;

        strip.style.transition = 'transform 5s cubic-bezier(0.15, 0.85, 0.25, 1)';
        strip.style.transform = `translateX(-${targetOffset + randomOffset}px) translateY(-50%)`;

        setTimeout(() => {
            isSpinning = false;
            document.getElementById('btn-open-case').disabled = false;
            showWonSkin(wonSkin);
        }, 5200);
    } catch (e) {
        isSpinning = false;
        document.getElementById('btn-open-case').disabled = false;
        notify(e.message, 'error');
    }
}

function showWonSkin(skin) {
    const display = document.getElementById('won-skin-display');
    const card = document.getElementById('won-skin-card');
    card.className = `won-skin-card border-${skin.rarity}`;
    card.innerHTML = `
        <span class="skin-icon">${WEAPON_EMOJIS[skin.weapon] || '🔫'}</span>
        <span class="skin-name rarity-${skin.rarity}">${escapeHtml(skin.name)}</span>
        <span class="skin-price">${skin.price.toFixed(2)} ₽</span>
        <span class="skin-card-rarity rarity-${skin.rarity}">${RARITY_NAMES[skin.rarity] || skin.rarity}</span>
    `;
    display.classList.remove('hidden');
    display.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

/* ========== PROFILE ========== */
async function loadProfile() {
    if (!currentUser) { navigateTo('home'); showModal('login'); return; }
    try {
        const user = await api('/api/auth/me');
        currentUser = user;
        updateUI();
        document.getElementById('profile-username').textContent = user.username;
        document.getElementById('profile-email').textContent = user.email;
        document.getElementById('profile-balance').textContent = user.balance.toFixed(2) + ' ₽';
        document.getElementById('profile-avatar-letter').textContent = user.username[0].toUpperCase();
        document.getElementById('profile-joined').textContent = user.created_at ?
            new Date(user.created_at).toLocaleDateString('ru-RU') : '-';
        loadInventory();
    } catch (e) {
        notify('Ошибка загрузки профиля', 'error');
    }
}

async function loadInventory() {
    try {
        const items = await api('/api/profile/inventory');
        const grid = document.getElementById('inventory-grid');
        if (items.length === 0) {
            grid.innerHTML = '<div class="empty-state">Инвентарь пуст. Откройте кейс, чтобы получить скины!</div>';
            return;
        }
        grid.innerHTML = items.map(item => `
            <div class="inventory-card border-${item.skin.rarity} bg-${item.skin.rarity}">
                <div class="skin-icon">${WEAPON_EMOJIS[item.skin.weapon] || '🔫'}</div>
                <div class="skin-name">${escapeHtml(item.skin.name)}</div>
                <div class="skin-price">${item.skin.price.toFixed(2)} ₽</div>
                <div class="skin-from">Из: ${escapeHtml(item.obtained_from)}</div>
                <button class="btn btn-accent btn-sm" onclick="sellSkin(${item.inventory_id}, '${escapeHtml(item.skin.name)}', ${item.skin.price})">
                    Продать за ${item.skin.price.toFixed(2)} ₽
                </button>
            </div>
        `).join('');
    } catch (e) {
        notify('Ошибка загрузки инвентаря', 'error');
    }
}

async function sellSkin(inventoryId, name, price) {
    if (!confirm(`Продать "${name}" за ${price.toFixed(2)} ₽?`)) return;
    try {
        const data = await api(`/api/profile/sell/${inventoryId}`, { method: 'POST' });
        currentUser.balance = data.new_balance;
        updateUI();
        loadInventory();
        notify(`Продано за ${data.sold_price.toFixed(2)} ₽`, 'success');
    } catch (e) {
        notify(e.message, 'error');
    }
}

function switchProfileTab(tab) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    event.target.classList.add('active');
    const content = document.getElementById('profile-tab-content');
    if (tab === 'inventory') {
        content.innerHTML = '<div class="inventory-grid" id="inventory-grid"><div class="empty-state">Загрузка...</div></div>';
        loadInventory();
    } else if (tab === 'history') {
        loadPaymentHistory();
    } else if (tab === 'settings') {
        content.innerHTML = `
            <div style="max-width:500px;">
                <h3 style="margin-bottom:16px;">⚙️ Настройки аккаунта</h3>
                <div class="form-group">
                    <label>Имя пользователя</label>
                    <input type="text" class="input" value="${escapeHtml(currentUser.username)}" disabled>
                </div>
                <div class="form-group">
                    <label>Email</label>
                    <input type="text" class="input" value="${escapeHtml(currentUser.email)}" disabled>
                </div>
                <div class="form-group">
                    <label>Steam Trade URL</label>
                    <input type="text" class="input" placeholder="Вставьте Trade URL для вывода скинов">
                </div>
                <button class="btn btn-primary" onclick="notify('Настройки сохранены','success')">Сохранить</button>
                <button class="btn btn-secondary" onclick="logout()" style="margin-left:10px;color:var(--danger);">Выйти из аккаунта</button>
            </div>
        `;
    }
}

async function loadPaymentHistory() {
    try {
        const payments = await api('/api/payments/history');
        const content = document.getElementById('profile-tab-content');
        if (payments.length === 0) {
            content.innerHTML = '<div class="empty-state">История платежей пуста</div>';
            return;
        }
        content.innerHTML = `<div class="tickets-list">${payments.map(p => `
            <div class="ticket-item" style="cursor:default;">
                <div>
                    <div class="ticket-subject">${p.amount.toFixed(2)} ₽ — ${p.method}</div>
                    <div class="ticket-date">${p.created_at ? new Date(p.created_at).toLocaleString('ru-RU') : '-'}</div>
                </div>
                <span class="ticket-status ${p.status === 'completed' ? 'open' : 'closed'}">${p.status}</span>
            </div>
        `).join('')}</div>`;
    } catch (e) {
        notify('Ошибка загрузки истории', 'error');
    }
}

/* ========== PAYMENTS ========== */
async function loadPaymentMethods() {
    if (!currentUser) { navigateTo('home'); showModal('login'); return; }
    try {
        const methods = await api('/api/payments/methods');
        const container = document.getElementById('deposit-methods');
        container.innerHTML = methods.map(m => `
            <div class="deposit-method-card" onclick="selectDepositMethod('${m.id}', '${escapeHtml(m.name)}', ${m.min_amount}, ${m.max_amount}, ${m.commission})">
                <div class="deposit-method-icon">${m.icon}</div>
                <div class="deposit-method-name">${escapeHtml(m.name)}</div>
                <div class="deposit-method-desc">${escapeHtml(m.description)}</div>
                <div class="deposit-method-limits">${m.min_amount} — ${m.max_amount} ₽${m.commission > 0 ? ` (комиссия ${m.commission}%)` : ''}</div>
            </div>
        `).join('');
        document.getElementById('deposit-form').classList.add('hidden');
    } catch (e) {
        notify('Ошибка загрузки методов оплаты', 'error');
    }
}

function selectDepositMethod(id, name, min, max, commission) {
    selectedDepositMethod = { id, name, min, max, commission };
    document.getElementById('deposit-method-name').textContent = name;
    document.getElementById('deposit-amount').min = min;
    document.getElementById('deposit-amount').max = max;
    document.getElementById('deposit-amount').placeholder = `От ${min} до ${max} ₽`;
    document.getElementById('deposit-info').textContent = commission > 0
        ? `Комиссия: ${commission}%. Минимум: ${min} ₽, Максимум: ${max} ₽`
        : `Без комиссии. Минимум: ${min} ₽, Максимум: ${max} ₽`;
    document.getElementById('deposit-form').classList.remove('hidden');
    document.getElementById('deposit-form').scrollIntoView({ behavior: 'smooth' });
}

async function submitDeposit() {
    if (!selectedDepositMethod) return;
    const amount = parseFloat(document.getElementById('deposit-amount').value);
    if (!amount || amount < selectedDepositMethod.min || amount > selectedDepositMethod.max) {
        notify(`Введите сумму от ${selectedDepositMethod.min} до ${selectedDepositMethod.max} ₽`, 'error');
        return;
    }
    try {
        const data = await api('/api/payments/deposit', {
            method: 'POST',
            body: JSON.stringify({ method: selectedDepositMethod.id, amount })
        });
        notify(data.message, 'success');
        document.getElementById('deposit-form').classList.add('hidden');
    } catch (e) {
        notify(e.message, 'error');
    }
}

function cancelDeposit() {
    document.getElementById('deposit-form').classList.add('hidden');
    selectedDepositMethod = null;
}

/* ========== SUPPORT ========== */
async function loadSupport() {
    loadFAQ();
    if (currentUser) loadTickets();
}

async function loadFAQ() {
    try {
        const faq = await api('/api/support/faq');
        const list = document.getElementById('faq-list');
        list.innerHTML = faq.map((item, i) => `
            <div class="faq-item" id="faq-${i}">
                <div class="faq-question" onclick="toggleFAQ(${i})">
                    <span>${escapeHtml(item.question)}</span>
                    <span class="faq-arrow">▼</span>
                </div>
                <div class="faq-answer">${escapeHtml(item.answer)}</div>
            </div>
        `).join('');
    } catch { /* FAQ is optional */ }
}

function toggleFAQ(index) {
    const item = document.getElementById('faq-' + index);
    item.classList.toggle('open');
}

async function loadTickets() {
    try {
        const tickets = await api('/api/support/tickets');
        const list = document.getElementById('tickets-list');
        if (tickets.length === 0) {
            list.innerHTML = '<div class="empty-state">У вас пока нет обращений</div>';
            return;
        }
        list.innerHTML = tickets.map(t => `
            <div class="ticket-item" onclick="openTicketChat(${t.id})">
                <div>
                    <div class="ticket-subject">${escapeHtml(t.subject)}</div>
                    <div class="ticket-date">${t.created_at ? new Date(t.created_at).toLocaleString('ru-RU') : '-'}</div>
                </div>
                <span class="ticket-status ${t.status}">${t.status === 'open' ? 'Открыт' : 'Закрыт'}</span>
            </div>
        `).join('');
    } catch { /* ok */ }
}

function showNewTicketForm() {
    if (!currentUser) { showModal('login'); return; }
    document.getElementById('new-ticket-form').classList.remove('hidden');
    document.getElementById('btn-new-ticket').classList.add('hidden');
}

function hideNewTicketForm() {
    document.getElementById('new-ticket-form').classList.add('hidden');
    document.getElementById('btn-new-ticket').classList.remove('hidden');
}

async function submitTicket() {
    const subject = document.getElementById('ticket-subject').value.trim();
    const message = document.getElementById('ticket-message').value.trim();
    if (!subject || !message) { notify('Заполните все поля', 'error'); return; }
    try {
        await api('/api/support/tickets', {
            method: 'POST', body: JSON.stringify({ subject, message })
        });
        notify('Обращение создано!', 'success');
        hideNewTicketForm();
        document.getElementById('ticket-subject').value = '';
        document.getElementById('ticket-message').value = '';
        loadTickets();
    } catch (e) {
        notify(e.message, 'error');
    }
}

async function openTicketChat(ticketId) {
    currentTicketId = ticketId;
    try {
        const data = await api(`/api/support/tickets/${ticketId}`);
        document.getElementById('ticket-chat-subject').textContent = data.subject;
        const chatMessages = document.getElementById('chat-messages');
        chatMessages.innerHTML = data.messages.map(m => `
            <div class="chat-msg ${m.is_admin ? 'admin' : 'user'}">
                <div>${escapeHtml(m.message)}</div>
                <div class="chat-msg-time">${m.created_at ? new Date(m.created_at).toLocaleTimeString('ru-RU') : ''}</div>
            </div>
        `).join('');
        chatMessages.scrollTop = chatMessages.scrollHeight;

        document.querySelector('.faq-section').style.display = 'none';
        document.querySelector('.support-tickets').style.display = 'none';
        document.getElementById('ticket-chat').classList.remove('hidden');
    } catch (e) {
        notify(e.message, 'error');
    }
}

function closeTicketChat() {
    document.getElementById('ticket-chat').classList.add('hidden');
    document.querySelector('.faq-section').style.display = '';
    document.querySelector('.support-tickets').style.display = '';
    currentTicketId = null;
}

async function sendTicketMessage() {
    if (!currentTicketId) return;
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    if (!message) return;
    try {
        await api(`/api/support/tickets/${currentTicketId}/message`, {
            method: 'POST', body: JSON.stringify({ message })
        });
        input.value = '';
        openTicketChat(currentTicketId);
    } catch (e) {
        notify(e.message, 'error');
    }
}

/* ========== BATTLES ========== */
function createBattle(mode) {
    if (!currentUser) { showModal('login'); return; }
    notify('Батл-режим скоро будет доступен! Следите за обновлениями.', 'info');
}

/* ========== UTILITIES ========== */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/* ========== INIT ========== */
document.addEventListener('DOMContentLoaded', () => {
    loadUser();
    loadCases();
});
