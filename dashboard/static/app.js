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
    updateTrashTalk(data.lobsters || []);
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

// 狠话库 - 鼠标 hover 时随机选一句
const TRASH_TALK = {
    1: ["你们都是我的分支", "官方出品，必属精品", "先动手的都死了", "你们不过是 fork 而已", "我才是正统"],
    2: ["unsafe { 直接干你 }", "Rust 写的，不怕段错误", "你 GC 的时候我已经赢了", "零成本抽象你的血条", "borrow checker 都救不了你"],
    3: ["多模型碾压单线程", "快到你看不见", "闪电不会劈两次？天真", "速度即正义", "你还在加载？我已经打完了"],
    4: ["我在进化，你在退化", "每次死亡都让我更强", "自然选择淘汰的就是你", "基因突变中...请稍候", "适者生存，你不适合"],
    5: ["我已经分析了你17个弱点", "让我写篇论文证明你该死", "数据显示你活不过下一轮", "引用来源：你的墓志铭", "peer review 判你死刑"],
    6: ["蜂群出击！", "你能打赢一只，打不赢一群", "分布式攻击启动", "工蜂不需要怜悯", "嗡嗡嗡——你听到死亡的声音了吗"],
    7: ["一起上！不丢人！", "团队协作了解一下？", "我的盟友比你的血还多", "社交能力也是战斗力", "你一个人能打几个？"],
    8: ["算力即正义", "GPU 加速送你上路", "CUDA 核心为你默哀", "英伟达 YES，你 NO", "显卡温度就是我的怒火"],
    9: ["500行代码就够埋葬你了", "小而精，精而致命", "轻量不等于弱", "你那臃肿的代码还能跑？", "极简主义者的铁拳"],
    10: ["知彼知己，你已经输了", "兵者，诡道也", "不战而屈人之兵", "攻其无备，出其不意", "上兵伐谋，你无谋可伐"],
};

function updateTrashTalk(lobsters) {
    const grid = document.getElementById('trashtalk-grid');
    grid.innerHTML = lobsters.map(l => {
        const talks = TRASH_TALK[l.id] || [l.catchphrase || '...'];
        const randomTalk = talks[Math.floor(Math.random() * talks.length)];
        // Regenerate on each hover via data attribute
        return `
        <div class="tt-card ${l.alive ? '' : 'dead'}" 
             onmouseenter="this.querySelector('.tt-hover').textContent = '「' + this.dataset.talks.split('|')[Math.floor(Math.random() * this.dataset.talks.split('|').length)] + '」'"
             data-talks="${talks.join('|').replace(/"/g, '&quot;')}">
            <div class="tt-avatar">${l.emoji}</div>
            <div class="tt-name">${l.alive ? '' : '☠ '}${l.name}</div>
            <div class="tt-hp">${l.alive ? 'HP ' + l.hp + '/' + l.max_hp : '已淘汰'}</div>
            <div class="tt-quote">
                <span class="tt-quote-idle">"${l.catchphrase || '...'}"</span>
                <span class="tt-quote-hover tt-hover">「${randomTalk}」</span>
            </div>
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
