const adminStats = document.getElementById('adminStats');
const serviceMonitorStats = document.getElementById('serviceMonitorStats');
const serviceMonitorDetails = document.getElementById('serviceMonitorDetails');
const adminStoresList = document.getElementById('adminStoresList');
const merchantUsersList = document.getElementById('merchantUsersList');
const customerUsersList = document.getElementById('customerUsersList');
const recentOrdersList = document.getElementById('recentOrdersList');
const adminLoginLink = document.getElementById('adminLoginLink');
const adminUserInfo = document.getElementById('adminUserInfo');
const adminUsername = document.getElementById('adminUsername');
const adminLogoutBtn = document.getElementById('adminLogoutBtn');

const STORAGE_PREFIX = 'admin';
let sessionId = null;
let currentUser = null;
let adminCustomers = [];
let adminMerchants = [];
let adminStores = [];

function authHeaders() {
    return sessionId ? { 'X-Session-ID': sessionId } : {};
}

function formatPrice(price) {
    return Number(price || 0).toFixed(2);
}

function showPage(pageName) {
    document.querySelectorAll('.menu-item').forEach(button => {
        button.classList.toggle('active', button.dataset.page === pageName);
    });
    document.querySelectorAll('.page').forEach(page => {
        page.classList.toggle('active', page.id === `page-${pageName}`);
    });
}

function bindSidebarNavigation() {
    document.querySelectorAll('.menu-item').forEach(button => {
        button.addEventListener('click', () => showPage(button.dataset.page));
    });
}

function renderAuthState() {
    if (sessionId && currentUser) {
        adminLoginLink.style.display = 'none';
        adminUserInfo.style.display = 'block';
        adminUsername.textContent = currentUser.username;
    } else {
        adminLoginLink.style.display = 'block';
        adminUserInfo.style.display = 'none';
    }
}

function logout(redirect = true) {
    if (sessionId) {
        fetch('/api/users/logout', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId })
        });
    }
    localStorage.removeItem(`${STORAGE_PREFIX}:sessionId`);
    localStorage.removeItem(`${STORAGE_PREFIX}:user`);
    sessionId = null;
    currentUser = null;
    renderAuthState();
    if (redirect) {
        window.location.href = '/login';
    }
}

function renderStats(stats) {
    adminStats.innerHTML = `
        <div class="stat-card"><h3>账户总数</h3><div class="stat-value">${stats.user_count}</div></div>
        <div class="stat-card"><h3>客户端用户</h3><div class="stat-value">${stats.customer_count}</div></div>
        <div class="stat-card"><h3>商家用户</h3><div class="stat-value">${stats.merchant_count}</div></div>
        <div class="stat-card"><h3>异常关注用户</h3><div class="stat-value">${stats.flagged_user_count}</div></div>
        <div class="stat-card"><h3>禁用账户</h3><div class="stat-value">${stats.disabled_user_count}</div></div>
        <div class="stat-card"><h3>店铺数量</h3><div class="stat-value">${stats.store_count}</div></div>
        <div class="stat-card"><h3>上架店铺</h3><div class="stat-value">${stats.active_store_count}</div></div>
        <div class="stat-card"><h3>下架店铺</h3><div class="stat-value">${stats.inactive_store_count}</div></div>
        <div class="stat-card"><h3>订单总数</h3><div class="stat-value">${stats.order_count}</div></div>
        <div class="stat-card"><h3>平台收入</h3><div class="stat-value">¥${formatPrice(stats.total_revenue)}</div></div>
        <div class="stat-card"><h3>商品数量</h3><div class="stat-value">${stats.menu_count}</div></div>
        <div class="stat-card"><h3>套餐数量</h3><div class="stat-value">${stats.combo_count}</div></div>`;
}

function statusLabel(status) {
    return status === 'disabled' ? '已禁用' : '正常';
}

function riskLabel(status) {
    return status === 'flagged' ? '异常关注' : '正常';
}

function renderUserManagement(container, users, emptyText) {
    container.innerHTML = users.length
        ? users.map(user => `
        <div class="order-card">
            <h4>${user.username}</h4>
            <small>角色: ${user.role_label} · 电话: ${user.phone || '未填写'} · 注册时间: ${user.created_at || '未知'}</small>
            <div class="order-summary">账户状态：${statusLabel(user.account_status)} · 风险状态：${riskLabel(user.risk_status)}${user.store_name ? ` · 店铺：${user.store_name}` : ''}</div>
            <div class="analysis-summary">管理员备注：${user.admin_note || '暂无备注'}</div>
            <div class="form-actions-row">
                <button class="secondary" onclick="toggleUserAccount(${user.id})">${user.account_status === 'active' ? '禁用账户' : '恢复账户'}</button>
                <button class="secondary" onclick="toggleUserRisk(${user.id})">${user.risk_status === 'flagged' ? '取消异常' : '标记异常'}</button>
                <button class="secondary" onclick="editUserNote(${user.id})">编辑备注</button>
            </div>
        </div>`).join('')
        : `<p>${emptyText}</p>`;
}

function renderStores(stores) {
    adminStores = stores;
    adminStoresList.innerHTML = stores.length
        ? stores.map(store => `
        <article class="service-card">
            <div class="store-cover">
                <img src="${store.cover_image_url}" alt="${store.name} 封面" />
            </div>
            <div class="store-card-header">
                <img class="store-avatar" src="${store.avatar_url}" alt="${store.name} 头像" />
                <div>
                    <span class="service-tag">${store.business_status || '营业中'}</span>
                    <h3>${store.name}</h3>
                </div>
            </div>
            <p>${store.description || '暂无店铺介绍。'}</p>
            <div class="store-meta-grid">
                <span>商家：${store.owner_username || '未知商家'}</span>
                <span>营业时间：${store.business_hours || '09:00-22:00'}</span>
                <span>评分：${Number(store.rating || 0).toFixed(1)}</span>
                <span>月售：${store.monthly_sales || 0}</span>
                <span>商品数：${store.menu_count || 0}</span>
                <span>套餐数：${store.combo_count || 0}</span>
                <span>已完成订单：${store.completed_order_count || 0}</span>
                <span>总营收：¥${formatPrice(store.total_revenue)}</span>
                <span>展示状态：${store.status === 'active' ? '上架展示' : '下架隐藏'}</span>
                <span>配送费：¥${formatPrice(store.delivery_fee)}</span>
            </div>
            <div class="store-announcement">${store.announcement || '暂无公告'}</div>
            <div class="form-actions-row">
                <button class="secondary" onclick="toggleStoreStatus(${store.id})">${store.status === 'active' ? '下架店铺' : '上架店铺'}</button>
                <button class="secondary" onclick="toggleStoreBusiness(${store.id})">切换营业状态</button>
                <button class="secondary" onclick="editStoreAnnouncement(${store.id})">编辑公告</button>
            </div>
        </article>`).join('')
        : '<p>暂无店铺。</p>';
}

function renderOrders(orders) {
    recentOrdersList.innerHTML = orders.length
        ? orders.map(order => `
        <div class="order-card">
            <h4>订单 #${order.id} - ${order.customer}</h4>
            <small>店铺: ${order.store_name || '未知店铺'} · 状态: ${order.status} · 下单时间: ${order.created_at}</small>
            <ul class="order-items">
                ${order.items.map(item => `<li>${item.name} × ${item.quantity} = ¥${formatPrice(item.subtotal)}</li>`).join('')}
            </ul>
            <div class="order-summary">总价：¥${formatPrice(order.total)}</div>
        </div>`).join('')
        : '<p>暂无订单。</p>';
}

function renderServiceMonitor(monitor) {
    serviceMonitorStats.innerHTML = `
        <div class="stat-card"><h3>AI客服调用</h3><div class="stat-value">${monitor.ai_chat_requests || 0}</div></div>
        <div class="stat-card"><h3>AI客服失败</h3><div class="stat-value">${monitor.ai_chat_failures || 0}</div></div>
        <div class="stat-card"><h3>点餐助手调用</h3><div class="stat-value">${monitor.smart_order_requests || 0}</div></div>
        <div class="stat-card"><h3>点餐助手失败</h3><div class="stat-value">${monitor.smart_order_failures || 0}</div></div>
        <div class="stat-card"><h3>数据分析调用</h3><div class="stat-value">${monitor.data_analysis_requests || 0}</div></div>
        <div class="stat-card"><h3>数据分析失败</h3><div class="stat-value">${monitor.data_analysis_failures || 0}</div></div>`;

    serviceMonitorDetails.innerHTML = `
        <div class="analysis-panel">
            <h3>远程 AI 配置</h3>
            <div class="analysis-list-item"><strong>配置状态</strong><span>${monitor.remote_ai_configured ? '已配置' : '未配置'}</span></div>
            <div class="analysis-list-item"><strong>模型名称</strong><span>${monitor.remote_ai_model || '未指定'}</span></div>
            <div class="analysis-list-item"><strong>当前生效地址</strong><span>${monitor.active_remote_ai_url || '未配置'}</span></div>
        </div>
        <div class="analysis-panel">
            <h3>最近调用时间</h3>
            <div class="analysis-list-item"><strong>AI客服</strong><span>${monitor.last_ai_chat_at || '暂无记录'}</span></div>
            <div class="analysis-list-item"><strong>智能点餐助手</strong><span>${monitor.last_smart_order_at || '暂无记录'}</span></div>
            <div class="analysis-list-item"><strong>数据智能分析</strong><span>${monitor.last_data_analysis_at || '暂无记录'}</span></div>
        </div>`;
}

function loadOverview() {
    fetch('/api/admin/overview', { headers: authHeaders() })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                adminStats.innerHTML = `<p>${data.error}</p>`;
                serviceMonitorStats.innerHTML = '';
                serviceMonitorDetails.innerHTML = '';
                adminStoresList.innerHTML = '';
                merchantUsersList.innerHTML = '';
                customerUsersList.innerHTML = '';
                recentOrdersList.innerHTML = '';
                return;
            }
            adminCustomers = data.customers || [];
            adminMerchants = data.merchants || [];
            renderStats(data.stats || {});
            renderServiceMonitor(data.service_monitor || {});
            renderStores(data.stores || []);
            renderUserManagement(merchantUsersList, adminMerchants, '暂无商家账户。');
            renderUserManagement(customerUsersList, adminCustomers, '暂无客户端用户。');
            renderOrders(data.recent_orders || []);
        });
}

function updateAdminUser(userId, payload) {
    fetch(`/api/admin/users/${userId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify(payload)
    })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }
            loadOverview();
        });
}

function toggleUserAccount(userId) {
    const user = [...adminCustomers, ...adminMerchants].find(item => item.id === userId);
    if (!user) return;
    const nextStatus = user.account_status === 'active' ? 'disabled' : 'active';
    updateAdminUser(userId, {
        account_status: nextStatus,
        risk_status: user.risk_status,
        admin_note: user.admin_note || ''
    });
}

function toggleUserRisk(userId) {
    const user = [...adminCustomers, ...adminMerchants].find(item => item.id === userId);
    if (!user) return;
    const nextRisk = user.risk_status === 'flagged' ? 'normal' : 'flagged';
    updateAdminUser(userId, {
        account_status: user.account_status,
        risk_status: nextRisk,
        admin_note: user.admin_note || ''
    });
}

function editUserNote(userId) {
    const user = [...adminCustomers, ...adminMerchants].find(item => item.id === userId);
    if (!user) return;
    const note = prompt('请输入管理员备注：', user.admin_note || '');
    if (note === null) return;
    updateAdminUser(userId, {
        account_status: user.account_status,
        risk_status: user.risk_status,
        admin_note: note.trim()
    });
}

function updateAdminStore(storeId, payload) {
    fetch(`/api/admin/stores/${storeId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify(payload)
    })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }
            loadOverview();
        });
}

function toggleStoreStatus(storeId) {
    const store = adminStores.find(item => item.id === storeId);
    if (!store) return;
    updateAdminStore(storeId, {
        status: store.status === 'active' ? 'inactive' : 'active',
        business_status: store.business_status,
        announcement: store.announcement || ''
    });
}

function toggleStoreBusiness(storeId) {
    const store = adminStores.find(item => item.id === storeId);
    if (!store) return;
    const nextBusiness = store.business_status === '营业中' ? '休息中' : '营业中';
    updateAdminStore(storeId, {
        status: store.status,
        business_status: nextBusiness,
        announcement: store.announcement || ''
    });
}

function editStoreAnnouncement(storeId) {
    const store = adminStores.find(item => item.id === storeId);
    if (!store) return;
    const announcement = prompt('请输入店铺公告：', store.announcement || '');
    if (announcement === null) return;
    updateAdminStore(storeId, {
        status: store.status,
        business_status: store.business_status,
        announcement: announcement.trim()
    });
}

function checkLoginStatus() {
    sessionId = localStorage.getItem(`${STORAGE_PREFIX}:sessionId`);
    const storedUser = localStorage.getItem(`${STORAGE_PREFIX}:user`);
    currentUser = storedUser ? JSON.parse(storedUser) : null;
    renderAuthState();

    if (!sessionId) {
        adminStats.innerHTML = '<p>登录管理员账户后可查看平台全局数据。</p>';
        serviceMonitorStats.innerHTML = '<p>登录后可查看智能服务监控。</p>';
        adminStoresList.innerHTML = '<p>登录后可查看店铺列表。</p>';
        return;
    }

    fetch('/api/users/session', { headers: authHeaders() })
        .then(response => response.json())
        .then(data => {
            if (data.error || data.user.role !== 'admin') {
                logout(false);
                return;
            }
            currentUser = data.user;
            localStorage.setItem(`${STORAGE_PREFIX}:user`, JSON.stringify(currentUser));
            renderAuthState();
            loadOverview();
        });
}

adminLogoutBtn.addEventListener('click', () => logout());
window.toggleUserAccount = toggleUserAccount;
window.toggleUserRisk = toggleUserRisk;
window.editUserNote = editUserNote;
window.toggleStoreStatus = toggleStoreStatus;
window.toggleStoreBusiness = toggleStoreBusiness;
window.editStoreAnnouncement = editStoreAnnouncement;

window.addEventListener('load', () => {
    bindSidebarNavigation();
    showPage('overview');
    checkLoginStatus();
});
