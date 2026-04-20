const refreshAnalysisBtn = document.getElementById('refreshAnalysis');
const analysisStats = document.getElementById('analysisStats');
const topItems = document.getElementById('topItems');
const orderTrendChart = document.getElementById('orderTrendChart');
const timeDistributionChart = document.getElementById('timeDistributionChart');
const analysisSource = document.getElementById('analysisSource');
const analysisSummary = document.getElementById('analysisSummary');
const analysisInsights = document.getElementById('analysisInsights');
const analysisSuggestions = document.getElementById('analysisSuggestions');
const analysisRisks = document.getElementById('analysisRisks');
const analysisToast = document.getElementById('analysisToast');

const STORAGE_PREFIX = 'merchant';
let toastTimer = null;

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
    container.innerHTML = buildFeedbackState(type, title, message);
}

function renderLoadingState() {
    setBlockState(analysisStats, 'loading', '指标计算中', '正在汇总营业额、订单量和复购率。');
    setBlockState(orderTrendChart, 'loading', '订单趋势生成中', '正在整理近阶段订单变化。');
    setBlockState(topItems, 'loading', '热销商品生成中', '正在统计商品销量排行。');
    setBlockState(timeDistributionChart, 'loading', '时段分布生成中', '正在分析不同时间段的订单表现。');
    setBlockState(analysisInsights, 'loading', '洞察生成中', '正在提取经营重点。');
    setBlockState(analysisSuggestions, 'loading', '建议生成中', '正在整理优化建议。');
    setBlockState(analysisRisks, 'loading', '风险扫描中', '正在识别经营风险。');
}

function renderErrorState(message) {
    setBlockState(analysisStats, 'error', '分析加载失败', message);
    setBlockState(orderTrendChart, 'error', '图表加载失败', message);
    setBlockState(topItems, 'error', '图表加载失败', message);
    setBlockState(timeDistributionChart, 'error', '图表加载失败', message);
    setBlockState(analysisInsights, 'error', '洞察加载失败', message);
    setBlockState(analysisSuggestions, 'error', '建议加载失败', message);
    setBlockState(analysisRisks, 'error', '风险加载失败', message);
}

function renderStats(stats) {
    analysisStats.innerHTML = `
        <div class="stat-card"><h3>营业额</h3><div class="stat-value">¥${formatPrice(stats.revenue)}</div></div>
        <div class="stat-card"><h3>订单量</h3><div class="stat-value">${stats.order_volume}</div></div>
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

async function loadAnalysis() {
    refreshAnalysisBtn.disabled = true;
    analysisSource.textContent = '正在生成分析...';
    analysisSummary.textContent = '请稍候。';
    renderLoadingState();

    try {
        const response = await fetch('/api/data-analysis', {
            headers: authHeaders()
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || '分析加载失败');
        }

        const stats = data.stats || {};
        const charts = data.charts || {};
        const trendData = (charts.order_trend || []).map(item => ({
            ...item,
            percent: Math.max(...(charts.order_trend || []).map(entry => Number(entry.value || 0)), 1) ? (Number(item.value || 0) / Math.max(...(charts.order_trend || []).map(entry => Number(entry.value || 0)), 1)) * 100 : 0
        }));
        const topItemsData = (charts.top_items || []).map(item => ({
            ...item,
            percent: Math.max(...(charts.top_items || []).map(entry => Number(entry.quantity || 0)), 1) ? (Number(item.quantity || 0) / Math.max(...(charts.top_items || []).map(entry => Number(entry.quantity || 0)), 1)) * 100 : 0
        }));
        const timeData = (charts.time_distribution || []).map(item => ({
            ...item,
            percent: Math.max(...(charts.time_distribution || []).map(entry => Number(entry.value || 0)), 1) ? (Number(item.value || 0) / Math.max(...(charts.time_distribution || []).map(entry => Number(entry.value || 0)), 1)) * 100 : 0
        }));

        renderStats(stats);
        renderBarList(orderTrendChart, trendData, item => `${item.value} 单`);
        renderBarList(topItems, topItemsData, item => `销量 ${item.quantity} · ¥${formatPrice(item.revenue)}`);
        renderBarList(timeDistributionChart, timeData, item => `${item.value} 单`);
        renderTextList(analysisInsights, data.insights || []);
        renderTextList(analysisSuggestions, data.suggestions || []);
        renderTextList(analysisRisks, data.risks || []);
        analysisSummary.textContent = data.ai_summary || '暂无分析摘要。';
        analysisSource.textContent = data.source === 'remote_api'
            ? '当前结果由 AI 经营分析生成'
            : `当前结果为本地分析${data.warning ? `，${data.warning}` : ''}`;
        showToast('经营分析已刷新。', 'success');
    } catch (error) {
        analysisSource.textContent = '分析加载失败';
        analysisSummary.textContent = error.message || '服务暂时不可用。';
        renderErrorState(error.message || '服务暂时不可用。');
        showToast(error.message || '分析加载失败。', 'error');
    } finally {
        refreshAnalysisBtn.disabled = false;
    }
}

refreshAnalysisBtn.addEventListener('click', loadAnalysis);
window.addEventListener('load', loadAnalysis);
