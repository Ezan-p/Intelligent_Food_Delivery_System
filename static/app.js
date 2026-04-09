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

// 用户和地址相关
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

// 页面和菜单
const pages = document.querySelectorAll('.page');
const menuItems = document.querySelectorAll('.menu-item');
const addressMenuBtn = document.getElementById('addressMenuBtn');

let menuData = [];
let categoryData = [];
let comboData = [];
let cart = [];
let currentCategory = 'all';
let currentUser = null;
let sessionId = null;

// 页面切换函数
function switchPage(pageName) {
    // 隐藏所有页面
    pages.forEach(page => page.classList.remove('active'));
    
    // 显示目标页面
    const targetPage = document.getElementById(`page-${pageName}`);
    if (targetPage) {
        targetPage.classList.add('active');
    }
    
    // 更新菜单项的 active 状态
    menuItems.forEach(item => {
        if (item.dataset.page === pageName) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });
}

function formatPrice(price) {
    return Number(price).toFixed(2);
}

function loadCategories() {
    fetch('/api/categories')
        .then(response => response.json())
        .then(data => {
            categoryData = data.categories;
            renderCategoryFilter();
        });
}

function renderCategoryFilter() {
    const filterButtons = categoryFilter.querySelectorAll('.filter-btn:not([data-category="all"])');
    filterButtons.forEach(btn => btn.remove());

    categoryData.forEach(cat => {
        const btn = document.createElement('button');
        btn.className = 'filter-btn';
        btn.dataset.category = cat.id.toString();
        btn.textContent = cat.name;
        btn.addEventListener('click', () => filterByCategory(cat.id.toString()));
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

function loadMenu() {
    fetch('/api/menu')
        .then(response => response.json())
        .then(data => {
            menuData = data.menu;
            renderMenu();
        });
}

function renderMenu() {
    let filteredMenu = menuData;
    if (currentCategory !== 'all') {
        filteredMenu = menuData.filter(item => item.category_id.toString() === currentCategory);
    }

    menuList.innerHTML = filteredMenu.length
        ? filteredMenu.map(item => {
            const category = categoryData.find(c => c.id === item.category_id);
            return `
        <div class="menu-card">
            ${item.image ? `<div class="card-image"><img src="${item.image}" alt="${item.name}" /></div>` : '<div class="card-image no-image">暂无图片</div>'}
            <h3>${item.name}</h3>
            <p>${item.description}</p>
            <div class="menu-card-footer">
                <span class="price">¥${formatPrice(item.price)}</span>
                <span class="category">${category ? category.name : '未分类'}</span>
                <button class="primary" onclick="addToCart(${item.id})">加入购物车</button>
            </div>
        </div>
    `}).join('')
        : '<p>当前分类暂无商品。</p>';
}

function loadCombos() {
    fetch('/api/combos')
        .then(response => response.json())
        .then(data => {
            comboData = data.combos;
            renderCombos();
        });
}

function renderCombos() {
    comboList.innerHTML = comboData.length
        ? comboData.map(combo => {
            const itemNames = combo.items.map(id => {
                const item = menuData.find(m => m.id === id);
                return item ? item.name : `商品${id}`;
            }).join(', ');
            const firstItem = menuData.find(m => m.id === combo.items[0]);
            return `
        <div class="combo-card">
            ${firstItem && firstItem.image ? `<div class="card-image"><img src="${firstItem.image}" alt="${combo.name}" /></div>` : '<div class="card-image no-image">暂无图片</div>'}
            <h3>${combo.name}</h3>
            <p>${combo.description}</p>
            <div class="combo-items">包含商品: ${itemNames}</div>
            <div class="combo-footer">
                <span class="price">¥${formatPrice(combo.price * combo.discount)}</span>
                <span class="original-price">原价 ¥${formatPrice(combo.price)}</span>
                <span class="discount">${(combo.discount * 100).toFixed(0)}%折扣</span>
                <button class="primary" onclick="addComboToCart(${combo.id})">加入购物车</button>
            </div>
        </div>
    `}).join('')
        : '<p>暂无推荐套餐。</p>';
}

function addComboToCart(comboId) {
    const combo = comboData.find(c => c.id === comboId);
    if (!combo) return;

    // 添加套餐到购物车
    const existing = cart.find(c => c.id === comboId && c.type === 'combo');
    if (existing) {
        existing.quantity += 1;
    } else {
        cart.push({
            id: combo.id,
            name: combo.name,
            price: combo.price * combo.discount,
            quantity: 1,
            type: 'combo',
            discount: combo.discount,
            originalPrice: combo.price
        });
    }
    renderCart();
}

function addToCart(id) {
    const item = menuData.find(m => m.id === id);
    if (!item) return;
    const existing = cart.find(c => c.id === id && c.type !== 'combo');
    if (existing) {
        existing.quantity += 1;
    } else {
        cart.push({ ...item, quantity: 1, type: 'item' });
    }
    renderCart();
}

function renderCart() {
    if (!cart.length) {
        cartItems.innerHTML = '<p>购物车为空。</p>';
        cartTotal.textContent = '0.00';
        return;
    }

    cartItems.innerHTML = cart.map(item => `
        <div class="cart-item">
            <strong>${item.name}</strong>
            ${item.type === 'combo' ? `<span class="combo-badge">套餐</span>` : ''}
            <span>数量: ${item.quantity} × ¥${formatPrice(item.price)}</span>
            <span>小计: ¥${formatPrice(item.price * item.quantity)}</span>
            <button class="secondary" onclick="removeFromCart(${item.id}, '${item.type}')">移除</button>
        </div>
    `).join('');

    const total = cart.reduce((sum, item) => sum + item.price * item.quantity, 0);
    cartTotal.textContent = formatPrice(total);
}

function removeFromCart(id, type) {
    cart = cart.filter(item => !(item.id === id && item.type === type));
    renderCart();
}

function submitOrderHandler() {
    const customer = customerName.value.trim();
    if (!customer) {
        alert('请输入姓名。');
        return;
    }
    if (!cart.length) {
        alert('购物车为空，请先添加商品。');
        return;
    }

    const items = cart.filter(item => item.type === 'item').map(item => ({ id: item.id, quantity: item.quantity }));
    const combo_id = cart.find(item => item.type === 'combo')?.id;

    fetch('/api/order', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ customer, items, combo_id })
    })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }
            alert('订单提交成功！');
            cart = [];
            renderCart();
            customerName.value = '';
            loadOrders();
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
        orderList.innerHTML = '<p>当前暂无订单。</p>';
        return;
    }

    orderList.innerHTML = orders.slice().reverse().map(order => `
        <div class="order-card">
            <h4>订单 #${order.id} - ${order.customer}</h4>
            <small>状态: ${order.status} · 下单时间: ${order.created_at}</small>
            <ul class="order-items">
                ${order.items.map(item => `<li>${item.name} × ${item.quantity} = ¥${formatPrice(item.subtotal)}</li>`).join('')}
            </ul>
            <div class="order-summary">总价：¥${formatPrice(order.total)}</div>
            <button class="secondary" onclick="cancelOrder(${order.id})">取消订单</button>
            ${order.status === '已接单' ? `<button class="primary" onclick="completeOrder(${order.id})">标记完成</button>` : ''}
        </div>
    `).join('');
}

function searchHistoryHandler() {
    const customer = historyCustomer.value.trim();
    if (!customer) {
        alert('请输入姓名查询历史订单。');
        return;
    }

    fetch(`/api/orders?customer=${encodeURIComponent(customer)}`)
        .then(response => response.json())
        .then(data => {
            renderHistory(data.orders);
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
            <small>状态: ${order.status} · 下单时间: ${order.created_at}</small>
            <ul class="order-items">
                ${order.items.map(item => `<li>${item.name} × ${item.quantity} = ¥${formatPrice(item.subtotal)}</li>`).join('')}
            </ul>
            <div class="order-summary">总价：¥${formatPrice(order.total)}</div>
        </div>
    `).join('');
}

function cancelOrder(orderId) {
    fetch(`/api/order/${orderId}/cancel`, { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }
            loadOrders();
        });
}

function completeOrder(orderId) {
    fetch(`/api/order/${orderId}/complete`, { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }
            loadOrders();
        });
}

// 用户相关函数
function checkLoginStatus() {
    sessionId = localStorage.getItem('sessionId');
    currentUser = localStorage.getItem('user');
    
    if (sessionId && currentUser) {
        currentUser = JSON.parse(currentUser);
        loginLink.style.display = 'none';
        userInfo.style.display = 'block';
        username.textContent = currentUser.username;
        addressMenuBtn.style.display = 'flex';
        loadAddresses();
    } else {
        loginLink.style.display = 'block';
        userInfo.style.display = 'none';
        addressMenuBtn.style.display = 'none';
    }
}

function logout() {
    if (sessionId) {
        fetch('/api/users/logout', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId })
        });
    }
    localStorage.removeItem('sessionId');
    localStorage.removeItem('user');
    currentUser = null;
    sessionId = null;
    checkLoginStatus();
}

// 地址管理函数
function loadAddresses() {
    if (!sessionId) return;

    fetch('/api/addresses', {
        headers: { 'X-Session-ID': sessionId }
    })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                console.log(data.error);
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
            </div>
        `).join('')
        : '<p>暂无地址，请添加收货地址</p>';
}

function addAddressHandler() {
    const name = addressName.value.trim();
    const address = addressDetail.value.trim();
    const phone = addressPhone.value.trim();
    const defaultAddr = isDefault.checked;

    if (!name || !address || !phone) {
        alert('请填写所有字段');
        return;
    }

    fetch('/api/addresses', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Session-ID': sessionId
        },
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
    const addr = currentUser.addresses.find(a => a.id === addressId);
    if (!addr) return;

    const newName = prompt('收货人名称:', addr.name);
    if (newName === null) return;

    const newAddress = prompt('详细地址:', addr.address);
    if (newAddress === null) return;

    const newPhone = prompt('电话号码:', addr.phone);
    if (newPhone === null) return;

    fetch(`/api/addresses/${addressId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
            'X-Session-ID': sessionId
        },
        body: JSON.stringify({
            name: newName,
            address: newAddress,
            phone: newPhone,
            is_default: addr.is_default
        })
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

    fetch(`/api/addresses/${addressId}`, {
        method: 'DELETE',
        headers: { 'X-Session-ID': sessionId }
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

submitOrder.addEventListener('click', submitOrderHandler);
searchHistory.addEventListener('click', searchHistoryHandler);
logoutBtn.addEventListener('click', logout);
addAddressBtn.addEventListener('click', addAddressHandler);

// 菜单项点击事件
menuItems.forEach(item => {
    item.addEventListener('click', () => {
        const pageName = item.dataset.page;
        switchPage(pageName);
    });
});

window.addToCart = addToCart;
window.addComboToCart = addComboToCart;
window.removeFromCart = removeFromCart;
window.cancelOrder = cancelOrder;
window.completeOrder = completeOrder;
window.editAddress = editAddress;
window.deleteAddress = deleteAddress;

window.addEventListener('load', () => {
    checkLoginStatus();
    loadCategories();
    loadMenu();
    loadCombos();
    loadOrders();
});
