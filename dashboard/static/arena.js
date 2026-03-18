// 圆形斗兽场 + 攻击箭头动画

class ArenaRenderer {
    constructor() {
        this.canvas = document.getElementById('arena-canvas');
        this.ctx = this.canvas.getContext('2d');
        this.fighters = [];
        this.attacks = [];      // 攻击动画队列
        this.positions = {};    // lobster_id -> {x, y, angle}
        this.lastEvents = [];
        this.dpr = window.devicePixelRatio || 1;
        this.resize();
        window.addEventListener('resize', () => this.resize());
        this.animate();
    }

    resize() {
        const wrapper = this.canvas.parentElement;
        const size = Math.min(wrapper.clientWidth, 700);
        this.size = size;
        this.canvas.style.width = size + 'px';
        this.canvas.style.height = size + 'px';
        this.canvas.width = size * this.dpr;
        this.canvas.height = size * this.dpr;
        this.ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
        this.cx = size / 2;
        this.cy = size / 2;
        this.radius = size * 0.36;
        this.updatePositions();
    }

    updatePositions() {
        const n = this.fighters.length || 10;
        this.positions = {};
        this.fighters.forEach((f, i) => {
            const angle = (i / n) * Math.PI * 2 - Math.PI / 2;
            this.positions[f.id] = {
                x: this.cx + Math.cos(angle) * this.radius,
                y: this.cy + Math.sin(angle) * this.radius,
                angle: angle
            };
        });
    }

    setFighters(lobsters) {
        this.fighters = lobsters;
        this.updatePositions();
        this.updateFighterDom();
    }

    processEvents(events) {
        // 找出新的攻击事件
        const newEvents = events.filter(e =>
            e.event_type === 'attack' && e.detail && e.detail.success !== undefined &&
            !this.lastEvents.some(le => le.timestamp === e.timestamp && le.source_id === e.source_id)
        );
        newEvents.forEach(e => {
            this.addAttack(e.source_id, e.target_id, e.detail.success, e.detail.attack_name || '');
        });
        // 结盟动画
        const allyEvents = events.filter(e =>
            e.event_type === 'alliance' && e.message && e.message.includes('结盟') &&
            !this.lastEvents.some(le => le.timestamp === e.timestamp)
        );
        allyEvents.forEach(e => {
            this.addAllianceLine(e.source_id, e.target_id);
        });
        this.lastEvents = events.slice(-30);
    }

    addAttack(fromId, toId, success, name) {
        this.attacks.push({
            from: fromId,
            to: toId,
            success: success,
            name: name,
            progress: 0,
            startTime: performance.now(),
            duration: 800,
            type: 'attack'
        });
    }

    addAllianceLine(id1, id2) {
        this.attacks.push({
            from: id1,
            to: id2,
            success: true,
            name: '结盟',
            progress: 0,
            startTime: performance.now(),
            duration: 1500,
            type: 'alliance'
        });
    }

    updateFighterDom() {
        const container = document.getElementById('arena-fighters');
        container.innerHTML = '';
        this.fighters.forEach(f => {
            const pos = this.positions[f.id];
            if (!pos) return;
            const pct = Math.round(f.hp / f.max_hp * 100);
            const hpColor = !f.alive ? '#555' : pct <= 20 ? '#ff4757' : pct <= 50 ? '#ffa502' : '#2ed573';

            const el = document.createElement('div');
            el.className = `arena-fighter ${f.alive ? '' : 'dead'}`;
            el.style.left = pos.x + 'px';
            el.style.top = pos.y + 'px';
            el.innerHTML = `
                <div class="af-avatar" style="border-color:${hpColor}">${f.emoji}</div>
                <div class="af-hp-ring">
                    <svg viewBox="0 0 40 40">
                        <circle cx="20" cy="20" r="17" fill="none" stroke="#222" stroke-width="3"/>
                        <circle cx="20" cy="20" r="17" fill="none" stroke="${hpColor}" stroke-width="3"
                            stroke-dasharray="${f.alive ? pct * 1.068 : 0} 106.8"
                            stroke-linecap="round" transform="rotate(-90 20 20)"/>
                    </svg>
                </div>
                <div class="af-name">${f.name}</div>
                <div class="af-hp-text" style="color:${hpColor}">${f.alive ? f.hp : '☠'}</div>
            `;
            container.appendChild(el);
        });
    }

    animate() {
        const ctx = this.ctx;
        const now = performance.now();
        ctx.clearRect(0, 0, this.size, this.size);

        // Draw arena circle
        ctx.beginPath();
        ctx.arc(this.cx, this.cy, this.radius + 30, 0, Math.PI * 2);
        ctx.strokeStyle = 'rgba(255,255,255,0.04)';
        ctx.lineWidth = 1;
        ctx.stroke();

        ctx.beginPath();
        ctx.arc(this.cx, this.cy, this.radius + 60, 0, Math.PI * 2);
        ctx.strokeStyle = 'rgba(255,255,255,0.02)';
        ctx.stroke();

        // Inner circle glow
        const grad = ctx.createRadialGradient(this.cx, this.cy, 0, this.cx, this.cy, this.radius + 30);
        grad.addColorStop(0, 'rgba(255,71,87,0.03)');
        grad.addColorStop(0.5, 'rgba(55,66,250,0.02)');
        grad.addColorStop(1, 'transparent');
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(this.cx, this.cy, this.radius + 30, 0, Math.PI * 2);
        ctx.fill();

        // Draw attacks
        this.attacks = this.attacks.filter(a => {
            const elapsed = now - a.startTime;
            const progress = Math.min(elapsed / a.duration, 1);
            const from = this.positions[a.from];
            const to = this.positions[a.to];
            if (!from || !to) return false;

            if (a.type === 'alliance') {
                // Alliance: blue dashed line that fades in then out
                const alpha = progress < 0.5 ? progress * 2 : (1 - progress) * 2;
                ctx.beginPath();
                ctx.moveTo(from.x, from.y);
                ctx.lineTo(to.x, to.y);
                ctx.strokeStyle = `rgba(112, 161, 255, ${alpha * 0.6})`;
                ctx.lineWidth = 2;
                ctx.setLineDash([6, 4]);
                ctx.stroke();
                ctx.setLineDash([]);
                return progress < 1;
            }

            // Attack arrow
            const easeOut = 1 - Math.pow(1 - progress, 3);
            const headX = from.x + (to.x - from.x) * easeOut;
            const headY = from.y + (to.y - from.y) * easeOut;

            // Trail
            const trailStart = Math.max(0, easeOut - 0.3);
            const tailX = from.x + (to.x - from.x) * trailStart;
            const tailY = from.y + (to.y - from.y) * trailStart;

            const color = a.success ? 'rgba(255, 71, 87,' : 'rgba(136, 136, 160,';
            const fade = progress > 0.7 ? (1 - progress) / 0.3 : 1;

            // Glow line
            ctx.beginPath();
            ctx.moveTo(tailX, tailY);
            ctx.lineTo(headX, headY);
            const lineGrad = ctx.createLinearGradient(tailX, tailY, headX, headY);
            lineGrad.addColorStop(0, `${color}0)`);
            lineGrad.addColorStop(1, `${color}${fade * 0.9})`);
            ctx.strokeStyle = lineGrad;
            ctx.lineWidth = a.success ? 3 : 1.5;
            ctx.stroke();

            // Glow effect for successful hits
            if (a.success) {
                ctx.beginPath();
                ctx.moveTo(tailX, tailY);
                ctx.lineTo(headX, headY);
                ctx.strokeStyle = `rgba(255, 71, 87, ${fade * 0.3})`;
                ctx.lineWidth = 8;
                ctx.stroke();
            }

            // Arrowhead
            if (progress < 0.85) {
                const angle = Math.atan2(to.y - from.y, to.x - from.x);
                const headLen = a.success ? 12 : 8;
                ctx.beginPath();
                ctx.moveTo(headX, headY);
                ctx.lineTo(headX - headLen * Math.cos(angle - 0.4), headY - headLen * Math.sin(angle - 0.4));
                ctx.moveTo(headX, headY);
                ctx.lineTo(headX - headLen * Math.cos(angle + 0.4), headY - headLen * Math.sin(angle + 0.4));
                ctx.strokeStyle = `${color}${fade})`;
                ctx.lineWidth = 2;
                ctx.stroke();
            }

            // Impact flash
            if (a.success && progress > 0.85 && progress < 1) {
                const impactAlpha = (1 - (progress - 0.85) / 0.15) * 0.6;
                const impactR = (progress - 0.85) / 0.15 * 25;
                ctx.beginPath();
                ctx.arc(to.x, to.y, impactR, 0, Math.PI * 2);
                ctx.fillStyle = `rgba(255, 71, 87, ${impactAlpha})`;
                ctx.fill();
            }

            // Label
            if (a.name && progress > 0.2 && progress < 0.7) {
                const labelAlpha = progress < 0.3 ? (progress - 0.2) / 0.1 : (0.7 - progress) / 0.2;
                const midX = (from.x + to.x) / 2;
                const midY = (from.y + to.y) / 2 - 14;
                ctx.font = '500 11px Inter, Noto Sans SC, sans-serif';
                ctx.textAlign = 'center';
                ctx.fillStyle = `rgba(255,255,255,${labelAlpha * 0.8})`;
                ctx.fillText(a.name, midX, midY);
            }

            return progress < 1;
        });

        requestAnimationFrame(() => this.animate());
    }
}

// Global instance
let arena;
document.addEventListener('DOMContentLoaded', () => {
    arena = new ArenaRenderer();
});
