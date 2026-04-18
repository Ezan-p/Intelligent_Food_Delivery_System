const productList = document.getElementById('productList');
const merchantOrderList = document.getElementById('merchantOrderList');
const itemName = document.getElementById('itemName');
const itemDescription = document.getElementById('itemDescription');
const itemPrice = document.getElementById('itemPrice');
const itemCategory = document.getElementById('itemCategory');
const itemImage = document.getElementById('itemImage');
const imagePreview = document.getElementById('imagePreview');
const saveItem = document.getElementById('saveItem');
const resetItem = document.getElementById('resetItem');

const categoryName = document.getElementById('categoryName');
const saveCategory = document.getElementById('saveCategory');
const resetCategory = document.getElementById('resetCategory');
const categoryList = document.getElementById('categoryList');

const comboName = document.getElementById('comboName');
const comboDescription = document.getElementById('comboDescription');
const comboPrice = document.getElementById('comboPrice');
const comboDiscount = document.getElementById('comboDiscount');
const comboItems = document.getElementById('comboItems');
const saveCombo = document.getElementById('saveCombo');
const resetCombo = document.getElementById('resetCombo');
const comboList = document.getElementById('comboList');
const dashboardStats = document.getElementById('dashboardStats');

const merchantStoreName = document.getElementById('merchantStoreName');
const storePreviewCard = document.getElementById('storePreviewCard');
const storeName = document.getElementById('storeName');
const storeDescription = document.getElementById('storeDescription');
const storeBusinessStatus = document.getElementById('storeBusinessStatus');
const storeBusinessHours = document.getElementById('storeBusinessHours');
const storeRating = document.getElementById('storeRating');
const storeDeliveryFee = document.getElementById('storeDeliveryFee');
const storeMinOrderAmount = document.getElementById('storeMinOrderAmount');
const storeMonthlySales = document.getElementById('storeMonthlySales');
const storeStatus = document.getElementById('storeStatus');
const storeAnnouncement = document.getElementById('storeAnnouncement');
const storeAvatarFile = document.getElementById('storeAvatarFile');
const storeCoverFile = document.getElementById('storeCoverFile');
const storeAvatarPreview = document.getElementById('storeAvatarPreview');
const storeCoverPreview = document.getElementById('storeCoverPreview');
const saveStoreBtn = document.getElementById('saveStoreBtn');
const resetStoreBtn = document.getElementById('resetStoreBtn');

const merchantLoginLink = document.getElementById('merchantLoginLink');
const merchantUserInfo = document.getElementById('merchantUserInfo');
const merchantUsername = document.getElementById('merchantUsername');
const merchantLogoutBtn = document.getElementById('merchantLogoutBtn');

const STORAGE_PREFIX = 'merchant';
let menuData = [];
let categoryData = [];
let comboData = [];
let editingId = null;
let editingCategoryId = null;
let editingComboId = null;
let currentImageData = null;
let sessionId = null;
let currentUser = null;
let currentStore = null;
let draftStoreAvatar = null;
let draftStoreCover = null;

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

function requireMerchantSession() {
    if (!sessionId) {
        alert('请先登录商家账户。');
        window.location.href = '/login';
        return false;
    }
    return true;
}

function renderAuthState() {
    if (sessionId && currentUser) {
        merchantLoginLink.style.display = 'none';
        merchantUserInfo.style.display = 'block';
        merchantUsername.textContent = currentUser.username;
    } else {
        merchantLoginLink.style.display = 'block';
        merchantUserInfo.style.display = 'none';
    }
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

function renderStorePreview() {
    if (!currentStore) {
        storePreviewCard.innerHTML = '<p>当前没有可管理的店铺。</p>';
        merchantStoreName.textContent = '未配置店铺';
        return;
    }

    merchantStoreName.textContent = currentStore.name || '未命名店铺';
    storePreviewCard.innerHTML = `
        <div class="store-cover">
            <img src="${currentStore.cover_image_url}" alt="${currentStore.name} 封面" />
        </div>
        <div class="store-card-header">
            <img class="store-avatar" src="${currentStore.avatar_url}" alt="${currentStore.name} 头像" />
            <div>
                <span class="service-tag">${currentStore.business_status || '营业中'}</span>
                <h3>${currentStore.name}</h3>
            </div>
        </div>
        <p>${currentStore.description || '暂无店铺介绍。'}</p>
        <div class="store-meta-grid">
            <span>营业时间：${currentStore.business_hours || '09:00-22:00'}</span>
            <span>评分：${Number(currentStore.rating || 0).toFixed(1)}</span>
            <span>月售：${currentStore.monthly_sales || 0}</span>
            <span>配送费：¥${formatPrice(currentStore.delivery_fee)}</span>
            <span>起送价：¥${formatPrice(currentStore.min_order_amount)}</span>
            <span>展示状态：${currentStore.status === 'active' ? '上架展示' : '下架隐藏'}</span>
        </div>
        <div class="store-announcement">${currentStore.announcement || '暂无公告'}</div>`;

    storeAvatarPreview.innerHTML = `<img src="${currentStore.avatar_url}" alt="头像预览" class="preview-img" />`;
    storeCoverPreview.innerHTML = `<img src="${currentStore.cover_image_url}" alt="封面预览" class="preview-img" />`;
}

function fillStoreForm() {
    if (!currentStore) return;
    storeName.value = currentStore.name || '';
    storeDescription.value = currentStore.description || '';
    storeBusinessStatus.value = currentStore.business_status || '营业中';
    storeBusinessHours.value = currentStore.business_hours || '09:00-22:00';
    storeRating.value = Number(currentStore.rating || 0).toFixed(1);
    storeDeliveryFee.value = formatPrice(currentStore.delivery_fee || 0);
    storeMinOrderAmount.value = formatPrice(currentStore.min_order_amount || 0);
    storeMonthlySales.value = `${currentStore.monthly_sales || 0}`;
    storeStatus.value = currentStore.status || 'active';
    storeAnnouncement.value = currentStore.announcement || '';
    storeAvatarFile.value = '';
    storeCoverFile.value = '';
    draftStoreAvatar = currentStore.avatar_url;
    draftStoreCover = currentStore.cover_image_url;
    renderStorePreview();
}

function syncDraftStorePreview() {
    if (!currentStore) return;
    const name = storeName.value.trim() || currentStore.name || '未命名店铺';
    const description = storeDescription.value.trim() || '暂无店铺介绍。';
    const businessStatus = storeBusinessStatus.value || '营业中';
    const businessHours = storeBusinessHours.value.trim() || '09:00-22:00';
    const rating = Number(storeRating.value || currentStore.rating || 0).toFixed(1);
    const deliveryFee = formatPrice(storeDeliveryFee.value || currentStore.delivery_fee || 0);
    const minOrderAmount = formatPrice(storeMinOrderAmount.value || currentStore.min_order_amount || 0);
    const announcement = storeAnnouncement.value.trim() || '暂无公告';
    const statusText = (storeStatus.value || currentStore.status) === 'active' ? '上架展示' : '下架隐藏';

    merchantStoreName.textContent = name;
    storePreviewCard.innerHTML = `
        <div class="store-cover">
            <img src="${draftStoreCover || currentStore.cover_image_url}" alt="${name} 封面" />
        </div>
        <div class="store-card-header">
            <img class="store-avatar" src="${draftStoreAvatar || currentStore.avatar_url}" alt="${name} 头像" />
            <div>
                <span class="service-tag">${businessStatus}</span>
                <h3>${name}</h3>
            </div>
        </div>
        <p>${description}</p>
        <div class="store-meta-grid">
            <span>营业时间：${businessHours}</span>
            <span>评分：${rating}</span>
            <span>月售：${currentStore.monthly_sales || 0}</span>
            <span>配送费：¥${deliveryFee}</span>
            <span>起送价：¥${minOrderAmount}</span>
            <span>展示状态：${statusText}</span>
        </div>
        <div class="store-announcement">${announcement}</div>`;

    storeAvatarPreview.innerHTML = `<img src="${draftStoreAvatar || currentStore.avatar_url}" alt="头像预览" class="preview-img" />`;
    storeCoverPreview.innerHTML = `<img src="${draftStoreCover || currentStore.cover_image_url}" alt="封面预览" class="preview-img" />`;
}

function loadStore() {
    if (!requireMerchantSession()) return Promise.resolve();
    return fetch('/api/stores', { headers: authHeaders() })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                storePreviewCard.innerHTML = `<p>${data.error}</p>`;
                return;
            }
            currentStore = (data.stores || [])[0] || null;
            fillStoreForm();
        });
}

async function saveStore() {
    if (!requireMerchantSession() || !currentStore) return;

    const avatarData = storeAvatarFile.files[0] ? await readFileAsDataUrl(storeAvatarFile.files[0]) : draftStoreAvatar;
    const coverData = storeCoverFile.files[0] ? await readFileAsDataUrl(storeCoverFile.files[0]) : draftStoreCover;

    const payload = {
        name: storeName.value.trim(),
        description: storeDescription.value.trim(),
        avatar_url: avatarData,
        cover_image_url: coverData,
        business_status: storeBusinessStatus.value,
        business_hours: storeBusinessHours.value.trim(),
        rating: parseFloat(storeRating.value || currentStore.rating || 0),
        delivery_fee: parseFloat(storeDeliveryFee.value || currentStore.delivery_fee || 0),
        min_order_amount: parseFloat(storeMinOrderAmount.value || currentStore.min_order_amount || 0),
        announcement: storeAnnouncement.value.trim(),
        status: storeStatus.value
    };

    fetch(`/api/stores/${currentStore.id}`, {
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
            currentStore = data.store;
            draftStoreAvatar = currentStore.avatar_url;
            draftStoreCover = currentStore.cover_image_url;
            fillStoreForm();
            alert('店铺信息已更新。');
        });
}

function checkLoginStatus() {
    sessionId = localStorage.getItem(`${STORAGE_PREFIX}:sessionId`);
    const storedUser = localStorage.getItem(`${STORAGE_PREFIX}:user`);
    currentUser = storedUser ? JSON.parse(storedUser) : null;
    renderAuthState();

    if (!sessionId) {
        dashboardStats.innerHTML = '<p>登录商家账户后可管理店铺、商品、套餐和订单。</p>';
        storePreviewCard.innerHTML = '<p>登录后可编辑店铺卡片信息。</p>';
        return;
    }

    fetch('/api/users/session', { headers: authHeaders() })
        .then(response => response.json())
        .then(data => {
            if (data.error || !['merchant', 'admin'].includes(data.user.role)) {
                logout(false);
                return;
            }
            currentUser = data.user;
            localStorage.setItem(`${STORAGE_PREFIX}:user`, JSON.stringify(currentUser));
            renderAuthState();
            loadDashboard();
            loadStore();
            loadCategories();
            loadMenu();
            loadCombos();
            loadOrders();
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
    sessionId = null;
    currentUser = null;
    currentStore = null;
    renderAuthState();
    if (redirect) {
        window.location.href = '/login';
    }
}

function loadDashboard() {
    if (!requireMerchantSession()) return;
    fetch('/api/dashboard', { headers: authHeaders() })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                dashboardStats.innerHTML = `<p>${data.error}</p>`;
                return;
            }
            renderDashboard(data);
        });
}

function renderDashboard(stats) {
    dashboardStats.innerHTML = `
        <div class="stat-card"><h3>总订单数</h3><div class="stat-value">${stats.total_orders}</div></div>
        <div class="stat-card"><h3>总收入</h3><div class="stat-value">¥${formatPrice(stats.total_revenue)}</div></div>
        <div class="stat-card"><h3>待处理订单</h3><div class="stat-value">${stats.pending_orders}</div></div>
        <div class="stat-card"><h3>已完成订单</h3><div class="stat-value">${stats.completed_orders}</div></div>
        <div class="stat-card"><h3>已取消订单</h3><div class="stat-value">${stats.cancelled_orders}</div></div>
        <div class="stat-card"><h3>今日订单</h3><div class="stat-value">${stats.today_orders}</div></div>
        <div class="stat-card"><h3>今日收入</h3><div class="stat-value">¥${formatPrice(stats.today_revenue)}</div></div>
        <div class="stat-card"><h3>商品数量</h3><div class="stat-value">${stats.menu_count}</div></div>
        <div class="stat-card"><h3>套餐数量</h3><div class="stat-value">${stats.combo_count}</div></div>`;
}

function loadCategories() {
    fetch('/api/categories', { headers: authHeaders() })
        .then(response => response.json())
        .then(data => {
            categoryData = data.categories || [];
            renderCategories();
            updateCategorySelect();
        });
}

function renderCategories() {
    categoryList.innerHTML = categoryData.length
        ? categoryData.map(cat => `
        <div class="category-item">
            <span>${cat.name}</span>
            <div class="category-actions">
                <button class="secondary" onclick="startEditCategory(${cat.id})">编辑</button>
                <button class="secondary" onclick="deleteCategory(${cat.id})">删除</button>
            </div>
        </div>`).join('')
        : '<p>当前没有分类。</p>';
}

function updateCategorySelect() {
    itemCategory.innerHTML = '<option value="">请选择分类</option>' + categoryData.map(cat => `<option value="${cat.id}">${cat.name}</option>`).join('');
}

function startEditCategory(id) {
    const category = categoryData.find(item => item.id === id);
    if (!category) return;
    editingCategoryId = id;
    categoryName.value = category.name;
    saveCategory.textContent = '更新分类';
    showPage('categories');
}

function resetCategoryForm() {
    editingCategoryId = null;
    categoryName.value = '';
    saveCategory.textContent = '保存分类';
}

function saveCategoryHandler() {
    if (!requireMerchantSession()) return;
    const name = categoryName.value.trim();
    if (!name) {
        alert('请输入分类名称。');
        return;
    }

    const url = editingCategoryId ? `/api/categories/${editingCategoryId}` : '/api/categories';
    const method = editingCategoryId ? 'PUT' : 'POST';

    fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({ name })
    })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }
            resetCategoryForm();
            loadCategories();
        });
}

function deleteCategory(id) {
    if (!requireMerchantSession()) return;
    if (!confirm('确定要删除该分类吗？')) return;

    fetch(`/api/categories/${id}`, {
        method: 'DELETE',
        headers: authHeaders()
    })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }
            loadCategories();
        });
}

function loadMenu() {
    fetch('/api/menu', { headers: authHeaders() })
        .then(response => response.json())
        .then(data => {
            menuData = data.menu || [];
            renderProducts();
            updateComboItemsSelect();
        });
}

function renderProducts() {
    productList.innerHTML = menuData.length
        ? menuData.map(item => {
            const category = categoryData.find(cat => cat.id === item.category_id);
            return `
        <div class="menu-card">
            ${item.image ? `<div class="card-image"><img src="${item.image}" alt="${item.name}" /></div>` : '<div class="card-image no-image">暂无图片</div>'}
            <h3>${item.name}</h3>
            <p>${item.description || '暂无描述'}</p>
            <div class="menu-card-footer">
                <span class="price">¥${formatPrice(item.price)}</span>
                <span class="category">${category ? category.name : '未分类'}</span>
                <div class="card-actions">
                    <button class="secondary" onclick="startEdit(${item.id})">编辑</button>
                    <button class="secondary" onclick="deleteProduct(${item.id})">删除</button>
                </div>
            </div>
        </div>`;
        }).join('')
        : '<p>当前没有商品，请添加新商品。</p>';
}

function startEdit(id) {
    const item = menuData.find(menuItem => menuItem.id === id);
    if (!item) return;
    editingId = id;
    itemName.value = item.name;
    itemDescription.value = item.description;
    itemPrice.value = item.price;
    itemCategory.value = item.category_id;
    currentImageData = item.image || null;
    imagePreview.innerHTML = item.image ? `<img src="${item.image}" alt="${item.name}" class="preview-img" />` : '<p>暂无图片</p>';
    saveItem.textContent = '更新商品';
    showPage('products');
}

function resetForm() {
    editingId = null;
    itemName.value = '';
    itemDescription.value = '';
    itemPrice.value = '';
    itemCategory.value = '';
    itemImage.value = '';
    imagePreview.innerHTML = '';
    currentImageData = null;
    saveItem.textContent = '保存商品';
}

function saveProduct() {
    if (!requireMerchantSession()) return;
    const name = itemName.value.trim();
    const description = itemDescription.value.trim();
    const price = itemPrice.value;
    const categoryId = itemCategory.value;

    if (!name || !price || !categoryId) {
        alert('请完整填写商品信息。');
        return;
    }

    if (itemImage.files && itemImage.files[0]) {
        const reader = new FileReader();
        reader.onload = event => {
            doSaveProduct({ name, description, price, category_id: parseInt(categoryId, 10), image: event.target.result });
        };
        reader.readAsDataURL(itemImage.files[0]);
        return;
    }

    doSaveProduct({ name, description, price, category_id: parseInt(categoryId, 10), image: currentImageData });
}

function doSaveProduct(payload) {
    const url = editingId ? `/api/menu/${editingId}` : '/api/menu';
    const method = editingId ? 'PUT' : 'POST';

    fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify(payload)
    })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }
            resetForm();
            loadMenu();
        });
}

function deleteProduct(id) {
    if (!requireMerchantSession()) return;
    if (!confirm('确定要删除该商品吗？')) return;

    fetch(`/api/menu/${id}`, {
        method: 'DELETE',
        headers: authHeaders()
    })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }
            loadMenu();
        });
}

function loadCombos() {
    fetch('/api/combos', { headers: authHeaders() })
        .then(response => response.json())
        .then(data => {
            comboData = data.combos || [];
            renderCombos();
        });
}

function updateComboItemsSelect() {
    comboItems.innerHTML = menuData.map(item => `<option value="${item.id}">${item.name}</option>`).join('');
}

function renderCombos() {
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
                <div class="card-actions">
                    <button class="secondary" onclick="startEditCombo(${combo.id})">编辑</button>
                    <button class="secondary" onclick="deleteCombo(${combo.id})">删除</button>
                </div>
            </div>
        </div>`;
        }).join('')
        : '<p>当前没有套餐。</p>';
}

function startEditCombo(id) {
    const combo = comboData.find(item => item.id === id);
    if (!combo) return;
    editingComboId = id;
    comboName.value = combo.name;
    comboDescription.value = combo.description;
    comboPrice.value = combo.price;
    comboDiscount.value = combo.discount;
    Array.from(comboItems.options).forEach(option => {
        option.selected = combo.items.includes(parseInt(option.value, 10));
    });
    saveCombo.textContent = '更新套餐';
    showPage('combos');
}

function resetComboForm() {
    editingComboId = null;
    comboName.value = '';
    comboDescription.value = '';
    comboPrice.value = '';
    comboDiscount.value = 1.0;
    Array.from(comboItems.options).forEach(option => {
        option.selected = false;
    });
    saveCombo.textContent = '保存套餐';
}

function saveComboHandler() {
    if (!requireMerchantSession()) return;
    const name = comboName.value.trim();
    const description = comboDescription.value.trim();
    const price = comboPrice.value;
    const discount = comboDiscount.value;
    const selectedItems = Array.from(comboItems.selectedOptions).map(option => parseInt(option.value, 10));

    if (!name || !price || !selectedItems.length) {
        alert('请完整填写套餐信息。');
        return;
    }

    const payload = {
        name,
        description,
        price: parseFloat(price),
        discount: parseFloat(discount),
        items: selectedItems
    };
    const url = editingComboId ? `/api/combos/${editingComboId}` : '/api/combos';
    const method = editingComboId ? 'PUT' : 'POST';

    fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify(payload)
    })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }
            resetComboForm();
            loadCombos();
        });
}

function deleteCombo(id) {
    if (!requireMerchantSession()) return;
    if (!confirm('确定要删除该套餐吗？')) return;

    fetch(`/api/combos/${id}`, {
        method: 'DELETE',
        headers: authHeaders()
    })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }
            loadCombos();
        });
}

function loadOrders() {
    if (!requireMerchantSession()) return;
    fetch('/api/orders', { headers: authHeaders() })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                merchantOrderList.innerHTML = `<p>${data.error}</p>`;
                return;
            }
            renderOrders(data.orders || []);
        });
}

function renderOrders(orders) {
    if (!orders.length) {
        merchantOrderList.innerHTML = '<p>暂无订单。</p>';
        return;
    }

    merchantOrderList.innerHTML = orders.slice().reverse().map(order => `
        <div class="order-card">
            <h4>订单 #${order.id} - ${order.customer}</h4>
            <small>状态: ${order.status} · 下单时间: ${order.created_at}</small>
            <ul class="order-items">
                ${order.items.map(item => `<li>${item.name} × ${item.quantity} = ¥${formatPrice(item.subtotal)}</li>`).join('')}
            </ul>
            <div class="order-summary">总价：¥${formatPrice(order.total)}</div>
            ${order.status === '已接单' ? `<button class="primary" onclick="completeOrder(${order.id})">标记完成</button>` : ''}
        </div>`).join('');
}

function completeOrder(orderId) {
    if (!requireMerchantSession()) return;
    fetch(`/api/order/${orderId}/complete`, {
        method: 'POST',
        headers: authHeaders()
    })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }
            loadDashboard();
            loadOrders();
            loadStore();
        });
}

itemImage.addEventListener('change', event => {
    if (event.target.files && event.target.files[0]) {
        const reader = new FileReader();
        reader.onload = e => {
            imagePreview.innerHTML = `<img src="${e.target.result}" alt="preview" class="preview-img" />`;
            currentImageData = e.target.result;
        };
        reader.readAsDataURL(event.target.files[0]);
    }
});

storeAvatarFile.addEventListener('change', event => {
    const file = event.target.files && event.target.files[0];
    if (!file) return;
    readFileAsDataUrl(file).then(result => {
        draftStoreAvatar = result;
        syncDraftStorePreview();
    });
});

storeCoverFile.addEventListener('change', event => {
    const file = event.target.files && event.target.files[0];
    if (!file) return;
    readFileAsDataUrl(file).then(result => {
        draftStoreCover = result;
        syncDraftStorePreview();
    });
});

[storeName, storeDescription, storeBusinessStatus, storeBusinessHours, storeRating, storeDeliveryFee, storeMinOrderAmount, storeStatus, storeAnnouncement]
    .forEach(element => element.addEventListener('input', syncDraftStorePreview));

saveItem.addEventListener('click', saveProduct);
resetItem.addEventListener('click', resetForm);
saveCategory.addEventListener('click', saveCategoryHandler);
resetCategory.addEventListener('click', resetCategoryForm);
saveCombo.addEventListener('click', saveComboHandler);
resetCombo.addEventListener('click', resetComboForm);
saveStoreBtn.addEventListener('click', saveStore);
resetStoreBtn.addEventListener('click', fillStoreForm);
merchantLogoutBtn.addEventListener('click', () => logout());

window.startEdit = startEdit;
window.deleteProduct = deleteProduct;
window.startEditCategory = startEditCategory;
window.deleteCategory = deleteCategory;
window.startEditCombo = startEditCombo;
window.deleteCombo = deleteCombo;
window.completeOrder = completeOrder;

window.addEventListener('load', () => {
    bindSidebarNavigation();
    showPage('dashboard');
    checkLoginStatus();
});
