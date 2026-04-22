const generateRecommendationBtn = document.getElementById('generateRecommendation');
const generateFreestyleRecommendationBtn = document.getElementById('generateFreestyleRecommendation');
const peopleCountInput = document.getElementById('peopleCount');
const budgetInput = document.getElementById('budget');
const preferenceTagButtons = document.querySelectorAll('.smart-pref-tag');
const selectedPreferenceSummary = document.getElementById('selectedPreferenceSummary');
const otherRequirementsInput = document.getElementById('otherRequirements');
const otherRequirementHint = document.getElementById('otherRequirementHint');
const freestyleEmotionInput = document.getElementById('freestyleEmotion');
const freestyleTimeSlotInput = document.getElementById('freestyleTimeSlot');
const freestyleSceneInput = document.getElementById('freestyleScene');
const freestyleNotesInput = document.getElementById('freestyleNotes');
const recommendationMeta = document.getElementById('recommendationMeta');
const recommendationResult = document.getElementById('recommendationResult');
const assistantStoreMeta = document.getElementById('assistantStoreMeta');
const scopeModeSelect = document.getElementById('scopeMode');
const planPanel = document.getElementById('planPanel');
const planSummary = document.getElementById('planSummary');
const planStoreCard = document.getElementById('planStoreCard');
const planItemList = document.getElementById('planItemList');
const planComboList = document.getElementById('planComboList');
const planActions = document.getElementById('planActions');
const rerollPlanBtn = document.getElementById('rerollPlanBtn');
const addPlanToCartBtn = document.getElementById('addPlanToCartBtn');

const STORAGE_PREFIX = 'customer';
const CART_STORAGE_KEY = `${STORAGE_PREFIX}:cart`;
let storeMetaRefreshTimer = null;
let currentPlan = null;
let excludedItemIds = [];
let lastPlanMode = 'normal';
let selectedPreferenceTags = [];

function authHeaders() {
    const sessionId = localStorage.getItem(`${STORAGE_PREFIX}:sessionId`);
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

function getSelectedStore() {
    const saved = localStorage.getItem(`${STORAGE_PREFIX}:selectedStore`);
    return saved ? JSON.parse(saved) : null;
}

function saveSelectedStore(store) {
    if (store) {
        localStorage.setItem(`${STORAGE_PREFIX}:selectedStore`, JSON.stringify(store));
    }
}

function loadCart() {
    const saved = localStorage.getItem(CART_STORAGE_KEY);
    return saved ? JSON.parse(saved) : [];
}

function saveCart(cart) {
    localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(cart));
}

async function refreshSelectedStore() {
    const selectedStore = getSelectedStore();
    if (!selectedStore) return null;

    try {
        const response = await apiFetch('/api/stores', { headers: authHeaders() });
        const data = await response.json();
        const latestStore = (data.stores || []).find(store => store.id === selectedStore.id) || selectedStore;
        saveSelectedStore(latestStore);
        return latestStore;
    } catch (error) {
        return selectedStore;
    }
}

async function renderStoreMeta() {
    const selectedStore = await refreshSelectedStore();
    assistantStoreMeta.textContent = selectedStore
        ? `当前已选店铺：${selectedStore.name}。你可以切到“优先当前店铺”，也可以继续按全平台推荐。`
        : '当前未选店铺，默认按全平台推荐。';
}

function startStoreMetaRefresh() {
    if (storeMetaRefreshTimer) clearInterval(storeMetaRefreshTimer);
    storeMetaRefreshTimer = setInterval(() => {
        if (document.hidden) return;
        renderStoreMeta();
    }, 3000);
}

function formatPrice(value) {
    return Number(value || 0).toFixed(2);
}

function escapeHtml(value) {
    return String(value || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
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
    window.clearTimeout(window.__smartToastTimer);
    window.__smartToastTimer = window.setTimeout(() => toast.classList.remove('visible'), 1800);
}

function syncPreferenceSummary() {
    selectedPreferenceSummary.textContent = selectedPreferenceTags.length
        ? `已选偏好：${selectedPreferenceTags.join('、')}`
        : '当前未选择固定偏好标签。';
}

function togglePreferenceTag(tag) {
    if (selectedPreferenceTags.includes(tag)) {
        selectedPreferenceTags = selectedPreferenceTags.filter(item => item !== tag);
    } else {
        selectedPreferenceTags = [...selectedPreferenceTags, tag];
    }
    preferenceTagButtons.forEach(button => {
        button.classList.toggle('active', selectedPreferenceTags.includes(button.dataset.tag));
    });
    syncPreferenceSummary();
}

function buildRequestPayload(action = 'generate', extra = {}) {
    const selectedStore = getSelectedStore();
    const useSelectedStore = scopeModeSelect.value === 'selected';
    return {
        action,
        people_count: Number(peopleCountInput.value || 1),
        budget: budgetInput.value.trim(),
        preference_tags: selectedPreferenceTags,
        preferences: selectedPreferenceTags.join('、'),
        other_requirements: otherRequirementsInput.value.trim(),
        store_id: useSelectedStore && selectedStore ? selectedStore.id : null,
        existing_item_ids: currentPlan?.selected_item_ids || [],
        excluded_item_ids: excludedItemIds,
        ...extra
    };
}

function buildFreestylePayload() {
    const selectedStore = getSelectedStore();
    const useSelectedStore = scopeModeSelect.value === 'selected';
    return {
        emotion: freestyleEmotionInput.value,
        time_slot: freestyleTimeSlotInput.value,
        scene: freestyleSceneInput.value,
        extra_notes: freestyleNotesInput.value.trim(),
        budget: budgetInput.value.trim(),
        store_id: useSelectedStore && selectedStore ? selectedStore.id : null,
        people_count: Number(peopleCountInput.value || 1)
    };
}

async function requestRecommendation(action = 'generate', extra = {}) {
    lastPlanMode = 'normal';
    recommendationMeta.textContent = '正在生成推荐...';
    recommendationResult.textContent = '请稍候，系统正在结合菜品、套餐、预算和约束生成可操作推荐。';
    generateRecommendationBtn.disabled = true;
    generateFreestyleRecommendationBtn.disabled = true;
    rerollPlanBtn.disabled = true;
    addPlanToCartBtn.disabled = true;

    try {
        const response = await fetch('/api/smart-order-assistant', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...authHeaders()
            },
            body: JSON.stringify(buildRequestPayload(action, extra))
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || '生成推荐失败');
        }

        currentPlan = data.plan || null;
        recommendationMeta.textContent = data.source === 'remote_api'
            ? '推荐已生成'
            : `推荐已生成${data.warning ? `，${data.warning}` : ''}`;
        if (currentPlan) {
            recommendationMeta.textContent += ` · 已从 ${currentPlan.candidate_store_count || 0} 家店、${currentPlan.candidate_item_count || 0} 道菜中筛选`;
        }
        if (Array.isArray(data.requirement_keywords) && data.requirement_keywords.length) {
            otherRequirementHint.textContent = `其他需求提炼关键词：${data.requirement_keywords.join('、')}（${data.keyword_source === 'remote_ai' ? '大模型提炼' : '本地提炼'}）`;
        } else {
            otherRequirementHint.textContent = '系统会先提炼关键词，再据此搜索更匹配的店铺和菜品。';
        }
        recommendationResult.textContent = data.recommendation || '暂无推荐结果。';
        renderPlan();
    } catch (error) {
        recommendationMeta.textContent = '推荐生成失败';
        recommendationResult.textContent = error.message || '服务暂时不可用。';
        currentPlan = null;
        renderPlan();
    } finally {
        generateRecommendationBtn.disabled = false;
        generateFreestyleRecommendationBtn.disabled = false;
        rerollPlanBtn.disabled = false;
        addPlanToCartBtn.disabled = false;
    }
}

async function requestFreestyleRecommendation() {
    lastPlanMode = 'freestyle';
    recommendationMeta.textContent = '正在生成随心推荐...';
    recommendationResult.textContent = '请稍候，系统正在结合你的情绪、时间段和场景生成推荐。';
    generateRecommendationBtn.disabled = true;
    generateFreestyleRecommendationBtn.disabled = true;
    rerollPlanBtn.disabled = true;
    addPlanToCartBtn.disabled = true;

    try {
        const response = await fetch('/api/smart-order-freestyle', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...authHeaders()
            },
            body: JSON.stringify(buildFreestylePayload())
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || '生成随心推荐失败');
        }

        currentPlan = data.plan || null;
        recommendationMeta.textContent = data.source === 'remote_api'
            ? '随心推荐已生成'
            : `随心推荐已生成${data.warning ? `，${data.warning}` : ''}`;
        if (currentPlan) {
            recommendationMeta.textContent += ` · 已从 ${currentPlan.candidate_store_count || 0} 家店、${currentPlan.candidate_item_count || 0} 道菜中筛选`;
        }
        recommendationResult.textContent = data.recommendation || '暂无推荐结果。';
        renderPlan();
    } catch (error) {
        recommendationMeta.textContent = '随心推荐生成失败';
        recommendationResult.textContent = error.message || '服务暂时不可用。';
        currentPlan = null;
        renderPlan();
    } finally {
        generateRecommendationBtn.disabled = false;
        generateFreestyleRecommendationBtn.disabled = false;
        rerollPlanBtn.disabled = false;
        addPlanToCartBtn.disabled = false;
    }
}

function renderPlan() {
    if (!currentPlan) {
        planPanel.style.display = 'none';
        planActions.style.display = 'none';
        planSummary.textContent = '';
        planStoreCard.innerHTML = '';
        planItemList.innerHTML = '';
        planComboList.innerHTML = '';
        return;
    }

    planPanel.style.display = 'block';
    planActions.style.display = 'flex';
    planSummary.textContent = currentPlan.summary || '';

    if (currentPlan.store) {
        const store = currentPlan.store;
        planStoreCard.innerHTML = `
            <div class="smart-store-card">
                <img class="smart-store-cover" src="${escapeHtml(store.cover_image_url || '')}" alt="${escapeHtml(store.name)} 封面" />
                <div class="smart-store-card-body">
                    <img class="smart-store-avatar" src="${escapeHtml(store.avatar_url || '')}" alt="${escapeHtml(store.name)} 头像" />
                    <div>
                        <h3>${escapeHtml(store.name)}</h3>
                        <p>${escapeHtml(store.description || '暂无店铺介绍')}</p>
                        <div class="store-feed-meta">
                            <span>评分 ${formatPrice(store.rating || 0)}</span>
                            <span>月售 ${store.monthly_sales || 0}</span>
                            <span>配送费 ¥${formatPrice(store.delivery_fee || 0)}</span>
                            <span>起送 ¥${formatPrice(store.min_order_amount || 0)}</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    } else {
        planStoreCard.innerHTML = '';
    }

    planItemList.innerHTML = (currentPlan.items || []).length
        ? currentPlan.items.map(item => `
            <article class="smart-plan-card">
                <div class="smart-plan-card-top">
                    <div>
                        <span class="service-tag">单品</span>
                        <h4>${escapeHtml(item.name)}</h4>
                    </div>
                    <strong>¥${formatPrice(item.price)}</strong>
                </div>
                <p>${escapeHtml(item.description || '暂无描述')}</p>
                <small>${escapeHtml(item.reason || '符合当前条件')}</small>
                <div class="form-actions-row">
                    <button class="secondary replace-item-btn" type="button" data-item-id="${item.id}">换一道菜</button>
                </div>
            </article>
        `).join('')
        : '<p>暂无推荐菜品。</p>';

    planComboList.innerHTML = (currentPlan.combo_alternatives || []).length
        ? currentPlan.combo_alternatives.map(combo => `
            <article class="smart-plan-card alt-card">
                <div class="smart-plan-card-top">
                    <div>
                        <span class="service-tag">套餐</span>
                        <h4>${escapeHtml(combo.name)}</h4>
                    </div>
                    <strong>¥${formatPrice(combo.price)}</strong>
                </div>
                <p>${escapeHtml(combo.description || '暂无描述')}</p>
            </article>
        `).join('')
        : '<p>当前没有更合适的套餐备选。</p>';

    planItemList.querySelectorAll('.replace-item-btn').forEach(button => {
        button.addEventListener('click', async () => {
            const replaceItemId = Number(button.dataset.itemId);
            excludedItemIds = Array.from(new Set([...excludedItemIds, replaceItemId]));
            if (lastPlanMode === 'freestyle') {
                recommendationMeta.textContent = '随心推荐暂不支持逐项换菜，请重新生成新的随心推荐。';
                return;
            }
            await requestRecommendation('replace_item', { replace_item_id: replaceItemId });
        });
    });
}

function addPlanToCart() {
    if (!currentPlan || !currentPlan.store || !(currentPlan.items || []).length) {
        showToast('当前没有可加入购物车的推荐结果');
        return;
    }

    const targetStore = currentPlan.store;
    let cart = loadCart();
    const cartStoreId = cart[0]?.store_id || null;
    if (cart.length && cartStoreId && Number(cartStoreId) !== Number(targetStore.id)) {
        if (!window.confirm('当前购物车已有其他店铺商品，继续会清空购物车。是否继续？')) {
            return;
        }
        cart = [];
    }

    currentPlan.items.forEach(item => {
        const existing = cart.find(cartItem => cartItem.id === item.id && cartItem.type === 'item');
        if (existing) {
            existing.quantity += 1;
            return;
        }
        cart.push({
            id: item.id,
            name: item.name,
            description: item.description,
            price: Number(item.price),
            quantity: 1,
            type: 'item',
            store_id: targetStore.id,
            store_name: targetStore.name,
            image: item.image || null
        });
    });

    saveCart(cart);
    saveSelectedStore(targetStore);
    showToast('推荐结果已加入购物车');
}

renderStoreMeta();
startStoreMetaRefresh();
renderPlan();
syncPreferenceSummary();
preferenceTagButtons.forEach(button => {
    button.addEventListener('click', () => togglePreferenceTag(button.dataset.tag));
});

generateRecommendationBtn.addEventListener('click', async () => {
    excludedItemIds = [];
    await requestRecommendation('generate');
});

generateFreestyleRecommendationBtn.addEventListener('click', async () => {
    excludedItemIds = [];
    await requestFreestyleRecommendation();
});

rerollPlanBtn.addEventListener('click', async () => {
    excludedItemIds = [];
    if (lastPlanMode === 'freestyle') {
        await requestFreestyleRecommendation();
        return;
    }
    await requestRecommendation('rebalance_budget');
});

addPlanToCartBtn.addEventListener('click', addPlanToCart);
