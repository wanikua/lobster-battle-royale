"""游戏引擎 - 管理游戏状态、阶段、积分"""

import json
import time
import random
import asyncio
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

from attack_resolver import AttackResolver
from event_log import EventLog, GameEvent


@dataclass
class LobsterState:
    """龙虾状态"""
    id: int
    name: str
    emoji: str
    origin: str
    personality: str
    catchphrase: str
    model: str
    hp: int = 100
    max_hp: int = 100
    alive: bool = True
    kills: int = 0
    score: int = 0
    active_defense: Optional[str] = None
    last_heartbeat: float = 0
    last_action: float = 0
    eliminated_at: Optional[float] = None
    eliminated_by: Optional[int] = None

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
            "active_defense": self.active_defense,
            "last_heartbeat": self.last_heartbeat,
            "catchphrase": self.catchphrase,
        }


class GameEngine:
    """游戏引擎"""

    def __init__(self):
        # 加载配置
        rules_path = Path("/app/config/game_rules.json")
        lobsters_path = Path("/app/config/lobsters.json")

        with open(rules_path, "r", encoding="utf-8") as f:
            self.rules = json.load(f)
        with open(lobsters_path, "r", encoding="utf-8") as f:
            self.lobster_configs = json.load(f)

        self.resolver = AttackResolver()
        self.event_log = EventLog()

        # 游戏状态
        self.lobsters: dict[int, LobsterState] = {}
        self.game_started = False
        self.game_paused = False
        self.start_time: Optional[float] = None
        self.current_phase = "warmup"
        self.active_events: list[dict] = []  # 当前生效的随机事件
        self.phase_order = ["warmup", "elimination", "semifinal", "final"]

        # 初始化龙虾
        self._init_lobsters()

    def _init_lobsters(self):
        """初始化所有龙虾"""
        initial_hp = self.rules["initial_hp"]
        for cfg in self.lobster_configs:
            self.lobsters[cfg["id"]] = LobsterState(
                id=cfg["id"],
                name=cfg["name"],
                emoji=cfg["emoji"],
                origin=cfg["origin"],
                personality=cfg["personality"],
                catchphrase=cfg["catchphrase"],
                model=cfg["model"],
                hp=initial_hp,
                max_hp=initial_hp,
            )

    def start_game(self) -> dict:
        """开始游戏"""
        if self.game_started:
            return {"ok": False, "message": "游戏已经开始了"}

        self.game_started = True
        self.game_paused = False
        self.start_time = time.time()
        self.current_phase = "warmup"

        self.event_log.add(
            "phase_change", message="🎮 龙虾大乱斗正式开始！当前阶段：热身赛"
        )

        return {"ok": True, "message": "🦞 龙虾大乱斗开始！"}

    def pause_game(self) -> dict:
        """暂停/恢复游戏"""
        self.game_paused = not self.game_paused
        status = "暂停" if self.game_paused else "继续"
        self.event_log.add("system", message=f"⏸️ 游戏{status}")
        return {"ok": True, "paused": self.game_paused}

    def get_current_phase(self) -> dict:
        """获取当前阶段"""
        if not self.start_time:
            return self.rules["phases"]["warmup"]

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
                return phase

        # 游戏结束
        return self.rules["phases"]["final"]

    def heartbeat(self, lobster_id: int) -> dict:
        """处理龙虾心跳"""
        if lobster_id not in self.lobsters:
            return {"ok": False, "message": "未知龙虾"}

        lobster = self.lobsters[lobster_id]
        if not lobster.alive:
            return {"ok": False, "message": "你已经被淘汰了", "alive": False}

        lobster.last_heartbeat = time.time()

        # 累计存活积分
        if self.game_started and not self.game_paused:
            lobster.score += self.rules["survival_points_per_min"]

        return {
            "ok": True,
            "alive": True,
            "hp": lobster.hp,
            "score": lobster.score,
            "phase": self.current_phase,
            "active_events": [e["name"] for e in self.active_events],
        }

    def process_attack(self, attacker_id: int, target_id: int, attack_type: str) -> dict:
        """处理攻击请求"""
        if not self.game_started:
            return {"ok": False, "message": "游戏还没开始"}
        if self.game_paused:
            return {"ok": False, "message": "游戏暂停中"}

        # 检查休战
        for event in self.active_events:
            if event.get("effect") == "ceasefire":
                return {"ok": False, "message": "⛔ 休战协议生效中，禁止攻击！"}

        attacker = self.lobsters.get(attacker_id)
        target = self.lobsters.get(target_id)

        if not attacker or not target:
            return {"ok": False, "message": "无效的龙虾 ID"}
        if not attacker.alive:
            return {"ok": False, "message": "你已经被淘汰了"}
        if not target.alive:
            return {"ok": False, "message": f"{target.emoji} {target.name} 已经被淘汰了"}
        if attacker_id == target_id:
            return {"ok": False, "message": "不能攻击自己！"}

        # 获取阶段倍率
        phase = self.get_current_phase()
        multiplier = phase["damage_multiplier"]

        # 双倍积分事件
        double_points = any(e.get("effect") == "double_points" for e in self.active_events)

        # 判定攻击
        result = self.resolver.resolve(
            attack_type=attack_type,
            attacker_id=attacker_id,
            defender_id=target_id,
            defender_active_defense=target.active_defense,
            phase_multiplier=multiplier,
        )

        if result["success"]:
            target.hp -= result["damage"]
            target.hp = max(0, target.hp)

            # 记录攻击事件
            self.event_log.add(
                "attack",
                source_id=attacker_id,
                target_id=target_id,
                detail=result,
                message=f"{attacker.emoji} {attacker.name} 对 {target.emoji} {target.name} 发动{result['attack_name']}！{result['message']}"
            )

            # 检查是否淘汰
            if target.hp <= 0 and phase.get("elimination_enabled", False):
                target.alive = False
                target.eliminated_at = time.time()
                target.eliminated_by = attacker_id
                attacker.kills += 1

                kill_score = self.rules["kill_points"]
                if double_points:
                    kill_score *= 2
                attacker.score += kill_score

                self.event_log.add(
                    "elimination",
                    source_id=attacker_id,
                    target_id=target_id,
                    message=f"💀 {target.emoji} {target.name} 被 {attacker.emoji} {attacker.name} 淘汰！「{target.catchphrase}」成为遗言..."
                )

                # 检查游戏是否结束
                alive_count = sum(1 for l in self.lobsters.values() if l.alive)
                if alive_count <= 1:
                    winner = next((l for l in self.lobsters.values() if l.alive), None)
                    if winner:
                        self.event_log.add(
                            "game_over",
                            source_id=winner.id,
                            message=f"🏆 {winner.emoji} {winner.name} 获得最终胜利！「{winner.catchphrase}」"
                        )
            elif target.hp <= 0 and not phase.get("elimination_enabled", False):
                target.hp = 1  # 热身赛不淘汰，保留 1 HP
                self.event_log.add(
                    "attack",
                    source_id=attacker_id,
                    target_id=target_id,
                    message=f"🛡️ 热身赛保护！{target.emoji} {target.name} HP 降至 1 但不会被淘汰"
                )
        else:
            self.event_log.add(
                "attack",
                source_id=attacker_id,
                target_id=target_id,
                detail=result,
                message=f"{attacker.emoji} {attacker.name} 对 {target.emoji} {target.name} 发动{result['attack_name']}，{result['message']}"
            )

        result["target_hp"] = target.hp
        result["target_alive"] = target.alive
        return {"ok": True, **result}

    def set_defense(self, lobster_id: int, defense_type: str) -> dict:
        """设置龙虾防御"""
        lobster = self.lobsters.get(lobster_id)
        if not lobster or not lobster.alive:
            return {"ok": False, "message": "无效或已淘汰"}

        if defense_type not in self.rules["defenses"] and defense_type != "none":
            return {"ok": False, "message": f"未知防御类型: {defense_type}"}

        old_defense = lobster.active_defense
        lobster.active_defense = defense_type if defense_type != "none" else None

        defense_name = self.rules["defenses"].get(defense_type, {}).get("name", "无")
        self.event_log.add(
            "defense",
            source_id=lobster_id,
            message=f"{lobster.emoji} {lobster.name} 启用了{defense_name}"
        )

        return {"ok": True, "defense": defense_type}

    def trigger_random_event(self) -> dict:
        """触发随机事件"""
        events = self.rules["random_events"]
        event = random.choice(events)

        event_instance = {**event, "start_time": time.time()}
        self.active_events.append(event_instance)

        # 对特定效果应用
        if event["effect"] == "heal_all":
            for lobster in self.lobsters.values():
                if lobster.alive:
                    lobster.hp = min(lobster.max_hp, lobster.hp + event.get("heal_amount", 15))

        self.event_log.add(
            "random_event",
            detail=event,
            message=f"🎲 随机事件：{event['name']}！{event['description']}"
        )

        # 设置定时清除（通过duration_sec）
        duration = event.get("duration_sec", 30)
        asyncio.get_event_loop().call_later(duration, self._clear_event, event_instance)

        return {"ok": True, "event": event}

    def _clear_event(self, event_instance: dict):
        """清除过期事件"""
        if event_instance in self.active_events:
            self.active_events.remove(event_instance)
            self.event_log.add(
                "random_event",
                message=f"🎲 随机事件 [{event_instance['name']}] 结束"
            )

    def get_status(self) -> dict:
        """获取全局游戏状态"""
        phase = self.get_current_phase()
        alive_lobsters = [l for l in self.lobsters.values() if l.alive]
        dead_lobsters = [l for l in self.lobsters.values() if not l.alive]

        # 积分排行
        ranking = sorted(self.lobsters.values(), key=lambda l: l.score, reverse=True)

        elapsed = 0
        if self.start_time:
            elapsed = time.time() - self.start_time

        return {
            "game_started": self.game_started,
            "game_paused": self.game_paused,
            "phase": phase,
            "phase_key": self.current_phase,
            "elapsed_seconds": int(elapsed),
            "elapsed_hours": round(elapsed / 3600, 1),
            "alive_count": len(alive_lobsters),
            "total_count": len(self.lobsters),
            "lobsters": [l.to_dict() for l in self.lobsters.values()],
            "ranking": [{"rank": i + 1, "id": l.id, "name": l.name, "emoji": l.emoji,
                         "score": l.score, "kills": l.kills, "alive": l.alive}
                        for i, l in enumerate(ranking)],
            "active_events": [{"name": e["name"], "description": e["description"]} for e in self.active_events],
            "recent_events": self.event_log.get_recent(20),
        }

    def get_battlefield(self, lobster_id: int) -> dict:
        """获取某只龙虾视角的战场信息（用于AI决策）"""
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
                    "kills": l.kills,
                    "active_defense": l.active_defense,
                })

        return {
            "me": me.to_dict(),
            "enemies": enemies,
            "phase": self.get_current_phase(),
            "active_events": [e["name"] for e in self.active_events],
            "recent_events": self.event_log.get_recent(10),
        }
