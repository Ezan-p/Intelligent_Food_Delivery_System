const refreshAnalysisBtn = document.getElementById('refreshAnalysis');
const analysisStats = document.getElementById('analysisStats');
const topItems = document.getElementById('topItems');
const orderTrendChart = document.getElementById('orderTrendChart');
const timeDistributionChart = document.getElementById('timeDistributionChart');
const reviewStatsPanel = document.getElementById('reviewStatsPanel');
const analysisSource = document.getElementById('analysisSource');
const analysisSummary = document.getElementById('analysisSummary');
const analysisInsights = document.getElementById('analysisInsights');
const analysisSuggestions = document.getElementById('analysisSuggestions');
const analysisRisks = document.getElementById('analysisRisks');
const analysisToast = document.getElementById('analysisToast');
const merchantAssistantContext = document.getElementById('merchantAssistantContext');
const merchantAssistantMessages = document.getElementById('merchantAssistantMessages');
const merchantAssistantForm = document.getElementById('merchantAssistantForm');
const merchantAssistantInput = document.getElementById('merchantAssistantInput');
const clearMerchantAssistantBtn = document.getElementById('clearMerchantAssistantBtn');
const sidebarAnchorItems = document.querySelectorAll('.sidebar-anchor-menu .menu-item[href^="#"]');

const STORAGE_PREFIX = 'merchant';
const ASSISTANT_HISTORY_LIMIT = 8;
let toastTimer = null;
let merchantAssistantHistory = [];

function authHeaders() {
    const sessionId = localStorage.getItem(`${STORAGE_PREFIX}:sessionId`);
    return sessionId ? { 'X-Session-ID': sessionId } : {};
}

function formatPrice(value) {
    return Number(value || 0).toFixed(2);
}

function showToast(message, type = 'info') {
    if (!analysisToast) return;
    analysisToast.textContent = message;
    analysisToast.className = `app-toast toast-${type}`;
    analysisToast.classList.add('visible');
    window.clearTimeout(toastTimer);
    toastTimer = window.setTimeout(() => {
        analysisToast.classList.remove('visible');
    }, 2200);
}

function buildFeedbackState(type, title, message) {
    const spinner = type === 'loading' ? '<span class="feedback-spinner" aria-hidden="true"></span>' : '';
    return `
        <div class="feedback-state ${type}">
            ${spinner}
            <strong>${title}</strong>
            <p>${message}</p>
        </div>`;
}

function setBlockState(container, type, title, message) {
    if (!container) return;
    container.innerHTML = buildFeedbackState(type, title, message);
}

function renderLoadingState() {
    setBlockState(analysisStats, 'loading', '指标计算中', '正在汇总营业额、订单量和复购率。');
    setBlockState(orderTrendChart, 'loading', '订单趋势生成中', '正在整理近阶段订单变化。');
    setBlockState(topItems, 'loading', '热销商品生成中', '正在统计商品销量排行。');
    setBlockState(timeDistributionChart, 'loading', '时段分布生成中', '正在分析不同时间段的订单表现。');
    setBlockState(reviewStatsPanel, 'loading', '评价指标生成中', '正在汇总评分、口味、包装与配送反馈。');
    setBlockState(analysisInsights, 'loading', '洞察生成中', '正在提取经营重点。');
    setBlockState(analysisSuggestions, 'loading', '建议生成中', '正在整理优化建议。');
    setBlockState(analysisRisks, 'loading', '风险扫描中', '正在识别经营风险。');
}

function renderErrorState(message) {
    setBlockState(analysisStats, 'error', '分析加载失败', message);
    setBlockState(orderTrendChart, 'error', '图表加载失败', message);
    setBlockState(topItems, 'error', '图表加载失败', message);
    setBlockState(timeDistributionChart, 'error', '图表加载失败', message);
    setBlockState(reviewStatsPanel, 'error', '评价指标加载失败', message);
    setBlockState(analysisInsights, 'error', '洞察加载失败', message);
    setBlockState(analysisSuggestions, 'error', '建议加载失败', message);
    setBlockState(analysisRisks, 'error', '风险加载失败', message);
}

function renderStats(stats) {
    analysisStats.innerHTML = `
        <div class="stat-card"><h3>营业额</h3><div class="stat-value">¥${formatPrice(stats.revenue)}</div></div>
        <div class="stat-card"><h3>订单量</h3><div class="stat-value">${stats.order_volume || 0}</div></div>
        <div class="stat-card"><h3>客单价</h3><div class="stat-value">¥${formatPrice(stats.average_order_value)}</div></div>
        <div class="stat-card"><h3>复购率</h3><div class="stat-value">${Number(stats.repurchase_rate || 0).toFixed(2)}%</div></div>`;
}

function renderBarList(container, items, formatter) {
    container.innerHTML = items.length
        ? items.map(item => `
            <div class="analysis-list-item">
                <div class="chart-row-head">
                    <strong>${item.label || item.name}</strong>
                    <span>${formatter(item)}</span>
                </div>
                <div class="chart-bar-track">
                    <div class="chart-bar-fill" style="width: ${Math.min(100, Number(item.percent || 0))}%"></div>
                </div>
            </div>`).join('')
        : buildFeedbackState('empty', '暂无图表数据', '当前没有可展示的数据。');
}

function renderTextList(container, items) {
    container.innerHTML = items.length
        ? items.map(item => `<div class="analysis-list-item">${item}</div>`).join('')
        : buildFeedbackState('empty', '暂无内容', '当前没有可展示的分析结果。');
}

function renderReviewStats(reviewStats) {
    if (!reviewStats || !reviewStats.review_count) {
        reviewStatsPanel.innerHTML = buildFeedbackState('empty', '暂无评价数据', '当前还没有足够评价样本。');
        return;
    }
    reviewStatsPanel.innerHTML = `
        <div class="analysis-list-item"><strong>评价数量</strong><span>${reviewStats.review_count}</span></div>
        <div class="analysis-list-item"><strong>综合评分</strong><span>${Number(reviewStats.average_rating || 0).toFixed(1)}</span></div>
        <div class="analysis-list-item"><strong>配送评分</strong><span>${Number(reviewStats.delivery_rating || 0).toFixed(1)}</span></div>
        <div class="analysis-list-item"><strong>包装评分</strong><span>${Number(reviewStats.packaging_rating || 0).toFixed(1)}</span></div>
        <div class="analysis-list-item"><strong>口味评分</strong><span>${Number(reviewStats.taste_rating || 0).toFixed(1)}</span></div>
        <div class="analysis-list-item"><strong>低分评价</strong><span>${reviewStats.low_rating_count || 0}</span></div>`;
}

function normalizeChartItems(items, valueKey) {
    const maxValue = Math.max(...items.map(entry => Number(entry[valueKey] || 0)), 1);
    return items.map(item => ({
        ...item,
        percent: (Number(item[valueKey] || 0) / maxValue) * 100
    }));
}

function renderAssistantMessages() {
    if (!merchantAssistantMessages) return;
    if (!merchantAssistantHistory.length) {
        merchantAssistantMessages.innerHTML = buildFeedbackState('empty', '等待提问', '你可以直接询问复购、商品优化、差评处理、活动设计等经营问题。');
        return;
    }

    merchantAssistantMessages.innerHTML = merchantAssistantHistory.map(item => `
        <div class="assistant-message assistant-${item.role}">
            <div class="assistant-message-role">${item.role === 'user' ? '商家' : '经营助手'}</div>
            <div class="assistant-message-content">${(item.content || '').replace(/\n/g, '<br />')}</div>
        </div>
    `).join('');
    merchantAssistantMessages.scrollTop = merchantAssistantMessages.scrollHeight;
}

function setAssistantPending() {
    if (!merchantAssistantMessages) return;
    merchantAssistantMessages.innerHTML += `
        <div class="assistant-message assistant-assistant assistant-pending">
            <div class="assistant-message-role">经营助手</div>
            <div class="assistant-message-content">正在结合当前店铺数据生成建议...</div>
        </div>`;
    merchantAssistantMessages.scrollTop = merchantAssistantMessages.scrollHeight;
}

function clearAssistantPending() {
    const pending = merchantAssistantMessages?.querySelector('.assistant-pending');
    if (pending) pending.remove();
}

async function loadAnalysis() {
    refreshAnalysisBtn.disabled = true;
    analysisSource.textContent = '正在生成分析...';
    analysisSummary.textContent = '请稍候。';
    merchantAssistantContext.textContent = '正在同步当前分析上下文...';
    renderLoadingState();

    try {
        const response = await fetch('/api/data-analysis', {
            headers: authHeaders()
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || '分析加载失败');
        }

        renderStats(data.stats || {});
        renderBarList(orderTrendChart, normalizeChartItems(data.charts?.order_trend || [], 'value'), item => `${item.value} 单`);
        renderBarList(topItems, normalizeChartItems(data.charts?.top_items || [], 'quantity'), item => `销量 ${item.quantity} · ¥${formatPrice(item.revenue)}`);
        renderBarList(timeDistributionChart, normalizeChartItems(data.charts?.time_distribution || [], 'value'), item => `${item.value} 单`);
        renderReviewStats(data.review_stats || {});
        renderTextList(analysisInsights, data.insights || []);
        renderTextList(analysisSuggestions, data.suggestions || []);
        renderTextList(analysisRisks, data.risks || []);

        analysisSummary.textContent = data.ai_summary || data.narrative_summary || '暂无分析摘要。';
        merchantAssistantContext.textContent = data.narrative_summary || data.ai_summary || '暂无上下文摘要。';
        analysisSource.textContent = data.source === 'remote_api'
            ? '当前结果由 AI 经营分析生成'
            : `当前结果为系统自动总结${data.warning ? `，${data.warning}` : ''}`;
        showToast('经营分析已刷新。', 'success');
    } catch (error) {
        analysisSource.textContent = '分析加载失败';
        analysisSummary.textContent = error.message || '服务暂时不可用。';
        merchantAssistantContext.textContent = error.message || '上下文加载失败。';
        renderErrorState(error.message || '服务暂时不可用。');
        showToast(error.message || '分析加载失败。', 'error');
    } finally {
        refreshAnalysisBtn.disabled = false;
    }
}

async function submitMerchantAssistantQuestion(event) {
    event.preventDefault();
    const message = merchantAssistantInput.value.trim();
    if (!message) {
        showToast('请输入经营问题。', 'error');
        return;
    }

    merchantAssistantHistory.push({ role: 'user', content: message });
    renderAssistantMessages();
    merchantAssistantInput.value = '';
    setAssistantPending();

    try {
        const response = await fetch('/api/merchant-assistant', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...authHeaders()
            },
            body: JSON.stringify({
                message,
                history: merchantAssistantHistory.slice(-ASSISTANT_HISTORY_LIMIT)
            })
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || '经营助手暂时不可用');
        }

        clearAssistantPending();
        merchantAssistantHistory.push({ role: 'assistant', content: data.reply || '暂无回复。' });
        merchantAssistantHistory = merchantAssistantHistory.slice(-ASSISTANT_HISTORY_LIMIT * 2);
        if (data.context_summary) {
            merchantAssistantContext.textContent = data.context_summary;
        }
        renderAssistantMessages();
        showToast(data.source === 'remote_api' ? '经营助手已回复。' : '已回退到本地经营建议。', data.source === 'remote_api' ? 'success' : 'info');
    } catch (error) {
        clearAssistantPending();
        merchantAssistantHistory.push({ role: 'assistant', content: error.message || '经营助手暂时不可用。' });
        renderAssistantMessages();
        showToast(error.message || '经营助手暂时不可用。', 'error');
    }
}

function clearAssistantHistory() {
    merchantAssistantHistory = [];
    renderAssistantMessages();
    merchantAssistantInput.value = '';
    showToast('经营助手对话已清空。', 'success');
}

function bindSidebarAnchors() {
    sidebarAnchorItems.forEach(anchor => {
        anchor.addEventListener('click', () => {
            sidebarAnchorItems.forEach(item => item.classList.remove('active'));
            anchor.classList.add('active');
        });
    });
}

refreshAnalysisBtn.addEventListener('click', loadAnalysis);
merchantAssistantForm.addEventListener('submit', submitMerchantAssistantQuestion);
clearMerchantAssistantBtn.addEventListener('click', clearAssistantHistory);

window.addEventListener('load', () => {
    bindSidebarAnchors();
    renderAssistantMessages();
    loadAnalysis();
});
