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
const homeAddressBtn = document.getElementById('homeAddressBtn');
const currentAddressDisplay = document.getElementById('currentAddressDisplay');
const messageCenterBtn = document.getElementById('messageCenterBtn');
const profileCenterBtn = document.getElementById('profileCenterBtn');
const quickCategoryStrip = document.getElementById('quickCategoryStrip');
const floatingCartBtn = document.getElementById('floatingCartBtn');
const floatingCartCount = document.getElementById('floatingCartCount');
const floatingCartAmount = document.getElementById('floatingCartAmount');
const selectedStoreBanner = document.getElementById('selectedStoreBanner');
const selectedComboStoreBanner = document.getElementById('selectedComboStoreBanner');
const cartStoreBanner = document.getElementById('cartStoreBanner');
const backToStoresBtn = document.getElementById('backToStoresBtn');
const storeDetailTabs = document.querySelectorAll('.store-detail-tab');
const reviewList = document.getElementById('reviewList');
const storeReviewSummary = document.getElementById('storeReviewSummary');
const favoriteStoreList = document.getElementById('favoriteStoreList');
const favoriteItemList = document.getElementById('favoriteItemList');
const recentViewList = document.getElementById('recentViewList');
const reorderList = document.getElementById('reorderList');
const reviewModal = document.getElementById('reviewModal');
const closeReviewModal = document.getElementById('closeReviewModal');
const reviewOrderMeta = document.getElementById('reviewOrderMeta');
const reviewRating = document.getElementById('reviewRating');
const deliveryRating = document.getElementById('deliveryRating');
const packagingRating = document.getElementById('packagingRating');
const tasteRating = document.getElementById('tasteRating');
const reviewContent = document.getElementById('reviewContent');
const reviewImage = document.getElementById('reviewImage');
const reviewImagePreview = document.getElementById('reviewImagePreview');
const submitReviewBtn = document.getElementById('submitReviewBtn');
const accountSummaryCard = document.getElementById('accountSummaryCard');
const accountInfoList = document.getElementById('accountInfoList');
const mySectionLinks = document.querySelectorAll('.my-subnav-link');
const mySections = document.querySelectorAll('.my-section');
const profileDisplayName = document.getElementById('profileDisplayName');
const profilePhone = document.getElementById('profilePhone');
const profileEmail = document.getElementById('profileEmail');
const profileGender = document.getElementById('profileGender');
const profileBirthday = document.getElementById('profileBirthday');
const profileBio = document.getElementById('profileBio');
const saveProfileBtn = document.getElementById('saveProfileBtn');

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
const CART_STORAGE_KEY = `${STORAGE_PREFIX}:cart`;
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
let storeShortcutKeyword = 'all';
let menuSearchKeyword = '';
let currentStoreTab = 'menu';
let toastTimer = null;
let favoriteStoreIds = [];
let favoriteMenuIds = [];
let favoriteItems = [];
let recentViews = [];
let reorderOrders = [];
let currentStoreReviews = [];
let currentReviewOrderId = null;
let reviewImageData = null;
let pendingAiTarget = null;

function loadCartFromStorage() {
    const saved = localStorage.getItem(CART_STORAGE_KEY);
    cart = saved ? JSON.parse(saved) : [];
}

function saveCartToStorage() {
    localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(cart));
}

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
    if (categoryFilter) {
        categoryFilter.style.display = tabName === 'menu' ? 'flex' : 'none';
    }
}

function showMySection(sectionName) {
    mySectionLinks.forEach(link => {
        link.classList.toggle('active', link.dataset.mySection === sectionName);
    });
    mySections.forEach(section => {
        section.classList.toggle('active', section.id === `my-section-${sectionName}`);
    });
}

function formatPrice(price) {
    return Number(price).toFixed(2);
}

function getStoreEta(store) {
    const base = 22 + Number(store.delivery_fee || 0) * 3 + (Number(store.monthly_sales || 0) > 80 ? 6 : 0);
    return `${Math.max(18, Math.round(base))}-${Math.max(28, Math.round(base + 10))} 分钟`;
}

function getStoreTags(store) {
    const text = [store.name, store.description, store.announcement].join(' ').toLowerCase();
    const tags = [];
    if (text.includes('轻食') || text.includes('沙拉')) tags.push('轻食');
    if (text.includes('奶茶') || text.includes('果饮') || text.includes('饮')) tags.push('饮品');
    if (text.includes('甜') || text.includes('蛋糕') || text.includes('面包')) tags.push('甜品');
    if (text.includes('夜') || text.includes('麻辣') || text.includes('烧烤') || text.includes('龙虾')) tags.push('夜宵');
    if (text.includes('盖饭') || text.includes('套餐') || text.includes('快')) tags.push('快餐');
    if (store.business_status && !tags.includes(store.business_status)) tags.push(store.business_status);
    if (Number(store.rating || 0) >= 4.8) tags.push('高评分');
    return [...new Set(tags)].slice(0, 4);
}

function updateCurrentAddressDisplay() {
    if (!currentUser || !Array.isArray(currentUser.addresses) || !currentUser.addresses.length) {
        currentAddressDisplay.textContent = '请先登录后选择地址';
        return;
    }
    const defaultAddress = currentUser.addresses.find(item => item.is_default) || currentUser.addresses[0];
    currentAddressDisplay.textContent = defaultAddress ? `${defaultAddress.name} · ${defaultAddress.address}` : '请前往地址管理完善信息';
}

function renderAccountProfile() {
    if (!accountSummaryCard || !accountInfoList) return;

    if (!currentUser) {
        accountSummaryCard.innerHTML = `
            <span class="service-tag">未登录</span>
            <h3>请先登录客户端账户</h3>
            <p>登录后可查看个人主页、账号信息、地址、收藏与评价入口。</p>
        `;
        accountInfoList.innerHTML = '<p>登录后可查看账号信息。</p>';
        if (profileDisplayName) profileDisplayName.value = '';
        if (profilePhone) profilePhone.value = '';
        if (profileEmail) profileEmail.value = '';
        if (profileGender) profileGender.value = '';
        if (profileBirthday) profileBirthday.value = '';
        if (profileBio) profileBio.value = '';
        return;
    }

    const addressCount = Array.isArray(currentUser.addresses) ? currentUser.addresses.length : 0;
    const displayName = currentUser.display_name || currentUser.username;
    accountSummaryCard.innerHTML = `
        <span class="service-tag">${currentUser.role === 'customer' ? '用户账户' : '账户'}</span>
        <h3>${displayName}</h3>
        <p>${currentUser.phone || '未绑定手机号'}</p>
        <div class="store-feed-meta">
            <span>地址 ${addressCount}</span>
            <span>收藏店铺 ${favoriteStoreIds.length}</span>
            <span>收藏菜品 ${favoriteMenuIds.length}</span>
            <span>最近浏览 ${recentViews.length}</span>
        </div>
    `;
    accountInfoList.innerHTML = `
        <h4>账号概览</h4>
        <p>用户名：${currentUser.username}</p>
        <p>昵称：${currentUser.display_name || '未填写'}</p>
        <p>手机号：${currentUser.phone || '未填写'}</p>
        <p>邮箱：${currentUser.email || '未填写'}</p>
        <p>性别：${currentUser.gender || '未填写'}</p>
        <p>生日：${currentUser.birthday || '未填写'}</p>
        <p>角色：${currentUser.role || 'customer'}</p>
        <p>默认地址：${(() => {
            const defaultAddress = (currentUser.addresses || []).find(item => item.is_default) || (currentUser.addresses || [])[0];
            return defaultAddress ? `${defaultAddress.name} · ${defaultAddress.address}` : '未设置';
        })()}</p>
        <p>个人简介：${currentUser.bio || '未填写'}</p>
    `;
    if (profileDisplayName) profileDisplayName.value = currentUser.display_name || '';
    if (profilePhone) profilePhone.value = currentUser.phone || '';
    if (profileEmail) profileEmail.value = currentUser.email || '';
    if (profileGender) profileGender.value = currentUser.gender || '';
    if (profileBirthday) profileBirthday.value = currentUser.birthday || '';
    if (profileBio) profileBio.value = currentUser.bio || '';
}

function saveProfileHandler() {
    if (!sessionId || !currentUser) {
        alert('请先登录客户端账户。');
        return;
    }
    fetch('/api/users/profile', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({
            display_name: profileDisplayName.value.trim(),
            phone: profilePhone.value.trim(),
            email: profileEmail.value.trim(),
            gender: profileGender.value,
            birthday: profileBirthday.value,
            bio: profileBio.value.trim()
        })
    })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }
            currentUser = data.user;
            localStorage.setItem(`${STORAGE_PREFIX}:user`, JSON.stringify(currentUser));
            renderAccountProfile();
            updateCurrentAddressDisplay();
            showToast(data.message || '个人信息已保存');
        });
}

function syncQuickCategoryState() {
    if (!quickCategoryStrip) return;
    quickCategoryStrip.querySelectorAll('.quick-category-chip').forEach(button => {
        button.classList.toggle('active', button.dataset.storeShortcut === storeShortcutKeyword);
    });
}

function updateFloatingCart() {
    const count = cart.reduce((sum, item) => sum + Number(item.quantity || 0), 0);
    const amount = cart.reduce((sum, item) => sum + Number(item.quantity || 0) * Number(item.price || 0), 0);
    floatingCartCount.textContent = `${count} 件商品`;
    floatingCartAmount.textContent = formatPrice(amount);
    floatingCartBtn.classList.toggle('has-items', count > 0);
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

function readFileAsDataUrl(file) {
    return new Promise((resolve, reject) => {
        if (!file) {
            resolve(null);
            return;
        }
        const reader = new FileReader();
        reader.onload = event => resolve(event.target.result);
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
}

function isFavoriteStore(storeId) {
    return favoriteStoreIds.includes(storeId);
}

function isFavoriteItem(itemId) {
    return favoriteMenuIds.includes(itemId);
}

function saveSelectedStore() {
    if (selectedStore) {
        localStorage.setItem(`${STORAGE_PREFIX}:selectedStore`, JSON.stringify(selectedStore));
    } else {
        localStorage.removeItem(`${STORAGE_PREFIX}:selectedStore`);
    }
}

function loadPendingAiTarget() {
    const raw = localStorage.getItem(`${STORAGE_PREFIX}:pendingAiTarget`);
    pendingAiTarget = raw ? JSON.parse(raw) : null;
}

function clearPendingAiTarget() {
    pendingAiTarget = null;
    localStorage.removeItem(`${STORAGE_PREFIX}:pendingAiTarget`);
}

function highlightPendingTarget() {
    if (!pendingAiTarget) return;
    const selector = pendingAiTarget.target_type === 'combo'
        ? `[data-combo-id="${pendingAiTarget.combo_id}"]`
        : pendingAiTarget.target_type === 'item'
            ? `[data-item-id="${pendingAiTarget.item_id}"]`
            : null;
    if (!selector) return;

    const target = document.querySelector(selector);
    if (!target) return;
    target.classList.add('ai-recommended-target');
    target.scrollIntoView({ behavior: 'smooth', block: 'center' });
    window.setTimeout(() => target.classList.remove('ai-recommended-target'), 2200);
    clearPendingAiTarget();
}

function applyPendingAiTarget() {
    if (!pendingAiTarget || !storeData.length) return;
    const targetStoreId = Number(pendingAiTarget.store_id || 0);
    if (!targetStoreId) {
        clearPendingAiTarget();
        return;
    }
    const targetStore = storeData.find(store => store.id === targetStoreId);
    if (!targetStore) {
        clearPendingAiTarget();
        return;
    }
    selectedStore = targetStore;
    currentCategory = 'all';
    saveSelectedStore();
    renderStoreList();
    renderSelectedStoreState();
    loadStoreData();
    loadReviews();
    showStoreTab(pendingAiTarget.target_type === 'combo' ? 'combos' : 'menu');
    switchPage('store-detail');
    window.setTimeout(highlightPendingTarget, 700);
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
            if (pendingAiTarget) {
                applyPendingAiTarget();
            }
        });
}

function renderStoreList() {
    const keyword = storeSearchKeyword.trim().toLowerCase();
    let filteredStores = keyword
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

    if (storeShortcutKeyword !== 'all') {
        const shortcut = storeShortcutKeyword.toLowerCase();
        filteredStores = filteredStores.filter(store => {
            const haystack = [store.name, store.description, store.announcement, ...getStoreTags(store)].join(' ').toLowerCase();
            return haystack.includes(shortcut);
        });
    }

    storeList.innerHTML = filteredStores.length
        ? filteredStores.map(store => `
            <article class="store-feed-card ${selectedStore && selectedStore.id === store.id ? 'selected-store-card' : ''}">
                <div class="store-feed-media">
                    <img src="${store.cover_image_url}" alt="${store.name} 封面" />
                    <span class="store-eta-badge">预计 ${getStoreEta(store)}</span>
                </div>
                <div class="store-feed-header">
                    <img class="store-avatar" src="${store.avatar_url}" alt="${store.name} 头像" />
                    <div>
                        <span class="service-tag">${store.business_status || '营业中'}</span>
                        <h3>${store.name}</h3>
                        <small>${store.business_hours || '09:00-22:00'}</small>
                    </div>
                </div>
                <p>${store.description || '暂无店铺介绍。'}</p>
                <div class="store-feed-meta">
                    <span>评分 ${Number(store.rating || 0).toFixed(1)}</span>
                    <span>月售 ${store.monthly_sales || 0}</span>
                    <span>配送费 ¥${formatPrice(store.delivery_fee || 0)}</span>
                    <span>起送 ¥${formatPrice(store.min_order_amount || 0)}</span>
                </div>
                <div class="store-tag-row">
                    ${getStoreTags(store).map(tag => `<span class="store-tag-chip">${tag}</span>`).join('')}
                </div>
                <div class="store-announcement">${store.announcement || '暂无公告'}</div>
                <div class="form-actions-row">
                    <button class="primary" onclick="selectStore(${store.id})">进入店铺</button>
                    <button class="secondary" onclick="toggleFavoriteStore(${store.id})">${isFavoriteStore(store.id) ? '取消收藏' : '收藏店铺'}</button>
                </div>
            </article>`).join('')
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
    loadReviews();
    recordRecentView({ type: 'store', store_id: store.id });
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
                    <div class="menu-card-inner" data-item-id="${item.id}">
                    ${item.image ? `<div class="card-image"><img src="${item.image}" alt="${item.name}" /></div>` : '<div class="card-image no-image">暂无图片</div>'}
                    <h3>${item.name}</h3>
                    <p>${item.description || '暂无描述'}</p>
                    <div class="menu-card-footer">
                        <span class="price">¥${formatPrice(item.price)}</span>
                        <span class="category">${category ? category.name : '未分类'}</span>
                        <div class="card-actions">
                            <button class="secondary" onclick="showItemDetail(${item.id})">查看详情</button>
                            <button class="secondary" onclick="toggleFavoriteItem(${item.id})">${isFavoriteItem(item.id) ? '取消收藏' : '收藏菜品'}</button>
                            <button class="primary" onclick="addToCart(${item.id})">加入购物车</button>
                        </div>
                    </div>
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
                    <div class="combo-card-inner" data-combo-id="${combo.id}">
                    <h3>${combo.name}</h3>
                    <p>${combo.description || '暂无描述'}</p>
                    <div class="combo-items">包含商品: ${itemNames}</div>
                    <div class="combo-footer">
                        <span class="price">¥${formatPrice(combo.price * combo.discount)}</span>
                        <span class="original-price">原价 ¥${formatPrice(combo.price)}</span>
                        <span class="discount">${(combo.discount * 100).toFixed(0)}%折扣</span>
                        <button class="primary" onclick="addComboToCart(${combo.id})">加入购物车</button>
                    </div>
                    </div>
                </div>`;
        }).join('')
        : '<p>当前店铺暂无套餐。</p>';
}

function loadFavorites() {
    if (!sessionId) {
        favoriteStoreList.innerHTML = '<p>登录后可查看收藏店铺。</p>';
        favoriteItemList.innerHTML = '<p>登录后可查看收藏菜品。</p>';
        recentViewList.innerHTML = '<p>登录后可查看最近浏览记录。</p>';
        reorderList.innerHTML = '<p>登录后可使用一键再来一单。</p>';
        return;
    }

    apiFetch('/api/favorites', { headers: authHeaders() })
        .then(response => response.json())
        .then(data => {
            favoriteStoreIds = data.favorite_store_ids || [];
            favoriteMenuIds = data.favorite_menu_ids || [];
            favoriteItems = data.items || [];
            recentViews = data.recent_views || [];
            reorderOrders = data.recent_orders || [];
            renderStoreList();
            renderFavoriteStores(data.stores || []);
            renderFavoriteItems(favoriteItems);
            renderRecentViews();
            renderReorderOrders();
            renderAccountProfile();
        });
}

function renderFavoriteStores(stores) {
    favoriteStoreList.innerHTML = stores.length
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
                <div class="form-actions-row">
                    <button class="primary" onclick="selectStore(${store.id})">进入店铺</button>
                    <button class="secondary" onclick="toggleFavoriteStore(${store.id})">取消收藏</button>
                </div>
            </article>`).join('')
        : '<p>暂无收藏店铺。</p>';
}

function renderFavoriteItems(items) {
    favoriteItemList.innerHTML = items.length
        ? items.map(item => `
            <div class="menu-card">
                ${item.image ? `<div class="card-image"><img src="${item.image}" alt="${item.name}" /></div>` : '<div class="card-image no-image">暂无图片</div>'}
                <h3>${item.name}</h3>
                <p>${item.description || '暂无描述'}</p>
                <div class="menu-card-footer">
                    <span class="price">¥${formatPrice(item.price)}</span>
                    <div class="card-actions">
                        <button class="secondary" onclick="showFavoriteItem(${item.id})">查看</button>
                        <button class="secondary" onclick="toggleFavoriteItem(${item.id})">取消收藏</button>
                    </div>
                </div>
            </div>`).join('')
        : '<p>暂无收藏菜品。</p>';
}

function renderRecentViews() {
    recentViewList.innerHTML = recentViews.length
        ? recentViews.map(view => `
            <div class="order-card">
                <h4>${view.title || '浏览记录'}</h4>
                <small>${view.subtitle || '暂无附加信息'} · 浏览时间: ${view.viewed_at || '未知'}</small>
                <div class="form-actions-row">
                    ${view.type === 'store'
                        ? `<button class="primary" onclick="selectStore(${view.store_id})">进入店铺</button>`
                        : `<button class="primary" onclick="showFavoriteItem(${view.item_id})">查看菜品</button>`}
                </div>
            </div>`).join('')
        : '<p>暂无最近浏览记录。</p>';
}

function renderReorderOrders() {
    reorderList.innerHTML = reorderOrders.length
        ? reorderOrders.map(order => `
            <div class="order-card">
                <h4>订单 #${order.id} - ${order.store_name || '未知店铺'}</h4>
                <small>状态: ${order.status} · 下单时间: ${order.created_at}</small>
                <div class="order-summary">总价：¥${formatPrice(order.total)}</div>
                <div class="form-actions-row">
                    <button class="primary" onclick="reorderOrder(${order.id})">一键再来一单</button>
                </div>
            </div>`).join('')
        : '<p>暂无可复购订单。</p>';
}

function recordRecentView(payload) {
    if (!sessionId) return;
    fetch('/api/recent-views', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify(payload)
    }).then(() => loadFavorites());
}

function showItemDetail(itemId) {
    const item = menuData.find(menuItem => menuItem.id === itemId);
    if (!item) return;
    recordRecentView({ type: 'item', store_id: selectedStore.id, item_id: item.id });
    alert(`${item.name}\n\n${item.description || '暂无描述'}\n价格：¥${formatPrice(item.price)}`);
}

function showFavoriteItem(itemId) {
    const item = favoriteItems.find(menuItem => menuItem.id === itemId) || menuData.find(menuItem => menuItem.id === itemId);
    if (!item) return;
    if (item.store_id) {
        selectStore(item.store_id);
        showStoreTab('menu');
    }
}

function reorderOrder(orderId) {
    if (!sessionId) {
        alert('请先登录客户端账户。');
        return;
    }
    fetch(`/api/orders/${orderId}/reorder`, {
        method: 'POST',
        headers: authHeaders()
    })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }
            const order = data.order;
            const store = storeData.find(item => item.id === order.store_id);
            if (store) {
                selectedStore = store;
                saveSelectedStore();
                renderSelectedStoreState();
                loadStoreData();
            }
            loadOrders();
            searchHistoryHandler();
            loadFavorites();
            switchPage('orders');
            showToast('已成功再来一单');
        });
}

function toggleFavoriteStore(storeId) {
    if (!sessionId) {
        alert('请先登录客户端账户。');
        return;
    }
    fetch(`/api/favorites/stores/${storeId}/toggle`, {
        method: 'POST',
        headers: authHeaders()
    })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }
            favoriteStoreIds = data.favorite_store_ids || [];
            loadFavorites();
            showToast(data.action === 'added' ? '店铺已收藏' : '已取消收藏店铺');
        });
}

function toggleFavoriteItem(itemId) {
    if (!sessionId) {
        alert('请先登录客户端账户。');
        return;
    }
    fetch(`/api/favorites/menu/${itemId}/toggle`, {
        method: 'POST',
        headers: authHeaders()
    })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }
            favoriteMenuIds = data.favorite_menu_ids || [];
            loadFavorites();
            renderMenu();
            showToast(data.action === 'added' ? '菜品已收藏' : '已取消收藏菜品');
        });
}

function loadReviews() {
    if (!selectedStore) {
        reviewList.innerHTML = '<p>请选择店铺后查看评价。</p>';
        storeReviewSummary.textContent = '暂无评价数据。';
        return;
    }
    apiFetch(`/api/reviews?store_id=${selectedStore.id}`)
        .then(response => response.json())
        .then(data => {
            currentStoreReviews = data.reviews || [];
            renderReviews();
        });
}

function renderReviews() {
    if (!currentStoreReviews.length) {
        storeReviewSummary.textContent = '当前店铺暂无评价。';
        reviewList.innerHTML = '<p>当前店铺暂无评价，欢迎完成订单后进行评价。</p>';
        return;
    }
    const avgRating = currentStoreReviews.reduce((sum, review) => sum + Number(review.rating || 0), 0) / currentStoreReviews.length;
    storeReviewSummary.textContent = `累计 ${currentStoreReviews.length} 条评价，平均评分 ${avgRating.toFixed(1)}`;
    reviewList.innerHTML = currentStoreReviews.map(review => `
        <div class="order-card">
            <h4>${review.customer}</h4>
            <small>综合评分 ${Number(review.rating || 0).toFixed(1)} · 配送 ${Number(review.delivery_rating || 0).toFixed(1)} · 包装 ${Number(review.packaging_rating || 0).toFixed(1)} · 口味 ${Number(review.taste_rating || 0).toFixed(1)}</small>
            <div class="analysis-summary">${review.content || '用户未填写文字评价。'}</div>
            ${review.image ? `<div class="card-image"><img src="${review.image}" alt="评价图片" /></div>` : ''}
        </div>`).join('');
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
    updateFloatingCart();
    saveCartToStorage();
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
            <div class="form-actions-row">
                ${order.status === '已接单' ? `<button class="secondary" onclick="cancelOrder(${order.id})">取消订单</button>` : ''}
                ${(order.status === '已完成' || order.status === '已送达') ? `<button class="secondary" onclick="reorderOrder(${order.id})">一键再来一单</button>` : ''}
                ${order.status === '已完成' && !order.reviewed ? `<button class="primary" onclick="openReviewModal(${order.id}, '${(order.store_name || '').replace(/'/g, "\\'")}')">去评价</button>` : ''}
                ${order.reviewed ? '<span class="service-tag">已评价</span>' : ''}
            </div>
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
            <div class="form-actions-row">
                ${(order.status === '已完成' || order.status === '已送达') ? `<button class="secondary" onclick="reorderOrder(${order.id})">一键再来一单</button>` : ''}
                ${order.status === '已完成' && !order.reviewed ? `<button class="primary" onclick="openReviewModal(${order.id}, '${(order.store_name || '').replace(/'/g, "\\'")}')">去评价</button>` : ''}
                ${order.reviewed ? '<span class="service-tag">已评价</span>' : ''}
            </div>
        </div>`).join('');
}

function resetReviewForm() {
    currentReviewOrderId = null;
    reviewRating.value = '';
    deliveryRating.value = '';
    packagingRating.value = '';
    tasteRating.value = '';
    reviewContent.value = '';
    reviewImage.value = '';
    reviewImageData = null;
    reviewImagePreview.innerHTML = '';
}

function openReviewModal(orderId, storeName = '') {
    resetReviewForm();
    currentReviewOrderId = orderId;
    reviewOrderMeta.textContent = `订单 #${orderId}${storeName ? ` · ${storeName}` : ''}`;
    reviewModal.style.display = 'flex';
}

function closeReviewDialog() {
    reviewModal.style.display = 'none';
    resetReviewForm();
}

function submitReviewHandler() {
    if (!sessionId || !currentReviewOrderId) return;

    const payload = {
        rating: Number(reviewRating.value),
        delivery_rating: Number(deliveryRating.value),
        packaging_rating: Number(packagingRating.value),
        taste_rating: Number(tasteRating.value),
        content: reviewContent.value.trim(),
        image: reviewImageData
    };

    if (![payload.rating, payload.delivery_rating, payload.packaging_rating, payload.taste_rating].every(score => score >= 1 && score <= 5)) {
        alert('请将综合评分、配送、包装、口味都填写为 1 到 5 分。');
        return;
    }

    fetch(`/api/orders/${currentReviewOrderId}/review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify(payload)
    })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }
            closeReviewDialog();
            showToast('评价提交成功');
            loadOrders();
            searchHistoryHandler();
            loadFavorites();
            loadReviews();
        });
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
    loadCartFromStorage();
    renderCart();
    if (!sessionId || !currentUser) {
        stopRealtimeRefresh();
        loginLink.style.display = 'block';
        userInfo.style.display = 'none';
        customerName.value = '';
        historyCustomer.value = '';
        renderAccountProfile();
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
            customerName.value = currentUser.username;
            historyCustomer.value = currentUser.username;
            loadAddresses();
            loadOrders();
            loadStores();
            loadFavorites();
            updateCurrentAddressDisplay();
            renderAccountProfile();
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
    localStorage.removeItem(CART_STORAGE_KEY);
    stopRealtimeRefresh();
    currentUser = null;
    sessionId = null;
    selectedStore = null;
    favoriteStoreIds = [];
    favoriteMenuIds = [];
    favoriteItems = [];
    recentViews = [];
    reorderOrders = [];
    currentStoreReviews = [];
    cart = [];
    closeReviewDialog();
    loginLink.style.display = 'block';
    userInfo.style.display = 'none';
    addressList.innerHTML = '<p>登录后可管理地址。</p>';
    orderList.innerHTML = '<p>登录后可查看自己的订单。</p>';
    historyList.innerHTML = '<p>登录后可查询历史订单。</p>';
    favoriteStoreList.innerHTML = '<p>登录后可查看收藏店铺。</p>';
    favoriteItemList.innerHTML = '<p>登录后可查看收藏菜品。</p>';
    recentViewList.innerHTML = '<p>登录后可查看最近浏览记录。</p>';
    reorderList.innerHTML = '<p>登录后可使用一键再来一单。</p>';
    currentAddressDisplay.textContent = '请先登录后选择地址';
    renderAccountProfile();
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
            updateCurrentAddressDisplay();
            renderAccountProfile();
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
saveProfileBtn.addEventListener('click', saveProfileHandler);
menuItems.forEach(item => item.addEventListener('click', () => switchPage(item.dataset.page)));
mySectionLinks.forEach(link => {
    link.addEventListener('click', () => showMySection(link.dataset.mySection));
});
document.querySelector('[data-category="all"]').addEventListener('click', () => filterByCategory('all'));
backToStoresBtn.addEventListener('click', () => switchPage('home'));
storeSearchInput.addEventListener('input', event => {
    storeSearchKeyword = event.target.value || '';
    renderStoreList();
});
quickCategoryStrip.querySelectorAll('.quick-category-chip').forEach(button => {
    button.addEventListener('click', () => {
        storeShortcutKeyword = button.dataset.storeShortcut || 'all';
        syncQuickCategoryState();
        renderStoreList();
    });
});
menuSearchInput.addEventListener('input', event => {
    menuSearchKeyword = event.target.value || '';
    renderMenu();
});
storeDetailTabs.forEach(tab => {
    tab.addEventListener('click', () => showStoreTab(tab.dataset.storeTab));
});
closeReviewModal.addEventListener('click', closeReviewDialog);
submitReviewBtn.addEventListener('click', submitReviewHandler);
reviewModal.addEventListener('click', event => {
    if (event.target === reviewModal) {
        closeReviewDialog();
    }
});
reviewImage.addEventListener('change', async event => {
    const [file] = event.target.files || [];
    reviewImageData = file ? await readFileAsDataUrl(file) : null;
    reviewImagePreview.innerHTML = reviewImageData ? `<img src="${reviewImageData}" alt="评价预览" />` : '';
});
homeAddressBtn.addEventListener('click', () => switchPage('my'));
messageCenterBtn.addEventListener('click', () => switchPage('orders'));
profileCenterBtn.addEventListener('click', () => switchPage('my'));
floatingCartBtn.addEventListener('click', () => {
    if (selectedStore) {
        switchPage('store-detail');
        return;
    }
    switchPage('home');
});

window.selectStore = selectStore;
window.switchPage = switchPage;
window.addToCart = addToCart;
window.addComboToCart = addComboToCart;
window.removeFromCart = removeFromCart;
window.cancelOrder = cancelOrder;
window.editAddress = editAddress;
window.deleteAddress = deleteAddress;
window.toggleFavoriteStore = toggleFavoriteStore;
window.toggleFavoriteItem = toggleFavoriteItem;
window.showItemDetail = showItemDetail;
window.showFavoriteItem = showFavoriteItem;
window.reorderOrder = reorderOrder;
window.openReviewModal = openReviewModal;

window.addEventListener('load', () => {
    loadSelectedStore();
    loadPendingAiTarget();
    renderSelectedStoreState();
    syncQuickCategoryState();
    showStoreTab(currentStoreTab);
    showMySection('profile');
    checkLoginStatus();
    renderCart();
});

document.addEventListener('visibilitychange', () => {
    if (!document.hidden && sessionId && currentUser) {
        loadStores(true);
    }
});
