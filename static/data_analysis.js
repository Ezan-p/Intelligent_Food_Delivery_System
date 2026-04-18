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

const STORAGE_PREFIX = 'merchant';

function authHeaders() {
    const sessionId = localStorage.getItem(`${STORAGE_PREFIX}:sessionId`);
    return sessionId ? { 'X-Session-ID': sessionId } : {};
}

function formatPrice(value) {
    return Number(value || 0).toFixed(2);
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
        : '<p>暂无订单数据。</p>';
}

function renderTextList(container, items) {
    container.innerHTML = items.length
        ? items.map(item => `<div class="analysis-list-item">${item}</div>`).join('')
        : '<p>暂无内容。</p>';
}

async function loadAnalysis() {
    refreshAnalysisBtn.disabled = true;
    analysisSource.textContent = '正在生成分析...';
    analysisSummary.textContent = '请稍候。';

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
    } catch (error) {
        analysisSource.textContent = '分析加载失败';
        analysisSummary.textContent = error.message || '服务暂时不可用。';
        analysisStats.innerHTML = '';
        topItems.innerHTML = '';
        orderTrendChart.innerHTML = '';
        timeDistributionChart.innerHTML = '';
        analysisInsights.innerHTML = '';
        analysisSuggestions.innerHTML = '';
        analysisRisks.innerHTML = '';
    } finally {
        refreshAnalysisBtn.disabled = false;
    }
}

refreshAnalysisBtn.addEventListener('click', loadAnalysis);
window.addEventListener('load', loadAnalysis);
