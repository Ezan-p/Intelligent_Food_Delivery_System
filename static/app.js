const menuList = document.getElementById('menuList');
const comboList = document.getElementById('comboList');
const cartItems = document.getElementById('cartItems');
const cartTotal = document.getElementById('cartTotal');
const orderList = document.getElementById('orderList');
const historyList = document.getElementById('historyList');
const submitOrder = document.getElementById('submitOrder');
const customerName = document.getElementById('customerName');
const historyCustomer = document.getElementById('historyCustomer');
const searchHistory = document.getElementById('searchHistory');
const categoryFilter = document.querySelector('.category-filter');
const storeList = document.getElementById('storeList');
const storeSearchInput = document.getElementById('storeSearchInput');
const menuSearchInput = document.getElementById('menuSearchInput');
const selectedStoreBanner = document.getElementById('selectedStoreBanner');
const selectedComboStoreBanner = document.getElementById('selectedComboStoreBanner');
const cartStoreBanner = document.getElementById('cartStoreBanner');
const backToStoresBtn = document.getElementById('backToStoresBtn');
const storeDetailTabs = document.querySelectorAll('.store-detail-tab');

const loginLink = document.getElementById('loginLink');
const userInfo = document.getElementById('userInfo');
const username = document.getElementById('username');
const logoutBtn = document.getElementById('logoutBtn');
const addressName = document.getElementById('addressName');
const addressDetail = document.getElementById('addressDetail');
const addressPhone = document.getElementById('addressPhone');
const isDefault = document.getElementById('isDefault');
const addAddressBtn = document.getElementById('addAddressBtn');
const addressList = document.getElementById('addressList');

const pages = document.querySelectorAll('.page');
const menuItems = document.querySelectorAll('.menu-item');
const addressMenuBtn = document.getElementById('addressMenuBtn');

const STORAGE_PREFIX = 'customer';
let menuData = [];
let categoryData = [];
let comboData = [];
let storeData = [];
let cart = [];
let currentCategory = 'all';
let currentUser = null;
let sessionId = null;
let selectedStore = null;
let realtimeRefreshTimer = null;
let storeSearchKeyword = '';
let menuSearchKeyword = '';
let currentStoreTab = 'menu';
let toastTimer = null;

function authHeaders() {
    return sessionId ? { 'X-Session-ID': sessionId } : {};
}

function apiFetch(url, options = {}) {
    const method = (options.method || 'GET').toUpperCase();
    const config = {
        cache: 'no-store',
        ...options
    };

    if (method === 'GET') {
        const separator = url.includes('?') ? '&' : '?';
        return fetch(`${url}${separator}_ts=${Date.now()}`, config);
    }

    return fetch(url, config);
}

function switchPage(pageName) {
    pages.forEach(page => page.classList.remove('active'));
    const targetPage = document.getElementById(`page-${pageName}`);
    if (targetPage) targetPage.classList.add('active');
    menuItems.forEach(item => item.classList.toggle('active', item.dataset.page === pageName));
}

function showStoreTab(tabName) {
    currentStoreTab = tabName;
    storeDetailTabs.forEach(tab => {
        tab.classList.toggle('active', tab.dataset.storeTab === tabName);
    });
    document.querySelectorAll('.store-detail-panel').forEach(panel => {
        panel.classList.toggle('active', panel.id === `store-tab-${tabName}`);
    });
}

function formatPrice(price) {
    return Number(price).toFixed(2);
}

function showToast(message) {
    let toast = document.getElementById('appToast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'appToast';
        toast.className = 'app-toast';
        document.body.appendChild(toast);
    }

    toast.textContent = message;
    toast.classList.add('visible');

    if (toastTimer) {
        clearTimeout(toastTimer);
    }
    toastTimer = setTimeout(() => {
        toast.classList.remove('visible');
    }, 1800);
}

function saveSelectedStore() {
    if (selectedStore) {
        localStorage.setItem(`${STORAGE_PREFIX}:selectedStore`, JSON.stringify(selectedStore));
    } else {
        localStorage.removeItem(`${STORAGE_PREFIX}:selectedStore`);
    }
}

function stopRealtimeRefresh() {
    if (realtimeRefreshTimer) {
        clearInterval(realtimeRefreshTimer);
        realtimeRefreshTimer = null;
    }
}

function syncCartStoreInfo() {
    if (!selectedStore || !cart.length) return;
    cart.forEach(item => {
        if (item.store_id === selectedStore.id) {
            item.store_name = selectedStore.name;
        }
    });
}

function syncCartItemPrices() {
    if (!cart.length) return;

    let changed = false;
    cart.forEach(cartItem => {
        if (cartItem.type === 'item') {
            const latestItem = menuData.find(menuItem => menuItem.id === cartItem.id);
            if (latestItem) {
                const latestPrice = Number(latestItem.price);
                if (Number(cartItem.price) !== latestPrice || cartItem.name !== latestItem.name) {
                    cartItem.price = latestPrice;
                    cartItem.name = latestItem.name;
                    changed = true;
                }
            }
        }

        if (cartItem.type === 'combo') {
            const latestCombo = comboData.find(comboItem => comboItem.id === cartItem.id);
            if (latestCombo) {
                const latestPrice = Number(latestCombo.price) * Number(latestCombo.discount);
                if (Number(cartItem.price) !== latestPrice || cartItem.name !== latestCombo.name) {
                    cartItem.price = latestPrice;
                    cartItem.name = latestCombo.name;
                    changed = true;
                }
            }
        }
    });

    if (changed) {
        renderCart();
    }
}

function startRealtimeRefresh() {
    stopRealtimeRefresh();
    if (!sessionId || !currentUser) return;

    realtimeRefreshTimer = setInterval(() => {
        if (document.hidden) return;
        loadStores(true);
    }, 3000);
}

function loadSelectedStore() {
    const saved = localStorage.getItem(`${STORAGE_PREFIX}:selectedStore`);
    selectedStore = saved ? JSON.parse(saved) : null;
}

function renderSelectedStoreState() {
    const text = selectedStore
        ? `当前店铺：${selectedStore.name} · ${selectedStore.business_status || '营业中'} · ${selectedStore.business_hours || '09:00-22:00'} · 评分 ${Number(selectedStore.rating || 0).toFixed(1)} · 配送费 ¥${formatPrice(selectedStore.delivery_fee || 0)} · 起送 ¥${formatPrice(selectedStore.min_order_amount || 0)}`
        : '尚未选择店铺。';
    selectedStoreBanner.textContent = text;
    selectedComboStoreBanner.textContent = text;
    cartStoreBanner.textContent = selectedStore ? `当前购物车店铺：${selectedStore.name}` : '请选择店铺后再加购。';
}

function loadStores(isSilent = false) {
    apiFetch('/api/stores', { headers: authHeaders() })
        .then(response => response.json())
        .then(data => {
            storeData = data.stores || [];
            if (selectedStore) {
                selectedStore = storeData.find(store => store.id === selectedStore.id) || null;
            }
            saveSelectedStore();
            syncCartStoreInfo();
            renderStoreList();
            renderSelectedStoreState();
            if (selectedStore) {
                loadStoreData(isSilent);
            }
        });
}

function renderStoreList() {
    const keyword = storeSearchKeyword.trim().toLowerCase();
    const filteredStores = keyword
        ? storeData.filter(store => {
            const haystack = [
                store.name,
                store.description,
                store.announcement,
                store.business_status
            ].join(' ').toLowerCase();
            return haystack.includes(keyword);
        })
        : storeData;

    storeList.innerHTML = filteredStores.length
        ? filteredStores.map(store => `
            <button class="service-card ${selectedStore && selectedStore.id === store.id ? 'selected-store-card' : ''}" onclick="selectStore(${store.id})">
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
                    <span>营业时间：${store.business_hours || '09:00-22:00'}</span>
                    <span>评分：${Number(store.rating || 0).toFixed(1)}</span>
                    <span>月售：${store.monthly_sales || 0}</span>
                    <span>配送费：¥${formatPrice(store.delivery_fee || 0)}</span>
                    <span>起送价：¥${formatPrice(store.min_order_amount || 0)}</span>
                </div>
                <div class="store-announcement">${store.announcement || '暂无公告'}</div>
                <span class="service-entry">${selectedStore && selectedStore.id === store.id ? '当前已选' : '进入店铺'}</span>
            </button>`).join('')
        : `<p>${keyword ? '未找到符合条件的店铺。' : '当前暂无可用店铺。'}</p>`;
}

function selectStore(storeId) {
    const store = storeData.find(item => item.id === storeId);
    if (!store) return;
    if (cart.length && selectedStore && selectedStore.id !== storeId) {
        if (!confirm('切换店铺会清空当前购物车，是否继续？')) return;
        cart = [];
        renderCart();
    }
    selectedStore = store;
    currentCategory = 'all';
    saveSelectedStore();
    renderStoreList();
    renderSelectedStoreState();
    loadStoreData();
    showStoreTab('menu');
    switchPage('store-detail');
}

function loadStoreData(isSilent = false) {
    if (!selectedStore) {
        categoryData = [];
        menuData = [];
        comboData = [];
        renderCategoryFilter();
        renderMenu();
        renderCombos();
        return;
    }
    loadCategories();
    loadMenu(isSilent);
    loadCombos(isSilent);
}

function loadCategories() {
    if (!selectedStore) return;
    apiFetch(`/api/categories?store_id=${selectedStore.id}`, { headers: authHeaders() })
        .then(response => response.json())
        .then(data => {
            categoryData = data.categories || [];
            renderCategoryFilter();
        });
}

function renderCategoryFilter() {
    const filterButtons = categoryFilter.querySelectorAll('.filter-btn:not([data-category="all"])');
    filterButtons.forEach(btn => btn.remove());
    categoryData.forEach(cat => {
        const btn = document.createElement('button');
        btn.className = 'filter-btn';
        btn.dataset.category = String(cat.id);
        btn.textContent = cat.name;
        btn.addEventListener('click', () => filterByCategory(String(cat.id)));
        categoryFilter.appendChild(btn);
    });
}

function filterByCategory(categoryId) {
    currentCategory = categoryId;
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.category === categoryId);
    });
    renderMenu();
}

function loadMenu(isSilent = false) {
    if (!selectedStore) return;
    apiFetch(`/api/menu?store_id=${selectedStore.id}`, { headers: authHeaders() })
        .then(response => response.json())
        .then(data => {
            menuData = data.menu || [];
            renderMenu();
            syncCartItemPrices();
            if (!isSilent) {
                renderCart();
            }
        });
}

function renderMenu() {
    if (!selectedStore) {
        menuList.innerHTML = '<p>请先在店铺列表中选择一家店铺。</p>';
        return;
    }
    let filteredMenu = menuData;
    if (currentCategory !== 'all') {
        filteredMenu = menuData.filter(item => String(item.category_id) === currentCategory);
    }
    const keyword = menuSearchKeyword.trim().toLowerCase();
    if (keyword) {
        filteredMenu = filteredMenu.filter(item => {
            const haystack = [item.name, item.description].join(' ').toLowerCase();
            return haystack.includes(keyword);
        });
    }
    menuList.innerHTML = filteredMenu.length
        ? filteredMenu.map(item => {
            const category = categoryData.find(c => c.id === item.category_id);
            return `
                <div class="menu-card">
                    ${item.image ? `<div class="card-image"><img src="${item.image}" alt="${item.name}" /></div>` : '<div class="card-image no-image">暂无图片</div>'}
                    <h3>${item.name}</h3>
                    <p>${item.description || '暂无描述'}</p>
                    <div class="menu-card-footer">
                        <span class="price">¥${formatPrice(item.price)}</span>
                        <span class="category">${category ? category.name : '未分类'}</span>
                        <button class="primary" onclick="addToCart(${item.id})">加入购物车</button>
                    </div>
                </div>`;
        }).join('')
        : `<p>${keyword ? '未找到符合条件的菜品。' : '当前店铺暂无该分类商品。'}</p>`;
}

function loadCombos(isSilent = false) {
    if (!selectedStore) return;
    apiFetch(`/api/combos?store_id=${selectedStore.id}`, { headers: authHeaders() })
        .then(response => response.json())
        .then(data => {
            comboData = data.combos || [];
            renderCombos();
            syncCartItemPrices();
            if (!isSilent) {
                renderCart();
            }
        });
}

function renderCombos() {
    if (!selectedStore) {
        comboList.innerHTML = '<p>请先在店铺列表中选择一家店铺。</p>';
        return;
    }
    comboList.innerHTML = comboData.length
        ? comboData.map(combo => {
            const itemNames = combo.items.map(id => {
                const item = menuData.find(menuItem => menuItem.id === id);
                return item ? item.name : `商品${id}`;
            }).join('，');
            return `
                <div class="combo-card">
                    <h3>${combo.name}</h3>
                    <p>${combo.description || '暂无描述'}</p>
                    <div class="combo-items">包含商品: ${itemNames}</div>
                    <div class="combo-footer">
                        <span class="price">¥${formatPrice(combo.price * combo.discount)}</span>
                        <span class="original-price">原价 ¥${formatPrice(combo.price)}</span>
                        <span class="discount">${(combo.discount * 100).toFixed(0)}%折扣</span>
                        <button class="primary" onclick="addComboToCart(${combo.id})">加入购物车</button>
                    </div>
                </div>`;
        }).join('')
        : '<p>当前店铺暂无套餐。</p>';
}

function addComboToCart(comboId) {
    if (!selectedStore) {
        alert('请先选择店铺。');
        return;
    }
    const combo = comboData.find(item => item.id === comboId);
    if (!combo) return;
    const existing = cart.find(item => item.id === comboId && item.type === 'combo');
    if (existing) {
        existing.quantity += 1;
    } else {
        cart.push({
            id: combo.id,
            name: combo.name,
            price: combo.price * combo.discount,
            quantity: 1,
            type: 'combo',
            store_id: selectedStore.id,
            store_name: selectedStore.name
        });
    }
    renderCart();
    showToast(`${combo.name} 已加入购物车`);
}

function addToCart(id) {
    if (!selectedStore) {
        alert('请先选择店铺。');
        return;
    }
    const item = menuData.find(menuItem => menuItem.id === id);
    if (!item) return;
    const existing = cart.find(cartItem => cartItem.id === id && cartItem.type === 'item');
    if (existing) {
        existing.quantity += 1;
    } else {
        cart.push({ ...item, quantity: 1, type: 'item', store_id: selectedStore.id, store_name: selectedStore.name });
    }
    renderCart();
    showToast(`${item.name} 已加入购物车`);
}

function renderCart() {
    renderSelectedStoreState();
    if (!cart.length) {
        cartItems.innerHTML = '<p>购物车为空。</p>';
        cartTotal.textContent = '0.00';
        return;
    }
    cartItems.innerHTML = cart.map(item => `
        <div class="cart-item">
            <strong>${item.name}</strong>
            ${item.type === 'combo' ? '<span class="combo-badge">套餐</span>' : ''}
            <span>店铺: ${item.store_name || ''}</span>
            <span>数量: ${item.quantity} × ¥${formatPrice(item.price)}</span>
            <span>小计: ¥${formatPrice(item.quantity * item.price)}</span>
            <button class="secondary" onclick="removeFromCart(${item.id}, '${item.type}')">移除</button>
        </div>`).join('');
    const total = cart.reduce((sum, item) => sum + item.quantity * item.price, 0);
    cartTotal.textContent = formatPrice(total);
}

function removeFromCart(id, type) {
    cart = cart.filter(item => !(item.id === id && item.type === type));
    renderCart();
}

function submitOrderHandler() {
    if (!sessionId || !currentUser) {
        alert('请先登录客户端账户再下单。');
        window.location.href = '/login';
        return;
    }
    if (!selectedStore) {
        alert('请先选择店铺。');
        return;
    }
    if (!cart.length) {
        alert('购物车为空，请先添加商品。');
        return;
    }
    const items = cart.filter(item => item.type === 'item').map(item => ({ id: item.id, quantity: item.quantity }));
    const comboIds = cart.filter(item => item.type === 'combo').map(item => item.id);
    const comboId = comboIds[0] || null;
    if (comboIds.length > 1) {
        alert('当前版本一次订单仅支持提交一个套餐，请拆分下单。');
        return;
    }
    fetch('/api/order', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({ items, combo_id: comboId, store_id: selectedStore.id })
    })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }
            alert('订单提交成功。');
            cart = [];
            renderCart();
            loadOrders();
        });
}

function loadOrders() {
    if (!sessionId) {
        orderList.innerHTML = '<p>登录后可查看自己的订单。</p>';
        return;
    }
    apiFetch('/api/orders', { headers: authHeaders() })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                orderList.innerHTML = `<p>${data.error}</p>`;
                return;
            }
            renderOrders(data.orders || []);
        });
}

function renderOrders(orders) {
    if (!orders.length) {
        orderList.innerHTML = '<p>当前暂无订单。</p>';
        return;
    }
    orderList.innerHTML = orders.slice().reverse().map(order => `
        <div class="order-card">
            <h4>订单 #${order.id} - ${order.customer}</h4>
            <small>店铺: ${order.store_name || '未知店铺'} · 状态: ${order.status} · 下单时间: ${order.created_at}</small>
            <ul class="order-items">
                ${order.items.map(item => `<li>${item.name} × ${item.quantity} = ¥${formatPrice(item.subtotal)}</li>`).join('')}
            </ul>
            <div class="order-summary">总价：¥${formatPrice(order.total)}</div>
            ${order.status === '已接单' ? `<button class="secondary" onclick="cancelOrder(${order.id})">取消订单</button>` : ''}
        </div>`).join('');
}

function searchHistoryHandler() {
    if (!sessionId || !currentUser) {
        alert('请先登录客户端账户。');
        return;
    }
    apiFetch(`/api/orders?customer=${encodeURIComponent(currentUser.username)}`, { headers: authHeaders() })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                historyList.innerHTML = `<p>${data.error}</p>`;
                return;
            }
            renderHistory(data.orders || []);
        });
}

function renderHistory(orders) {
    if (!orders.length) {
        historyList.innerHTML = '<p>未找到相关历史订单。</p>';
        return;
    }
    historyList.innerHTML = orders.slice().reverse().map(order => `
        <div class="order-card history-card">
            <h4>订单 #${order.id} - ${order.customer}</h4>
            <small>店铺: ${order.store_name || '未知店铺'} · 状态: ${order.status} · 下单时间: ${order.created_at}</small>
            <ul class="order-items">
                ${order.items.map(item => `<li>${item.name} × ${item.quantity} = ¥${formatPrice(item.subtotal)}</li>`).join('')}
            </ul>
            <div class="order-summary">总价：¥${formatPrice(order.total)}</div>
        </div>`).join('');
}

function cancelOrder(orderId) {
    fetch(`/api/order/${orderId}/cancel`, { method: 'POST', headers: authHeaders() })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }
            loadOrders();
            searchHistoryHandler();
        });
}

function checkLoginStatus() {
    sessionId = localStorage.getItem(`${STORAGE_PREFIX}:sessionId`);
    const storedUser = localStorage.getItem(`${STORAGE_PREFIX}:user`);
    currentUser = storedUser ? JSON.parse(storedUser) : null;
    if (!sessionId || !currentUser) {
        stopRealtimeRefresh();
        loginLink.style.display = 'block';
        userInfo.style.display = 'none';
        addressMenuBtn.style.display = 'none';
        customerName.value = '';
        historyCustomer.value = '';
        return;
    }
    apiFetch('/api/users/session', { headers: authHeaders() })
        .then(response => response.json())
        .then(data => {
            if (data.error || data.user.role !== 'customer') {
                logout(false);
                return;
            }
            currentUser = data.user;
            localStorage.setItem(`${STORAGE_PREFIX}:user`, JSON.stringify(currentUser));
            loginLink.style.display = 'none';
            userInfo.style.display = 'block';
            username.textContent = currentUser.username;
            addressMenuBtn.style.display = 'flex';
            customerName.value = currentUser.username;
            historyCustomer.value = currentUser.username;
            loadAddresses();
            loadOrders();
            loadStores();
            startRealtimeRefresh();
        });
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
    localStorage.removeItem(`${STORAGE_PREFIX}:selectedStore`);
    stopRealtimeRefresh();
    currentUser = null;
    sessionId = null;
    selectedStore = null;
    loginLink.style.display = 'block';
    userInfo.style.display = 'none';
    addressMenuBtn.style.display = 'none';
    addressList.innerHTML = '<p>登录后可管理地址。</p>';
    orderList.innerHTML = '<p>登录后可查看自己的订单。</p>';
    historyList.innerHTML = '<p>登录后可查询历史订单。</p>';
    if (redirect) window.location.href = '/login';
}

function loadAddresses() {
    if (!sessionId) {
        addressList.innerHTML = '<p>登录后可管理地址。</p>';
        return;
    }
    apiFetch('/api/addresses', { headers: authHeaders() })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                addressList.innerHTML = `<p>${data.error}</p>`;
                return;
            }
            currentUser.addresses = data.addresses || [];
            renderAddresses();
        });
}

function renderAddresses() {
    addressList.innerHTML = currentUser.addresses.length
        ? currentUser.addresses.map(addr => `
            <div class="address-item">
                <div class="address-info">
                    <h4>${addr.name} ${addr.is_default ? '<span class="badge">默认</span>' : ''}</h4>
                    <p>${addr.address}</p>
                    <p>电话: ${addr.phone}</p>
                </div>
                <div class="address-actions">
                    <button class="secondary" onclick="editAddress(${addr.id})">编辑</button>
                    <button class="secondary" onclick="deleteAddress(${addr.id})">删除</button>
                </div>
            </div>`).join('')
        : '<p>暂无地址，请添加收货地址。</p>';
}

function addAddressHandler() {
    if (!sessionId) {
        alert('请先登录客户端账户。');
        return;
    }
    const name = addressName.value.trim();
    const address = addressDetail.value.trim();
    const phone = addressPhone.value.trim();
    const defaultAddr = isDefault.checked;
    if (!name || !address || !phone) {
        alert('请填写所有字段。');
        return;
    }
    fetch('/api/addresses', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({ name, address, phone, is_default: defaultAddr })
    })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }
            addressName.value = '';
            addressDetail.value = '';
            addressPhone.value = '';
            isDefault.checked = false;
            loadAddresses();
        });
}

function editAddress(addressId) {
    const addr = currentUser.addresses.find(item => item.id === addressId);
    if (!addr) return;
    const newName = prompt('收货人名称:', addr.name);
    if (newName === null) return;
    const newAddress = prompt('详细地址:', addr.address);
    if (newAddress === null) return;
    const newPhone = prompt('电话号码:', addr.phone);
    if (newPhone === null) return;
    fetch(`/api/addresses/${addressId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({ name: newName, address: newAddress, phone: newPhone, is_default: addr.is_default })
    })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }
            loadAddresses();
        });
}

function deleteAddress(addressId) {
    if (!confirm('确定删除此地址吗？')) return;
    fetch(`/api/addresses/${addressId}`, { method: 'DELETE', headers: authHeaders() })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }
            loadAddresses();
        });
}

submitOrder.addEventListener('click', submitOrderHandler);
searchHistory.addEventListener('click', searchHistoryHandler);
logoutBtn.addEventListener('click', () => logout());
addAddressBtn.addEventListener('click', addAddressHandler);
menuItems.forEach(item => item.addEventListener('click', () => switchPage(item.dataset.page)));
document.querySelector('[data-category="all"]').addEventListener('click', () => filterByCategory('all'));
backToStoresBtn.addEventListener('click', () => switchPage('stores'));
storeSearchInput.addEventListener('input', event => {
    storeSearchKeyword = event.target.value || '';
    renderStoreList();
});
menuSearchInput.addEventListener('input', event => {
    menuSearchKeyword = event.target.value || '';
    renderMenu();
});
storeDetailTabs.forEach(tab => {
    tab.addEventListener('click', () => showStoreTab(tab.dataset.storeTab));
});

window.selectStore = selectStore;
window.addToCart = addToCart;
window.addComboToCart = addComboToCart;
window.removeFromCart = removeFromCart;
window.cancelOrder = cancelOrder;
window.editAddress = editAddress;
window.deleteAddress = deleteAddress;

window.addEventListener('load', () => {
    loadSelectedStore();
    renderSelectedStoreState();
    showStoreTab(currentStoreTab);
    checkLoginStatus();
    renderCart();
});

document.addEventListener('visibilitychange', () => {
    if (!document.hidden && sessionId && currentUser) {
        loadStores(true);
    }
});
