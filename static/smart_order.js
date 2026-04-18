const generateRecommendationBtn = document.getElementById('generateRecommendation');
const peopleCountInput = document.getElementById('peopleCount');
const budgetInput = document.getElementById('budget');
const preferencesInput = document.getElementById('preferences');
const recommendationMeta = document.getElementById('recommendationMeta');
const recommendationResult = document.getElementById('recommendationResult');
const assistantStoreMeta = document.getElementById('assistantStoreMeta');

const STORAGE_PREFIX = 'customer';
let storeMetaRefreshTimer = null;

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

async function refreshSelectedStore() {
    const selectedStore = getSelectedStore();
    if (!selectedStore) return null;

    try {
        const response = await apiFetch('/api/stores', { headers: authHeaders() });
        const data = await response.json();
        const latestStore = (data.stores || []).find(store => store.id === selectedStore.id) || selectedStore;
        localStorage.setItem(`${STORAGE_PREFIX}:selectedStore`, JSON.stringify(latestStore));
        return latestStore;
    } catch (error) {
        return selectedStore;
    }
}

async function renderStoreMeta() {
    const selectedStore = await refreshSelectedStore();
    assistantStoreMeta.textContent = selectedStore
        ? `当前店铺：${selectedStore.name}${selectedStore.description ? ` · ${selectedStore.description}` : ''}`
        : '请先返回用户端首页，在店铺列表中选择一家店铺。';
}

function startStoreMetaRefresh() {
    if (storeMetaRefreshTimer) {
        clearInterval(storeMetaRefreshTimer);
    }
    storeMetaRefreshTimer = setInterval(() => {
        if (document.hidden) return;
        renderStoreMeta();
    }, 3000);
}

async function generateRecommendation() {
    const selectedStore = getSelectedStore();
    if (!selectedStore) {
        recommendationMeta.textContent = '未选择店铺';
        recommendationResult.textContent = '请先返回用户端，在店铺列表中选择一家店铺后再使用点餐助手。';
        return;
    }

    const peopleCount = Number(peopleCountInput.value || 1);
    const budget = budgetInput.value.trim();
    const preferences = preferencesInput.value.trim();

    recommendationMeta.textContent = '正在生成推荐...';
    recommendationResult.textContent = '请稍候，系统正在结合当前店铺的菜品和套餐信息分析。';
    generateRecommendationBtn.disabled = true;

    try {
        const response = await fetch('/api/smart-order-assistant', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...authHeaders()
            },
            body: JSON.stringify({
                people_count: peopleCount,
                budget,
                preferences,
                store_id: selectedStore.id
            })
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || '生成推荐失败');
        }

        recommendationMeta.textContent = data.source === 'remote_api'
            ? `推荐已生成，店铺：${selectedStore.name}`
            : `推荐已生成，店铺：${selectedStore.name}，来源：本地策略${data.warning ? `，${data.warning}` : ''}`;
        recommendationResult.textContent = data.recommendation || '暂无推荐结果。';
    } catch (error) {
        recommendationMeta.textContent = '推荐生成失败';
        recommendationResult.textContent = error.message || '服务暂时不可用。';
    } finally {
        generateRecommendationBtn.disabled = false;
    }
}

renderStoreMeta();
startStoreMetaRefresh();
generateRecommendationBtn.addEventListener('click', generateRecommendation);
