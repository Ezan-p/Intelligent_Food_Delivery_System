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

// 分类管理元素
const categoryName = document.getElementById('categoryName');
const saveCategory = document.getElementById('saveCategory');
const resetCategory = document.getElementById('resetCategory');
const categoryList = document.getElementById('categoryList');

// 套餐管理元素
const comboName = document.getElementById('comboName');
const comboDescription = document.getElementById('comboDescription');
const comboPrice = document.getElementById('comboPrice');
const comboDiscount = document.getElementById('comboDiscount');
const comboItems = document.getElementById('comboItems');
const saveCombo = document.getElementById('saveCombo');
const resetCombo = document.getElementById('resetCombo');
const comboList = document.getElementById('comboList');

// 工作台元素
const dashboardStats = document.getElementById('dashboardStats');

let menuData = [];
let categoryData = [];
let comboData = [];
let editingId = null;
let editingCategoryId = null;
let editingComboId = null;
let currentImageData = null;

function formatPrice(price) {
    return Number(price).toFixed(2);
}

function loadDashboard() {
    fetch('/api/dashboard')
        .then(response => response.json())
        .then(data => {
            renderDashboard(data);
        });
}

function renderDashboard(stats) {
    dashboardStats.innerHTML = `
        <div class="stat-card">
            <h3>总订单数</h3>
            <div class="stat-value">${stats.total_orders}</div>
        </div>
        <div class="stat-card">
            <h3>总收入</h3>
            <div class="stat-value">¥${formatPrice(stats.total_revenue)}</div>
        </div>
        <div class="stat-card">
            <h3>待处理订单</h3>
            <div class="stat-value">${stats.pending_orders}</div>
        </div>
        <div class="stat-card">
            <h3>已完成订单</h3>
            <div class="stat-value">${stats.completed_orders}</div>
        </div>
        <div class="stat-card">
            <h3>今日订单</h3>
            <div class="stat-value">${stats.today_orders}</div>
        </div>
        <div class="stat-card">
            <h3>今日收入</h3>
            <div class="stat-value">¥${formatPrice(stats.today_revenue)}</div>
        </div>
        <div class="stat-card">
            <h3>商品数量</h3>
            <div class="stat-value">${stats.menu_count}</div>
        </div>
        <div class="stat-card">
            <h3>套餐数量</h3>
            <div class="stat-value">${stats.combo_count}</div>
        </div>
    `;
}

function loadCategories() {
    fetch('/api/categories')
        .then(response => response.json())
        .then(data => {
            categoryData = data.categories;
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
        </div>
    `).join('')
        : '<p>当前没有分类。</p>';
}

function updateCategorySelect() {
    itemCategory.innerHTML = '<option value="">请选择分类</option>' +
        categoryData.map(cat => `<option value="${cat.id}">${cat.name}</option>`).join('');
}

function startEditCategory(id) {
    const category = categoryData.find(c => c.id === id);
    if (!category) return;
    editingCategoryId = id;
    categoryName.value = category.name;
    saveCategory.textContent = '更新分类';
}

function resetCategoryForm() {
    editingCategoryId = null;
    categoryName.value = '';
    saveCategory.textContent = '保存分类';
}

function saveCategoryHandler() {
    const name = categoryName.value.trim();
    if (!name) {
        alert('请输入分类名称。');
        return;
    }

    const payload = { name };
    const url = editingCategoryId ? `/api/categories/${editingCategoryId}` : '/api/categories';
    const method = editingCategoryId ? 'PUT' : 'POST';

    fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
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
    if (!confirm('确定要删除该分类吗？')) {
        return;
    }

    fetch(`/api/categories/${id}`, { method: 'DELETE' })
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
    fetch('/api/menu')
        .then(response => response.json())
        .then(data => {
            menuData = data.menu;
            renderProducts();
            updateComboItemsSelect();
        });
}

function renderProducts() {
    productList.innerHTML = menuData.length
        ? menuData.map(item => {
            const category = categoryData.find(c => c.id === item.category_id);
            return `
        <div class="menu-card">
            ${item.image ? `<div class="card-image"><img src="${item.image}" alt="${item.name}" /></div>` : '<div class="card-image no-image">暂无图片</div>'}
            <h3>${item.name}</h3>
            <p>${item.description}</p>
            <div class="menu-card-footer">
                <span class="price">¥${formatPrice(item.price)}</span>
                <span class="category">${category ? category.name : '未分类'}</span>
                <div class="card-actions">
                    <button class="secondary" onclick="startEdit(${item.id})">编辑</button>
                    <button class="secondary" onclick="deleteProduct(${item.id})">删除</button>
                </div>
            </div>
        </div>
    `}).join('')
        : '<p>当前没有商品，请添加新商品。</p>';
}

function startEdit(id) {
    const item = menuData.find(m => m.id === id);
    if (!item) return;
    editingId = id;
    itemName.value = item.name;
    itemDescription.value = item.description;
    itemPrice.value = item.price;
    itemCategory.value = item.category_id;
    currentImageData = item.image;
    if (item.image) {
        imagePreview.innerHTML = `<img src="${item.image}" alt="${item.name}" class="preview-img" />`;
    } else {
        imagePreview.innerHTML = '<p>暂无图片</p>';
    }
    saveItem.textContent = '更新商品';
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
    const name = itemName.value.trim();
    const description = itemDescription.value.trim();
    const price = itemPrice.value;
    const categoryId = itemCategory.value;

    if (!name) {
        alert('请输入商品名称。');
        return;
    }
    if (!price) {
        alert('请输入商品价格。');
        return;
    }
    if (!categoryId) {
        alert('请选择商品分类。');
        return;
    }

    // 处理文件上传
    if (itemImage.files && itemImage.files[0]) {
        const file = itemImage.files[0];
        const reader = new FileReader();
        reader.onload = (e) => {
            doSaveProduct({ name, description, price, category_id: parseInt(categoryId), image: e.target.result });
        };
        reader.readAsDataURL(file);
    } else {
        doSaveProduct({ name, description, price, category_id: parseInt(categoryId), image: currentImageData });
    }
}

function doSaveProduct(payload) {
    const url = editingId ? `/api/menu/${editingId}` : '/api/menu';
    const method = editingId ? 'PUT' : 'POST';

    fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
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
    if (!confirm('确定要删除该商品吗？')) {
        return;
    }

    fetch(`/api/menu/${id}`, { method: 'DELETE' })
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
    fetch('/api/combos')
        .then(response => response.json())
        .then(data => {
            comboData = data.combos;
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
                const item = menuData.find(m => m.id === id);
                return item ? item.name : `商品${id}`;
            }).join(', ');
            return `
        <div class="combo-card">
            <h3>${combo.name}</h3>
            <p>${combo.description}</p>
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
        </div>
    `}).join('')
        : '<p>当前没有套餐。</p>';
}

function startEditCombo(id) {
    const combo = comboData.find(c => c.id === id);
    if (!combo) return;
    editingComboId = id;
    comboName.value = combo.name;
    comboDescription.value = combo.description;
    comboPrice.value = combo.price;
    comboDiscount.value = combo.discount;

    // 选中套餐商品
    Array.from(comboItems.options).forEach(option => {
        option.selected = combo.items.includes(parseInt(option.value));
    });

    saveCombo.textContent = '更新套餐';
}

function resetComboForm() {
    editingComboId = null;
    comboName.value = '';
    comboDescription.value = '';
    comboPrice.value = '';
    comboDiscount.value = 1.0;
    Array.from(comboItems.options).forEach(option => option.selected = false);
    saveCombo.textContent = '保存套餐';
}

function saveComboHandler() {
    const name = comboName.value.trim();
    const description = comboDescription.value.trim();
    const price = comboPrice.value;
    const discount = comboDiscount.value;
    const selectedItems = Array.from(comboItems.selectedOptions).map(option => parseInt(option.value));

    if (!name) {
        alert('请输入套餐名称。');
        return;
    }
    if (!price) {
        alert('请输入套餐价格。');
        return;
    }
    if (!selectedItems.length) {
        alert('请选择套餐商品。');
        return;
    }

    const payload = { name, description, price: parseFloat(price), discount: parseFloat(discount), items: selectedItems };
    const url = editingComboId ? `/api/combos/${editingComboId}` : '/api/combos';
    const method = editingComboId ? 'PUT' : 'POST';

    fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
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
    if (!confirm('确定要删除该套餐吗？')) {
        return;
    }

    fetch(`/api/combos/${id}`, { method: 'DELETE' })
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
    fetch('/api/orders')
        .then(response => response.json())
        .then(data => {
            renderOrders(data.orders);
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
        </div>
    `).join('');
}

// 事件绑定
itemImage.addEventListener('change', (e) => {
    if (e.target.files && e.target.files[0]) {
        const file = e.target.files[0];
        const reader = new FileReader();
        reader.onload = (event) => {
            imagePreview.innerHTML = `<img src="${event.target.result}" alt="preview" class="preview-img" />`;
            currentImageData = event.target.result;
        };
        reader.readAsDataURL(file);
    }
});

saveItem.addEventListener('click', saveProduct);
resetItem.addEventListener('click', resetForm);
saveCategory.addEventListener('click', saveCategoryHandler);
resetCategory.addEventListener('click', resetCategoryForm);
saveCombo.addEventListener('click', saveComboHandler);
resetCombo.addEventListener('click', resetComboForm);

// 全局函数
window.startEdit = startEdit;
window.deleteProduct = deleteProduct;
window.startEditCategory = startEditCategory;
window.deleteCategory = deleteCategory;
window.startEditCombo = startEditCombo;
window.deleteCombo = deleteCombo;

window.addEventListener('load', () => {
    loadDashboard();
    loadCategories();
    loadMenu();
    loadCombos();
    loadOrders();
});

