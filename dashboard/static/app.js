// 龙虾斗兽场 by 菠萝菠菠

let ws = null;
let reconnectTimer = null;

function connect() {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${location.host}/ws`);

    ws.onopen = () => {
        document.getElementById('connection-dot').className = 'connection-dot connected';
        if (reconnectTimer) { clearInterval(reconnectTimer); reconnectTimer = null; }
    };

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            if (!data.error) updateDashboard(data);
        } catch (e) {}
    };

    ws.onclose = () => {
        document.getElementById('connection-dot').className = 'connection-dot disconnected';
        if (!reconnectTimer) reconnectTimer = setInterval(connect, 5000);
    };

    ws.onerror = () => {};
}

function updateDashboard(data) {
    updateStats(data);
    updateEvents(data.active_events || []);
    updateAlliances(data.alliances || [], data.lobsters || []);
    // Update circular arena
    if (typeof arena !== 'undefined' && arena) {
        arena.setFighters(data.lobsters || []);
        arena.processEvents(data.recent_events || []);
    }
    updateLeaderboard(data.ranking || []);
    updateLog(data.recent_events || []);
}

function updateStats(data) {
    document.getElementById('alive-count').textContent = `${data.alive_count || 0}/${data.total_count || 10}`;
    document.getElementById('phase-name').textContent = (data.phase || {}).name || '未开始';
    const secs = data.elapsed_seconds || 0;
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    document.getElementById('elapsed-time').textContent = `${m}:${String(Math.floor(s)).padStart(2, '0')}`;
    document.getElementById('game-status').textContent = !data.game_started ? '待开始' : data.game_paused ? '暂停' : '进行中';
}

function updateEvents(events) {
    const el = document.getElementById('active-events');
    if (!events.length) { el.classList.remove('visible'); return; }
    el.classList.add('visible');
    el.innerHTML = '<strong>当前事件</strong> ' + events.map(e => `<span class="tag">${e.name || e}</span>`).join('');
}

function updateAlliances(alliances, lobsters) {
    const section = document.getElementById('alliances-section');
    const container = document.getElementById('alliances');
    if (!alliances || !alliances.length) { section.style.display = 'none'; return; }
    section.style.display = 'block';
    const map = {};
    lobsters.forEach(l => map[l.id] = l);
    container.innerHTML = alliances.map(a => {
        const l1 = map[a.lobster_1] || {};
        const l2 = map[a.lobster_2] || {};
        const mins = Math.floor(a.expires_in / 60);
        const secs = a.expires_in % 60;
        return `<div class="alliance-chip">
            <span>${l1.emoji || ''} ${l1.name || a.lobster_1}</span>
            <span style="color:var(--text2)">⟷</span>
            <span>${l2.emoji || ''} ${l2.name || a.lobster_2}</span>
            <span class="timer">${mins}:${String(secs).padStart(2,'0')}</span>
        </div>`;
    }).join('');
}

function updateLeaderboard(ranking) {
    const el = document.getElementById('leaderboard');
    const header = `<div class="lb-row lb-header">
        <span>排名</span><span>选手</span><span>积分</span><span>击杀</span><span>状态</span>
    </div>`;
    const rows = ranking.map((r, i) => {
        const rankCls = i === 0 ? 'gold' : i === 1 ? 'silver' : i === 2 ? 'bronze' : '';
        const rankText = i === 0 ? '1st' : i === 1 ? '2nd' : i === 2 ? '3rd' : `${i+1}`;
        return `<div class="lb-row">
            <span class="lb-rank ${rankCls}">${rankText}</span>
            <span class="lb-name"><span class="mini-avatar">${r.emoji}</span>${r.name}</span>
            <span class="lb-score">${r.score}</span>
            <span class="lb-kills">${r.kills}</span>
            <span class="lb-status"><span class="status-dot ${r.alive ? 'alive' : 'dead'}"></span></span>
        </div>`;
    }).join('');
    el.innerHTML = header + rows;
}

function updateLog(events) {
    const el = document.getElementById('event-log');
    el.innerHTML = [...events].reverse().map(e => `
        <div class="log-entry ${e.event_type || ''}">
            <span class="log-time">${e.time_str || ''}</span>
            <span class="log-msg">${e.message || ''}</span>
        </div>
    `).join('');
}

document.addEventListener('DOMContentLoaded', () => {
    connect();
    setInterval(async () => {
        if (ws && ws.readyState === WebSocket.OPEN) return;
        try {
            const resp = await fetch('/api/status');
            const data = await resp.json();
            if (!data.error) updateDashboard(data);
        } catch (e) {}
    }, 5000);
});
