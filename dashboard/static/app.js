// 龙虾大乱斗 - 实时战况前端

let ws = null;
let reconnectTimer = null;

// WebSocket 连接
function connect() {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${location.host}/ws`);

    ws.onopen = () => {
        console.log('✅ WebSocket 已连接');
        updateConnectionStatus(true);
        if (reconnectTimer) {
            clearInterval(reconnectTimer);
            reconnectTimer = null;
        }
    };

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            if (!data.error) {
                updateDashboard(data);
            }
        } catch (e) {
            console.error('解析数据失败:', e);
        }
    };

    ws.onclose = () => {
        console.log('❌ WebSocket 断开，5秒后重连...');
        updateConnectionStatus(false);
        if (!reconnectTimer) {
            reconnectTimer = setInterval(connect, 5000);
        }
    };

    ws.onerror = (err) => {
        console.error('WebSocket 错误:', err);
    };
}

function updateConnectionStatus(connected) {
    const el = document.getElementById('connection-status');
    el.className = `connection-status ${connected ? 'connected' : 'disconnected'}`;
    el.textContent = connected ? '🟢 已连接' : '🔴 断开连接';
}

// 更新整个仪表盘
function updateDashboard(data) {
    updateStatusBar(data);
    updateActiveEvents(data.active_events || []);
    updateLobsterGrid(data.lobsters || []);
    updateAlliances(data.alliances || [], data.lobsters || []);
    updateRanking(data.ranking || []);
    updateEventLog(data.recent_events || []);
}

// 状态栏
function updateStatusBar(data) {
    document.getElementById('alive-count').textContent =
        `${data.alive_count || 0} / ${data.total_count || 10}`;

    const phase = data.phase || {};
    document.getElementById('phase-name').textContent =
        phase.name || '未开始';

    const hours = data.elapsed_hours || 0;
    if (hours < 1) {
        document.getElementById('elapsed-time').textContent =
            `${Math.floor((data.elapsed_seconds || 0) / 60)} 分钟`;
    } else if (hours < 24) {
        document.getElementById('elapsed-time').textContent =
            `${hours.toFixed(1)} 小时`;
    } else {
        document.getElementById('elapsed-time').textContent =
            `${(hours / 24).toFixed(1)} 天`;
    }

    const statusText = !data.game_started ? '等待开始' :
        data.game_paused ? '⏸️ 暂停中' : '🔴 进行中';
    document.getElementById('game-status').textContent = statusText;
}

// 活跃事件
function updateActiveEvents(events) {
    const container = document.getElementById('active-events');
    if (events.length === 0) {
        container.classList.remove('visible');
        return;
    }
    container.classList.add('visible');
    container.innerHTML = '<strong>⚡ 当前事件：</strong> ' +
        events.map(e =>
            `<span class="event-badge">🎲 ${e.name || e}</span>`
        ).join('');
}

// 龙虾卡片
function updateLobsterGrid(lobsters) {
    const grid = document.getElementById('lobster-grid');
    grid.innerHTML = lobsters.map(l => {
        const hpPercent = (l.hp / l.max_hp * 100).toFixed(0);
        const hpClass = !l.alive ? 'dead' :
            hpPercent <= 20 ? 'critical' :
            hpPercent <= 50 ? 'low' : '';
        const cardClass = l.alive ? '' : 'eliminated';
        const statusIcon = l.alive ? '' : '💀 ';

        return `
        <div class="lobster-card ${cardClass}">
            <div class="lobster-header">
                <span class="lobster-emoji">${l.emoji}</span>
                <div>
                    <div class="lobster-name">${statusIcon}${l.name}</div>
                    <div class="lobster-origin">${l.origin}</div>
                </div>
            </div>
            <div class="hp-bar-container">
                <div class="hp-bar ${hpClass}" style="width: ${l.alive ? hpPercent : 0}%"></div>
                <span class="hp-text">${l.alive ? `${l.hp} / ${l.max_hp}` : '已淘汰'}</span>
            </div>
            <div class="lobster-stats">
                <span class="stat">⚔️ 击杀: ${l.kills}</span>
                <span class="stat">🏆 积分: ${l.score}</span>
                <span class="stat">🛡️ ${l.active_defense || '无防御'}</span>
            </div>
        </div>`;
    }).join('');
}

// 结盟关系
function updateAlliances(alliances, lobsters) {
    const container = document.getElementById('alliances');
    if (!alliances || alliances.length === 0) {
        container.innerHTML = '<span style="color: var(--text-secondary)">暂无结盟</span>';
        return;
    }
    const lobsterMap = {};
    lobsters.forEach(l => lobsterMap[l.id] = l);

    container.innerHTML = alliances.map(a => {
        const l1 = lobsterMap[a.lobster_1] || {};
        const l2 = lobsterMap[a.lobster_2] || {};
        const mins = Math.floor(a.expires_in / 60);
        const secs = a.expires_in % 60;
        return `<span class="alliance-badge">🤝 ${l1.emoji || ''} ${l1.name || a.lobster_1} ⟷ ${l2.emoji || ''} ${l2.name || a.lobster_2} (${mins}:${secs.toString().padStart(2,'0')})</span>`;
    }).join('');
}

// 排行榜
function updateRanking(ranking) {
    const tbody = document.getElementById('ranking-body');
    tbody.innerHTML = ranking.map((r, i) => {
        const rankClass = i < 3 ? `rank-${i + 1}` : '';
        const medal = i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : `#${i + 1}`;
        const status = r.alive ? '🟢' : '🔴';
        return `
        <tr class="${rankClass}">
            <td>${medal}</td>
            <td>${r.emoji} ${r.name}</td>
            <td>${r.score}</td>
            <td>${r.kills}</td>
            <td>${status}</td>
        </tr>`;
    }).join('');
}

// 事件日志
function updateEventLog(events) {
    const log = document.getElementById('event-log');
    log.innerHTML = events.reverse().map(e => `
        <div class="event-item ${e.event_type || ''}">
            <span class="event-time">${e.time_str || ''}</span>
            <span class="event-message">${e.message || JSON.stringify(e)}</span>
        </div>
    `).join('');
}

// 格式化时间
function formatDuration(seconds) {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    if (h > 0) return `${h}小时${m}分`;
    return `${m}分钟`;
}

// 启动
document.addEventListener('DOMContentLoaded', () => {
    connect();

    // 备用轮询（WebSocket 失败时）
    setInterval(async () => {
        if (ws && ws.readyState === WebSocket.OPEN) return;
        try {
            const resp = await fetch('/api/status');
            const data = await resp.json();
            if (!data.error) updateDashboard(data);
        } catch (e) {
            console.error('轮询失败:', e);
        }
    }, 5000);
});
