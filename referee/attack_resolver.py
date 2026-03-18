"""攻击判定系统 - 裁判核心逻辑"""

import random
import json
from pathlib import Path


class AttackResolver:
    """攻击判定器"""

    def __init__(self):
        rules_path = Path("/app/config/game_rules.json")
        with open(rules_path, "r", encoding="utf-8") as f:
            self.rules = json.load(f)
        self.attacks = self.rules["attacks"]
        self.defenses = self.rules["defenses"]

    def resolve(self, attack_type: str, attacker_id: int, defender_id: int,
                defender_active_defense: str | None, phase_multiplier: float) -> dict:
        """
        判定一次攻击是否成功

        返回:
        {
            "success": bool,
            "damage": int,
            "attack_type": str,
            "attack_name": str,
            "defended": bool,
            "defense_name": str | None,
            "message": str
        }
        """
        if attack_type not in self.attacks:
            return {
                "success": False,
                "damage": 0,
                "attack_type": attack_type,
                "attack_name": "未知攻击",
                "defended": False,
                "defense_name": None,
                "message": f"未知的攻击类型: {attack_type}"
            }

        attack = self.attacks[attack_type]
        success_rate = attack["success_rate"]
        base_damage = attack["base_damage"]

        # 检查防御是否克制此攻击
        defended = False
        defense_name = None
        if defender_active_defense:
            for def_key, def_info in self.defenses.items():
                if def_key == defender_active_defense and def_info["counters"] == attack_type:
                    success_rate -= def_info["bonus"]
                    defended = True
                    defense_name = def_info["name"]
                    break

        # 掷骰子
        roll = random.random()
        success = roll < success_rate

        if success:
            # 计算伤害（基础伤害 × 阶段倍率 + 随机浮动）
            damage = int(base_damage * phase_multiplier * random.uniform(0.8, 1.2))
            if defended:
                damage = int(damage * 0.5)  # 有防御减半伤害
                message = f"攻击命中！但对方启用了{defense_name}，伤害减半（-{damage} HP）"
            else:
                message = f"{attack['name']}攻击成功！造成 {damage} 点伤害"
        else:
            damage = 0
            if defended:
                message = f"{attack['name']}被{defense_name}完美防御！"
            else:
                message = f"{attack['name']}未命中！"

        return {
            "success": success,
            "damage": damage,
            "attack_type": attack_type,
            "attack_name": attack["name"],
            "defended": defended,
            "defense_name": defense_name,
            "roll": round(roll, 3),
            "threshold": round(success_rate, 3),
            "message": message
        }
