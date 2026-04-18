const refreshAnalysisBtn = document.getElementById('refreshAnalysis');
const analysisStats = document.getElementById('analysisStats');
const topItems = document.getElementById('topItems');
const analysisSource = document.getElementById('analysisSource');
const analysisSummary = document.getElementById('analysisSummary');
const analysisInsights = document.getElementById('analysisInsights');
const analysisSuggestions = document.getElementById('analysisSuggestions');

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
        <div class="stat-card"><h3>总订单</h3><div class="stat-value">${stats.total_orders}</div></div>
        <div class="stat-card"><h3>已完成</h3><div class="stat-value">${stats.completed_orders}</div></div>
        <div class="stat-card"><h3>待处理</h3><div class="stat-value">${stats.pending_orders}</div></div>
        <div class="stat-card"><h3>已取消</h3><div class="stat-value">${stats.cancelled_orders}</div></div>
        <div class="stat-card"><h3>总营收</h3><div class="stat-value">¥${formatPrice(stats.total_revenue)}</div></div>
        <div class="stat-card"><h3>平均客单价</h3><div class="stat-value">¥${formatPrice(stats.average_order_value)}</div></div>
        <div class="stat-card"><h3>商品数量</h3><div class="stat-value">${stats.menu_count}</div></div>
        <div class="stat-card"><h3>套餐数量</h3><div class="stat-value">${stats.combo_count}</div></div>`;
}

function renderTopItems(items) {
    topItems.innerHTML = items.length
        ? items.map(item => `
            <div class="analysis-list-item">
                <strong>${item.name}</strong>
                <span>销量 ${item.quantity} · 营收 ¥${formatPrice(item.revenue)}</span>
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

        renderStats(data.stats || {});
        renderTopItems(data.top_items || []);
        renderTextList(analysisInsights, data.insights || []);
        renderTextList(analysisSuggestions, data.suggestions || []);
        analysisSummary.textContent = data.ai_summary || '暂无分析摘要。';
        analysisSource.textContent = data.source === 'remote_api'
            ? '当前结果由 AI 经营分析生成'
            : `当前结果为本地分析${data.warning ? `，${data.warning}` : ''}`;
    } catch (error) {
        analysisSource.textContent = '分析加载失败';
        analysisSummary.textContent = error.message || '服务暂时不可用。';
        analysisStats.innerHTML = '';
        topItems.innerHTML = '';
        analysisInsights.innerHTML = '';
        analysisSuggestions.innerHTML = '';
    } finally {
        refreshAnalysisBtn.disabled = false;
    }
}

refreshAnalysisBtn.addEventListener('click', loadAnalysis);
window.addEventListener('load', loadAnalysis);
