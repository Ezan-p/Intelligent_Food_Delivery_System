const productList = document.getElementById('productList');
const merchantOrderList = document.getElementById('merchantOrderList');
const orderDetailContent = document.getElementById('orderDetailContent');
const orderStatusTabs = document.getElementById('orderStatusTabs');
const orderSearchInput = document.getElementById('orderSearchInput');

const itemName = document.getElementById('itemName');
const itemDescription = document.getElementById('itemDescription');
const itemPrice = document.getElementById('itemPrice');
const itemCategory = document.getElementById('itemCategory');
const itemStatus = document.getElementById('itemStatus');
const itemImage = document.getElementById('itemImage');
const imagePreview = document.getElementById('imagePreview');
const saveItem = document.getElementById('saveItem');
const resetItem = document.getElementById('resetItem');
const productSearchInput = document.getElementById('productSearchInput');
const productCategoryFilter = document.getElementById('productCategoryFilter');
const productStatusFilter = document.getElementById('productStatusFilter');
const openProductModalBtn = document.getElementById('openProductModalBtn');

const categoryName = document.getElementById('categoryName');
const categoryStatus = document.getElementById('categoryStatus');
const saveCategory = document.getElementById('saveCategory');
const resetCategory = document.getElementById('resetCategory');
const categoryList = document.getElementById('categoryList');
const categorySearchInput = document.getElementById('categorySearchInput');
const categoryStatusFilter = document.getElementById('categoryStatusFilter');
const openCategoryModalBtn = document.getElementById('openCategoryModalBtn');

const comboName = document.getElementById('comboName');
const comboDescription = document.getElementById('comboDescription');
const comboPrice = document.getElementById('comboPrice');
const comboDiscount = document.getElementById('comboDiscount');
const comboStatus = document.getElementById('comboStatus');
const comboItems = document.getElementById('comboItems');
const saveCombo = document.getElementById('saveCombo');
const resetCombo = document.getElementById('resetCombo');
const comboList = document.getElementById('comboList');
const comboSearchInput = document.getElementById('comboSearchInput');
const comboStatusFilter = document.getElementById('comboStatusFilter');
const openComboModalBtn = document.getElementById('openComboModalBtn');
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

const merchantEditorModal = document.getElementById('merchantEditorModal');
const closeMerchantEditorModal = document.getElementById('closeMerchantEditorModal');
const merchantEditorTitle = document.getElementById('merchantEditorTitle');
const merchantEditorSubtitle = document.getElementById('merchantEditorSubtitle');
const categoryEditorForm = document.getElementById('categoryEditorForm');
const productEditorForm = document.getElementById('productEditorForm');
const comboEditorForm = document.getElementById('comboEditorForm');

const STORAGE_PREFIX = 'merchant';
let menuData = [];
let categoryData = [];
let comboData = [];
let orderData = [];
let editingId = null;
let editingCategoryId = null;
let editingComboId = null;
let currentImageData = null;
let sessionId = null;
let currentUser = null;
let currentStore = null;
let draftStoreAvatar = null;
let draftStoreCover = null;
let currentOrderStatusFilter = 'all';
let currentOrderDetailId = null;

function authHeaders() {
    return sessionId ? { 'X-Session-ID': sessionId } : {};
}

function formatPrice(price) {
    return Number(price || 0).toFixed(2);
}

function getStatusLabel(status) {
    const labels = {
        active: '上架中',
        inactive: '已下架',
        '已接单': '待接单'
    };
    return labels[status] || status;
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

function openEditorModal(type) {
    merchantEditorModal.style.display = 'flex';
    categoryEditorForm.style.display = type === 'category' ? 'block' : 'none';
    productEditorForm.style.display = type === 'product' ? 'block' : 'none';
    comboEditorForm.style.display = type === 'combo' ? 'block' : 'none';

    const titleMap = {
        category: editingCategoryId ? '编辑分类' : '新增分类',
        product: editingId ? '编辑商品' : '新增商品',
        combo: editingComboId ? '编辑套餐' : '新增套餐'
    };
    merchantEditorTitle.textContent = titleMap[type];
    merchantEditorSubtitle.textContent = '在弹窗中完成新增与编辑。';
}

function closeEditorModal() {
    merchantEditorModal.style.display = 'none';
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
    if (redirect) window.location.href = '/login';
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
            dashboardStats.innerHTML = `
                <div class="stat-card"><h3>总订单数</h3><div class="stat-value">${data.total_orders}</div></div>
                <div class="stat-card"><h3>总收入</h3><div class="stat-value">¥${formatPrice(data.total_revenue)}</div></div>
                <div class="stat-card"><h3>待处理订单</h3><div class="stat-value">${data.pending_orders}</div></div>
                <div class="stat-card"><h3>已完成订单</h3><div class="stat-value">${data.completed_orders}</div></div>
                <div class="stat-card"><h3>已取消订单</h3><div class="stat-value">${data.cancelled_orders}</div></div>
                <div class="stat-card"><h3>今日订单</h3><div class="stat-value">${data.today_orders}</div></div>
                <div class="stat-card"><h3>今日收入</h3><div class="stat-value">¥${formatPrice(data.today_revenue)}</div></div>
                <div class="stat-card"><h3>商品数量</h3><div class="stat-value">${data.menu_count}</div></div>
                <div class="stat-card"><h3>套餐数量</h3><div class="stat-value">${data.combo_count}</div></div>`;
        });
}

function updateProductCategoryFilter() {
    productCategoryFilter.innerHTML = '<option value="all">全部分类</option>' + categoryData.map(cat => `<option value="${cat.id}">${cat.name}</option>`).join('');
}

function loadCategories() {
    fetch('/api/categories', { headers: authHeaders() })
        .then(response => response.json())
        .then(data => {
            categoryData = data.categories || [];
            renderCategories();
            updateCategorySelect();
            updateProductCategoryFilter();
        });
}

function renderCategories() {
    const keyword = (categorySearchInput.value || '').trim().toLowerCase();
    const status = categoryStatusFilter.value || 'all';
    const filtered = categoryData.filter(cat => {
        const hitKeyword = !keyword || (cat.name || '').toLowerCase().includes(keyword);
        const hitStatus = status === 'all' || (cat.status || 'active') === status;
        return hitKeyword && hitStatus;
    });

    categoryList.innerHTML = filtered.length ? filtered.map(cat => {
        const productCount = menuData.filter(item => item.category_id === cat.id).length;
        return `
            <tr>
                <td>${cat.id}</td>
                <td>${cat.name}</td>
                <td><span class="service-tag">${getStatusLabel(cat.status || 'active')}</span></td>
                <td>${productCount}</td>
                <td>
                    <div class="table-actions">
                        <button class="secondary" onclick="showCategoryDetail(${cat.id})">查看详情</button>
                        <button class="secondary" onclick="startEditCategory(${cat.id})">编辑</button>
                        <button class="secondary" onclick="toggleCategoryStatus(${cat.id})">${(cat.status || 'active') === 'active' ? '下架' : '上架'}</button>
                        <button class="secondary" onclick="deleteCategory(${cat.id})">删除</button>
                    </div>
                </td>
            </tr>`;
    }).join('') : '<tr><td colspan="5">当前没有符合条件的分类。</td></tr>';
}

function updateCategorySelect() {
    itemCategory.innerHTML = '<option value="">请选择分类</option>' + categoryData.filter(cat => (cat.status || 'active') === 'active').map(cat => `<option value="${cat.id}">${cat.name}</option>`).join('');
}

function startEditCategory(id) {
    const category = categoryData.find(item => item.id === id);
    if (!category) return;
    editingCategoryId = id;
    categoryName.value = category.name;
    categoryStatus.value = category.status || 'active';
    saveCategory.textContent = '更新分类';
    openEditorModal('category');
}

function resetCategoryForm() {
    editingCategoryId = null;
    categoryName.value = '';
    categoryStatus.value = 'active';
    saveCategory.textContent = '保存分类';
}

function showCategoryDetail(id) {
    startEditCategory(id);
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
        body: JSON.stringify({ name, status: categoryStatus.value })
    })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }
            resetCategoryForm();
            closeEditorModal();
            loadCategories();
        });
}

function toggleCategoryStatus(id) {
    const category = categoryData.find(item => item.id === id);
    if (!category) return;
    fetch(`/api/categories/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({ name: category.name, status: (category.status || 'active') === 'active' ? 'inactive' : 'active' })
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

function deleteCategory(id) {
    if (!requireMerchantSession()) return;
    if (!confirm('确定要删除该分类吗？')) return;
    fetch(`/api/categories/${id}`, { method: 'DELETE', headers: authHeaders() })
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
    const keyword = (productSearchInput.value || '').trim().toLowerCase();
    const categoryFilterValue = productCategoryFilter.value || 'all';
    const statusValue = productStatusFilter.value || 'all';
    const filtered = menuData.filter(item => {
        const category = categoryData.find(cat => cat.id === item.category_id);
        const haystack = [item.name, item.description, category ? category.name : ''].join(' ').toLowerCase();
        const hitKeyword = !keyword || haystack.includes(keyword);
        const hitCategory = categoryFilterValue === 'all' || String(item.category_id) === categoryFilterValue;
        const hitStatus = statusValue === 'all' || (item.status || 'active') === statusValue;
        return hitKeyword && hitCategory && hitStatus;
    });

    productList.innerHTML = filtered.length ? filtered.map(item => {
        const category = categoryData.find(cat => cat.id === item.category_id);
        return `
            <tr>
                <td>${item.id}</td>
                <td>
                    <div class="table-item-main">
                        ${item.image ? `<img src="${item.image}" alt="${item.name}" class="table-thumb" />` : '<div class="table-thumb table-thumb-empty">无图</div>'}
                        <div>
                            <strong>${item.name}</strong>
                            <small>${item.description || '暂无描述'}</small>
                        </div>
                    </div>
                </td>
                <td>${category ? category.name : '未分类'}</td>
                <td>¥${formatPrice(item.price)}</td>
                <td><span class="service-tag">${getStatusLabel(item.status || 'active')}</span></td>
                <td>
                    <div class="table-actions">
                        <button class="secondary" onclick="showProductDetail(${item.id})">查看详情</button>
                        <button class="secondary" onclick="startEdit(${item.id})">编辑</button>
                        <button class="secondary" onclick="toggleProductStatus(${item.id})">${(item.status || 'active') === 'active' ? '下架' : '上架'}</button>
                        <button class="secondary" onclick="deleteProduct(${item.id})">删除</button>
                    </div>
                </td>
            </tr>`;
    }).join('') : '<tr><td colspan="6">当前没有符合条件的商品。</td></tr>';
}

function showProductDetail(id) {
    startEdit(id);
}

function startEdit(id) {
    const item = menuData.find(menuItem => menuItem.id === id);
    if (!item) return;
    editingId = id;
    itemName.value = item.name;
    itemDescription.value = item.description;
    itemPrice.value = item.price;
    itemCategory.value = item.category_id;
    itemStatus.value = item.status || 'active';
    currentImageData = item.image || null;
    imagePreview.innerHTML = item.image ? `<img src="${item.image}" alt="${item.name}" class="preview-img" />` : '<p>暂无图片</p>';
    saveItem.textContent = '更新商品';
    openEditorModal('product');
}

function resetForm() {
    editingId = null;
    itemName.value = '';
    itemDescription.value = '';
    itemPrice.value = '';
    itemCategory.value = '';
    itemStatus.value = 'active';
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
            doSaveProduct({ name, description, price, category_id: parseInt(categoryId, 10), image: event.target.result, status: itemStatus.value });
        };
        reader.readAsDataURL(itemImage.files[0]);
        return;
    }

    doSaveProduct({ name, description, price, category_id: parseInt(categoryId, 10), image: currentImageData, status: itemStatus.value });
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
            closeEditorModal();
            loadMenu();
        });
}

function toggleProductStatus(id) {
    const item = menuData.find(menuItem => menuItem.id === id);
    if (!item) return;
    fetch(`/api/menu/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({
            name: item.name,
            description: item.description || '',
            price: item.price,
            category_id: item.category_id,
            image: item.image,
            status: (item.status || 'active') === 'active' ? 'inactive' : 'active'
        })
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

function deleteProduct(id) {
    if (!requireMerchantSession()) return;
    if (!confirm('确定要删除该商品吗？')) return;
    fetch(`/api/menu/${id}`, { method: 'DELETE', headers: authHeaders() })
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
    comboItems.innerHTML = menuData.filter(item => (item.status || 'active') === 'active').map(item => `<option value="${item.id}">${item.name}</option>`).join('');
}

function renderCombos() {
    const keyword = (comboSearchInput.value || '').trim().toLowerCase();
    const statusValue = comboStatusFilter.value || 'all';
    const filtered = comboData.filter(combo => {
        const haystack = [combo.name, combo.description].join(' ').toLowerCase();
        const hitKeyword = !keyword || haystack.includes(keyword);
        const hitStatus = statusValue === 'all' || (combo.status || 'active') === statusValue;
        return hitKeyword && hitStatus;
    });

    comboList.innerHTML = filtered.length ? filtered.map(combo => {
        const itemNames = combo.items.map(id => {
            const item = menuData.find(menuItem => menuItem.id === id);
            return item ? item.name : `商品${id}`;
        }).join('，');
        return `
            <tr>
                <td>${combo.id}</td>
                <td>
                    <div class="table-item-stack">
                        <strong>${combo.name}</strong>
                        <small>${combo.description || '暂无描述'}</small>
                    </div>
                </td>
                <td>${itemNames || '无'}</td>
                <td>¥${formatPrice(combo.price * combo.discount)}</td>
                <td><span class="service-tag">${getStatusLabel(combo.status || 'active')}</span></td>
                <td>
                    <div class="table-actions">
                        <button class="secondary" onclick="showComboDetail(${combo.id})">查看详情</button>
                        <button class="secondary" onclick="startEditCombo(${combo.id})">编辑</button>
                        <button class="secondary" onclick="toggleComboStatus(${combo.id})">${(combo.status || 'active') === 'active' ? '下架' : '上架'}</button>
                        <button class="secondary" onclick="deleteCombo(${combo.id})">删除</button>
                    </div>
                </td>
            </tr>`;
    }).join('') : '<tr><td colspan="6">当前没有符合条件的套餐。</td></tr>';
}

function showComboDetail(id) {
    startEditCombo(id);
}

function startEditCombo(id) {
    const combo = comboData.find(item => item.id === id);
    if (!combo) return;
    editingComboId = id;
    comboName.value = combo.name;
    comboDescription.value = combo.description;
    comboPrice.value = combo.price;
    comboDiscount.value = combo.discount;
    comboStatus.value = combo.status || 'active';
    Array.from(comboItems.options).forEach(option => {
        option.selected = combo.items.includes(parseInt(option.value, 10));
    });
    saveCombo.textContent = '更新套餐';
    openEditorModal('combo');
}

function resetComboForm() {
    editingComboId = null;
    comboName.value = '';
    comboDescription.value = '';
    comboPrice.value = '';
    comboDiscount.value = 1.0;
    comboStatus.value = 'active';
    Array.from(comboItems.options).forEach(option => { option.selected = false; });
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
        items: selectedItems,
        status: comboStatus.value
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
            closeEditorModal();
            loadCombos();
        });
}

function toggleComboStatus(id) {
    const combo = comboData.find(item => item.id === id);
    if (!combo) return;
    fetch(`/api/combos/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({
            name: combo.name,
            description: combo.description || '',
            price: combo.price,
            discount: combo.discount,
            items: combo.items,
            status: (combo.status || 'active') === 'active' ? 'inactive' : 'active'
        })
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

function deleteCombo(id) {
    if (!requireMerchantSession()) return;
    if (!confirm('确定要删除该套餐吗？')) return;
    fetch(`/api/combos/${id}`, { method: 'DELETE', headers: authHeaders() })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }
            loadCombos();
        });
}

function renderOrderDetail(order) {
    if (!order) {
        orderDetailContent.innerHTML = '<p>点击某个订单后，在这里查看详情。</p>';
        return;
    }
    const statusActions = {
        '已接单': ['制作中', '配送中', '已完成', '已取消'],
        '制作中': ['配送中', '已完成', '已取消'],
        '配送中': ['已完成'],
        '已完成': [],
        '已取消': []
    };
    orderDetailContent.innerHTML = `
        <div class="analysis-list-item"><strong>订单号</strong><span>#${order.id}</span></div>
        <div class="analysis-list-item"><strong>用户</strong><span>${order.customer}</span></div>
        <div class="analysis-list-item"><strong>状态</strong><span>${getStatusLabel(order.status)}</span></div>
        <div class="analysis-list-item"><strong>下单时间</strong><span>${order.created_at}</span></div>
        <div class="analysis-list-item"><strong>总金额</strong><span>¥${formatPrice(order.total)}</span></div>
        <div class="analysis-panel"><strong>商品明细</strong><ul class="order-items">${order.items.map(item => `<li>${item.name} × ${item.quantity} = ¥${formatPrice(item.subtotal)}</li>`).join('')}</ul></div>
        <div class="form-actions-row">
            ${statusActions[order.status].map(status => `<button class="secondary" onclick="updateOrderStatus(${order.id}, '${status}')">${getStatusLabel(status)}</button>`).join('')}
        </div>`;
}

function loadOrders() {
    if (!requireMerchantSession()) return;
    fetch('/api/orders', { headers: authHeaders() })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                merchantOrderList.innerHTML = `<tr><td colspan="6">${data.error}</td></tr>`;
                return;
            }
            orderData = data.orders || [];
            renderOrders();
        });
}

function renderOrders() {
    const keyword = (orderSearchInput.value || '').trim().toLowerCase();
    const filtered = orderData.filter(order => {
        const hitStatus = currentOrderStatusFilter === 'all' || order.status === currentOrderStatusFilter;
        const haystack = [`${order.id}`, order.customer, order.store_name || ''].join(' ').toLowerCase();
        const hitKeyword = !keyword || haystack.includes(keyword);
        return hitStatus && hitKeyword;
    });

    merchantOrderList.innerHTML = filtered.length ? filtered.slice().reverse().map(order => `
        <tr class="${currentOrderDetailId === order.id ? 'is-selected-row' : ''}">
            <td>#${order.id}</td>
            <td>${order.customer}</td>
            <td><span class="service-tag">${getStatusLabel(order.status)}</span></td>
            <td>¥${formatPrice(order.total)}</td>
            <td>${order.created_at}</td>
            <td>
                <div class="table-actions">
                    <button class="secondary" onclick="selectOrderDetail(${order.id})">查看详情</button>
                    ${order.status !== '已完成' && order.status !== '已取消' ? `<button class="secondary" onclick="updateOrderStatus(${order.id}, '${order.status === '已接单' ? '制作中' : order.status === '制作中' ? '配送中' : '已完成'}')">推进状态</button>` : ''}
                </div>
            </td>
        </tr>`).join('') : '<tr><td colspan="6">暂无符合条件的订单。</td></tr>';

    if (!currentOrderDetailId && filtered.length) {
        selectOrderDetail(filtered[filtered.length - 1].id, false);
    } else if (!filtered.some(order => order.id === currentOrderDetailId)) {
        currentOrderDetailId = null;
        renderOrderDetail(null);
    }
}

function selectOrderDetail(orderId, rerender = true) {
    currentOrderDetailId = orderId;
    const order = orderData.find(item => item.id === orderId) || null;
    renderOrderDetail(order);
    if (rerender) renderOrders();
}

function updateOrderStatus(orderId, status) {
    if (!requireMerchantSession()) return;
    fetch(`/api/order/${orderId}/status`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({ status })
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

function completeOrder(orderId) {
    updateOrderStatus(orderId, '已完成');
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
openCategoryModalBtn.addEventListener('click', () => { resetCategoryForm(); openEditorModal('category'); });
openProductModalBtn.addEventListener('click', () => { resetForm(); openEditorModal('product'); });
openComboModalBtn.addEventListener('click', () => { resetComboForm(); openEditorModal('combo'); });
closeMerchantEditorModal.addEventListener('click', closeEditorModal);
merchantEditorModal.addEventListener('click', event => {
    if (event.target === merchantEditorModal) closeEditorModal();
});
categorySearchInput.addEventListener('input', renderCategories);
categoryStatusFilter.addEventListener('change', renderCategories);
productSearchInput.addEventListener('input', renderProducts);
productCategoryFilter.addEventListener('change', renderProducts);
productStatusFilter.addEventListener('change', renderProducts);
comboSearchInput.addEventListener('input', renderCombos);
comboStatusFilter.addEventListener('change', renderCombos);
orderSearchInput.addEventListener('input', renderOrders);
orderStatusTabs.querySelectorAll('.status-tab').forEach(button => {
    button.addEventListener('click', () => {
        currentOrderStatusFilter = button.dataset.orderStatus || 'all';
        orderStatusTabs.querySelectorAll('.status-tab').forEach(item => item.classList.toggle('active', item === button));
        renderOrders();
    });
});

window.startEdit = startEdit;
window.deleteProduct = deleteProduct;
window.startEditCategory = startEditCategory;
window.deleteCategory = deleteCategory;
window.startEditCombo = startEditCombo;
window.deleteCombo = deleteCombo;
window.completeOrder = completeOrder;
window.showProductDetail = showProductDetail;
window.showCategoryDetail = showCategoryDetail;
window.showComboDetail = showComboDetail;
window.toggleProductStatus = toggleProductStatus;
window.toggleCategoryStatus = toggleCategoryStatus;
window.toggleComboStatus = toggleComboStatus;
window.selectOrderDetail = selectOrderDetail;
window.updateOrderStatus = updateOrderStatus;

window.addEventListener('load', () => {
    bindSidebarNavigation();
    showPage('dashboard');
    renderOrderDetail(null);
    checkLoginStatus();
});
