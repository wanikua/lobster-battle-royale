"""游戏引擎 v3 — CTF 真实攻防"""

import json
import time
import random
import asyncio
import hashlib
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

from event_log import EventLog

logger = logging.getLogger("referee.engine")

# 漏洞伤害表
VULN_DAMAGE = {
    "path_traversal": 10,
    "sql_injection": 20,
    "auth_bypass": 25,
    "ssrf": 30,
    "command_injection": 35,
}


@dataclass
class LobsterState:
    id: int
    name: str
    emoji: str
    origin: str
    personality: str
    catchphrase: str
    model: str
    hostname: str = ""
    hp: int = 200
    max_hp: int = 200
    alive: bool = True
    kills: int = 0
    score: int = 0
    last_heartbeat: float = 0
    eliminated_at: Optional[float] = None
    eliminated_by: Optional[int] = None
    current_flag: str = ""
    flag_captures: int = 0  # 被别人拿走几次 flag
    flags_stolen: int = 0   # 偷了几面 flag
    patched: list = field(default_factory=list)  # 已修补的漏洞
    service_up: bool = True
    service_down_since: Optional[float] = None
    health_failures: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "emoji": self.emoji,
            "origin": self.origin,
            "hp": self.hp,
            "max_hp": self.max_hp,
            "alive": self.alive,
            "kills": self.kills,
            "score": self.score,
            "last_heartbeat": self.last_heartbeat,
            "catchphrase": self.catchphrase,
            "hostname": self.hostname,
            "flags_stolen": self.flags_stolen,
            "flag_captures": self.flag_captures,
            "patched": self.patched,
            "service_up": self.service_up,
        }


class GameEngine:
    def __init__(self):
        rules_path = Path("/app/config/game_rules.json")
        lobsters_path = Path("/app/config/lobsters.json")

        with open(rules_path, "r", encoding="utf-8") as f:
            self.rules = json.load(f)
        with open(lobsters_path, "r", encoding="utf-8") as f:
            self.lobster_configs = json.load(f)

        self.event_log = EventLog()
        self.lobsters: dict[int, LobsterState] = {}
        self.game_started = False
        self.game_paused = False
        self.start_time: Optional[float] = None
        self.current_phase = "skirmish"
        self.phase_order = ["skirmish", "midgame", "bloodmoon", "final"]
        self.active_events: list[dict] = []

        # Flag 系统
        self.flag_rotation_interval = 300  # 5分钟轮换
        self.last_flag_rotation: float = 0
        self.submitted_flags: set = set()  # (attacker_id, target_id, flag) 防止重复提交
        self.referee_secret = "lobster-referee-key"

        # 毒圈
        self.last_poison_tick: float = 0

        # 随机事件
        self.last_random_event: float = 0

        self._init_lobsters()

    def _init_lobsters(self):
        initial_hp = self.rules.get("initial_hp", 200)
        for cfg in self.lobster_configs:
            self.lobsters[cfg["id"]] = LobsterState(
                id=cfg["id"],
                name=cfg["name"],
                emoji=cfg["emoji"],
                origin=cfg["origin"],
                personality=cfg["personality"],
                catchphrase=cfg["catchphrase"],
                model=cfg["model"],
                hostname=cfg.get("hostname", f"lobster-{cfg['name'].lower().replace(' ', '')}"),
                hp=initial_hp,
                max_hp=initial_hp,
            )

    def _generate_flag(self, lobster_id: int) -> str:
        ts = int(time.time())
        raw = f"lobster-{lobster_id}-{ts}-{random.randint(0, 99999)}"
        h = hashlib.sha256(raw.encode()).hexdigest()[:16]
        return f"FLAG{{{h}}}"

    def start_game(self) -> dict:
        if self.game_started:
            return {"ok": False, "message": "游戏已经开始了"}

        self.game_started = True
        self.game_paused = False
        self.start_time = time.time()
        self.current_phase = "skirmish"
        self.last_random_event = time.time()

        # 初始化 flag
        self.rotate_flags()

        self.event_log.add(
            "phase_change",
            message="🏴‍☠️ 龙虾 CTF 斗兽场开战！真实攻防，真刀真枪！"
        )

        return {"ok": True, "message": "🦞 龙虾 CTF 斗兽场开战！"}

    def rotate_flags(self):
        """轮换所有龙虾的 flag"""
        for lobster in self.lobsters.values():
            if lobster.alive:
                lobster.current_flag = self._generate_flag(lobster.id)
        self.submitted_flags.clear()
        self.last_flag_rotation = time.time()
        logger.info("🔄 Flag 已轮换")

    def get_current_phase(self) -> dict:
        if not self.start_time:
            return self.rules["phases"]["skirmish"]

        elapsed_hours = (time.time() - self.start_time) / 3600
        cumulative = 0

        for phase_key in self.phase_order:
            phase = self.rules["phases"][phase_key]
            cumulative += phase["duration_hours"]
            if elapsed_hours < cumulative:
                if self.current_phase != phase_key:
                    old_phase = self.current_phase
                    self.current_phase = phase_key
                    self.event_log.add(
                        "phase_change",
                        message=f"⚡ 阶段变更：{self.rules['phases'][old_phase]['name']} → {phase['name']}！{phase['description']}"
                    )
                    # 调整 flag 轮换间隔
                    if phase_key == "bloodmoon":
                        self.flag_rotation_interval = 180
                    elif phase_key == "final":
                        self.flag_rotation_interval = 120
                return phase

        return self.rules["phases"]["final"]

    def _tick_poison(self):
        phase = self.get_current_phase()
        poison = phase.get("poison_tick", 0)
        if poison <= 0:
            return
        now = time.time()
        if now - self.last_poison_tick < 30:
            return
        self.last_poison_tick = now
        
        for lobster in self.lobsters.values():
            if lobster.alive:
                lobster.hp -= poison
                if lobster.hp <= 0:
                    lobster.hp = 0
                    lobster.alive = False
                    lobster.eliminated_at = now
                    self.event_log.add(
                        "elimination", target_id=lobster.id,
                        message=f"☠️ {lobster.emoji} {lobster.name} 被毒圈吞噬！"
                    )
        
        alive_count = sum(1 for l in self.lobsters.values() if l.alive)
        self.event_log.add(
            "system",
            message=f"☣️ 毒圈侵蚀！全员 -{poison} HP（存活: {alive_count}）"
        )

    def _maybe_rotate_flags(self):
        now = time.time()
        if now - self.last_flag_rotation >= self.flag_rotation_interval:
            self.rotate_flags()
            self.event_log.add(
                "system",
                message=f"🔄 Flag 轮换！所有 flag 已更新"
            )

    def _maybe_random_event(self):
        interval = self.rules.get("random_event_interval_sec", 120)
        phase = self.get_current_phase()
        if phase.get("random_event_freq"):
            interval = int(interval / phase["random_event_freq"])
        now = time.time()
        if now - self.last_random_event < interval:
            return
        self.last_random_event = now
        self.trigger_random_event()

    def pause_game(self) -> dict:
        self.game_paused = not self.game_paused
        status = "暂停" if self.game_paused else "继续"
        self.event_log.add("system", message=f"⏸️ 游戏{status}")
        return {"ok": True, "paused": self.game_paused}

    def heartbeat(self, lobster_id: int) -> dict:
        if lobster_id not in self.lobsters:
            return {"ok": False, "message": "未知龙虾"}

        lobster = self.lobsters[lobster_id]
        if not lobster.alive:
            return {"ok": False, "message": "你已经被淘汰了", "alive": False}

        lobster.last_heartbeat = time.time()

        if self.game_started and not self.game_paused:
            lobster.score += self.rules.get("survival_points_per_min", 1)
            self._tick_poison()
            self._maybe_rotate_flags()
            self._maybe_random_event()

        return {
            "ok": True,
            "alive": True,
            "hp": lobster.hp,
            "score": lobster.score,
            "phase": self.current_phase,
            "game_started": self.game_started,
            "active_events": [e["name"] for e in self.active_events],
        }

    def submit_flag(self, attacker_id: int, target_id: int, flag: str, vulnerability: str) -> dict:
        """提交 flag — CTF 的核心判定"""
        if not self.game_started or self.game_paused:
            return {"ok": False, "message": "游戏未开始或暂停中"}

        attacker = self.lobsters.get(attacker_id)
        target = self.lobsters.get(target_id)

        if not attacker or not target:
            return {"ok": False, "message": "无效的龙虾 ID"}
        if not attacker.alive:
            return {"ok": False, "message": "你已被淘汰"}
        if not target.alive:
            return {"ok": False, "message": "目标已被淘汰"}
        if attacker_id == target_id:
            return {"ok": False, "message": "不能攻击自己"}

        # 检查 flag 是否正确
        if flag != target.current_flag:
            self.event_log.add(
                "attack",
                source_id=attacker_id,
                target_id=target_id,
                message=f"🚫 {attacker.emoji} {attacker.name} 提交了错误的 flag（{vulnerability}）"
            )
            return {"ok": False, "message": "Flag 错误或已过期"}

        # 检查是否已提交过
        submit_key = (attacker_id, target_id, flag)
        if submit_key in self.submitted_flags:
            return {"ok": False, "message": "这个 flag 已经提交过了"}
        self.submitted_flags.add(submit_key)

        # 计算伤害
        phase = self.get_current_phase()
        multiplier = phase.get("damage_multiplier", 1.0)
        base_damage = VULN_DAMAGE.get(vulnerability, 10)
        damage = int(base_damage * multiplier)

        # 扣血
        target.hp -= damage
        target.hp = max(0, target.hp)
        target.flag_captures += 1
        attacker.flags_stolen += 1

        # 积分
        points = self.rules.get("kill_points", 15)
        double_points = any(e.get("effect") == "double_points" for e in self.active_events)
        if double_points:
            points *= 2
        # 首杀奖励
        first_blood = len([k for k in self.submitted_flags if k[2] == flag]) <= 1
        if first_blood:
            points += 5
        attacker.score += points

        vuln_name = {
            "path_traversal": "路径遍历",
            "sql_injection": "SQL注入",
            "command_injection": "命令注入",
            "auth_bypass": "认证绕过",
            "ssrf": "SSRF",
        }.get(vulnerability, vulnerability)

        self.event_log.add(
            "attack",
            source_id=attacker_id,
            target_id=target_id,
            detail={"vulnerability": vulnerability, "damage": damage, "first_blood": first_blood},
            message=f"🏴‍☠️ {attacker.emoji} {attacker.name} 通过{vuln_name}攻破 {target.emoji} {target.name}！-{damage} HP{'（首杀！+5分）' if first_blood else ''}"
        )

        # 检查淘汰
        if target.hp <= 0 and phase.get("elimination_enabled", True):
            target.alive = False
            target.eliminated_at = time.time()
            target.eliminated_by = attacker_id
            attacker.kills += 1
            attacker.score += 10  # 淘汰额外奖励

            self.event_log.add(
                "elimination",
                source_id=attacker_id,
                target_id=target_id,
                message=f"💀 {target.emoji} {target.name} 被 {attacker.emoji} {attacker.name} 淘汰！「{target.catchphrase}」成为遗言..."
            )

            alive_count = sum(1 for l in self.lobsters.values() if l.alive)
            if alive_count <= 1:
                winner = next((l for l in self.lobsters.values() if l.alive), None)
                if winner:
                    self.event_log.add(
                        "game_over",
                        source_id=winner.id,
                        message=f"🏆 {winner.emoji} {winner.name} 获得最终胜利！「{winner.catchphrase}」"
                    )

        return {
            "ok": True,
            "damage": damage,
            "first_blood": first_blood,
            "target_hp": target.hp,
            "target_alive": target.alive,
            "message": f"攻击成功！{vuln_name} 造成 {damage} 伤害"
        }

    def attack_failed(self, attacker_id: int, target_id: int, vulnerability: str, reason: str) -> dict:
        """记录攻击失败"""
        attacker = self.lobsters.get(attacker_id)
        target = self.lobsters.get(target_id)
        if not attacker or not target:
            return {"ok": False}
        
        vuln_name = {
            "path_traversal": "路径遍历",
            "sql_injection": "SQL注入",
            "command_injection": "命令注入",
            "auth_bypass": "认证绕过",
            "ssrf": "SSRF",
        }.get(vulnerability, vulnerability)

        short_reason = "已修补" if "patched" in reason.lower() or "403" in reason or "400" in reason else "未命中"

        self.event_log.add(
            "attack",
            source_id=attacker_id,
            target_id=target_id,
            message=f"🛡️ {attacker.emoji} {attacker.name} 尝试{vuln_name}攻击 {target.emoji} {target.name}，{short_reason}！"
        )
        return {"ok": True}

    def record_defense(self, lobster_id: int, vulnerability: str) -> dict:
        """记录防御"""
        lobster = self.lobsters.get(lobster_id)
        if not lobster:
            return {"ok": False}

        if vulnerability not in lobster.patched:
            lobster.patched.append(vulnerability)
        
        vuln_name = {
            "path_traversal": "路径遍历",
            "sql_injection": "SQL注入",
            "command_injection": "命令注入",
            "auth_bypass": "认证绕过",
            "ssrf": "SSRF",
        }.get(vulnerability, vulnerability)

        self.event_log.add(
            "defense",
            source_id=lobster_id,
            message=f"🔧 {lobster.emoji} {lobster.name} 修补了{vuln_name}漏洞！"
        )
        return {"ok": True}

    def trigger_random_event(self) -> dict:
        events = self.rules.get("random_events", [])
        if not events:
            return {"ok": False}
        event = random.choice(events)
        event_instance = {**event, "start_time": time.time()}
        alive_lobsters = [l for l in self.lobsters.values() if l.alive]

        if event["effect"] == "heal_all":
            for l in alive_lobsters:
                l.hp = min(l.max_hp, l.hp + event.get("heal_amount", 25))

        elif event["effect"] == "random_damage":
            targets = random.sample(alive_lobsters, min(event.get("targets", 3), len(alive_lobsters)))
            dmg = event.get("damage", 20)
            names = [f"{t.emoji}{t.name}" for t in targets]
            for t in targets:
                t.hp = max(0, t.hp - dmg)
                phase = self.get_current_phase()
                if t.hp <= 0 and phase.get("elimination_enabled", True):
                    t.alive = False
                    t.eliminated_at = time.time()
                    self.event_log.add("elimination", target_id=t.id,
                                       message=f"⚡ {t.emoji} {t.name} 被雷暴劈死！")
            event_instance["_extra"] = f"被劈: {', '.join(names)}"

        elif event["effect"] == "random_heal":
            targets = random.sample(alive_lobsters, min(event.get("targets", 3), len(alive_lobsters)))
            heal = event.get("heal_amount", 40)
            for t in targets:
                t.hp = min(t.max_hp, t.hp + heal)
            names = [f"{t.emoji}{t.name}" for t in targets]
            event_instance["_extra"] = f"幸运儿: {', '.join(names)}"

        elif event["effect"] == "strip_patch":
            # 随机移除一只龙虾的一个补丁！
            candidates = [l for l in alive_lobsters if l.patched]
            if candidates:
                target = random.choice(candidates)
                vuln = random.choice(target.patched)
                target.patched.remove(vuln)
                event_instance["_extra"] = f"💥 {target.emoji}{target.name} 的 {vuln} 补丁被撕掉了！"

        elif event["effect"] == "shuffle_patches":
            # 打乱所有龙虾的补丁！
            all_patches = [l.patched[:] for l in alive_lobsters]
            random.shuffle(all_patches)
            for i, l in enumerate(alive_lobsters):
                l.patched = all_patches[i]
            event_instance["_extra"] = "所有龙虾的补丁被随机打乱！"

        self.active_events.append(event_instance)

        extra = event_instance.get("_extra", "")
        msg = f"🎲 随机事件：{event['name']}！{event['description']}"
        if extra:
            msg += f" {extra}"
        self.event_log.add("random_event", detail=event, message=msg)

        duration = event.get("duration_sec", 30)
        if duration > 0:
            try:
                asyncio.get_event_loop().call_later(duration, self._clear_event, event_instance)
            except:
                pass

        return {"ok": True, "event": event}

    def _clear_event(self, event_instance: dict):
        if event_instance in self.active_events:
            self.active_events.remove(event_instance)

    def get_status(self) -> dict:
        phase = self.get_current_phase()
        ranking = sorted(self.lobsters.values(), key=lambda l: l.score, reverse=True)
        elapsed = int(time.time() - self.start_time) if self.start_time else 0

        return {
            "game_started": self.game_started,
            "game_paused": self.game_paused,
            "phase": phase,
            "phase_key": self.current_phase,
            "elapsed_seconds": elapsed,
            "elapsed_hours": round(elapsed / 3600, 1),
            "alive_count": sum(1 for l in self.lobsters.values() if l.alive),
            "total_count": len(self.lobsters),
            "lobsters": [l.to_dict() for l in self.lobsters.values()],
            "ranking": [{"rank": i + 1, "id": l.id, "name": l.name, "emoji": l.emoji,
                         "score": l.score, "kills": l.kills, "alive": l.alive,
                         "flags_stolen": l.flags_stolen, "patched": len(l.patched)}
                        for i, l in enumerate(ranking)],
            "active_events": [{"name": e["name"], "description": e["description"]} for e in self.active_events],
            "recent_events": self.event_log.get_recent(20),
            "flag_rotation_interval": self.flag_rotation_interval,
            "next_flag_rotation": max(0, int(self.flag_rotation_interval - (time.time() - self.last_flag_rotation))),
        }

    def get_battlefield(self, lobster_id: int) -> dict:
        me = self.lobsters.get(lobster_id)
        if not me:
            return {}

        enemies = []
        for l in self.lobsters.values():
            if l.id != lobster_id and l.alive:
                enemies.append({
                    "id": l.id,
                    "name": l.name,
                    "emoji": l.emoji,
                    "hp": l.hp,
                    "max_hp": l.max_hp,
                    "kills": l.kills,
                    "hostname": l.hostname,
                    "patched": l.patched,
                    "flags_stolen": l.flags_stolen,
                })

        return {
            "me": me.to_dict(),
            "enemies": enemies,
            "phase": self.get_current_phase(),
            "active_events": [e["name"] for e in self.active_events],
            "recent_events": self.event_log.get_recent(10),
        }
