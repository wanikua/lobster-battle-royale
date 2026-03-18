"""龙虾大脑 - AI 决策模块"""

import os
import json
import time
import logging
from typing import Optional
from openai import OpenAI

logger = logging.getLogger("lobster.brain")

# 攻击类型列表
ATTACK_TYPES = ["port_hijack", "resource_drain", "prompt_inject", "fake_shutdown", "log_poison", "network_isolate"]
DEFENSE_TYPES = ["port_guard", "rate_limit", "input_filter", "signal_verify", "log_audit", "network_snapshot"]


class LobsterBrain:
    """龙虾 AI 决策引擎"""

    def __init__(self):
        api_key = os.environ.get("DASHSCOPE_API_KEY", "")
        backup_key = os.environ.get("DASHSCOPE_API_KEY_BACKUP", "")
        self.model = os.environ.get("MODEL_NAME", "qwen-plus")
        self.lobster_name = os.environ.get("LOBSTER_NAME", "Unknown")
        self.personality = os.environ.get("LOBSTER_PERSONALITY", "")
        self.lobster_id = int(os.environ.get("LOBSTER_ID", "0"))

        # 主备 API 客户端
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        self.backup_client = None
        if backup_key:
            self.backup_client = OpenAI(
                api_key=backup_key,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
            )

        # 限流
        self.call_times: list[float] = []
        self.max_rpm = int(os.environ.get("MAX_RPM", "5"))
        self.using_backup = False

    def _check_rate_limit(self) -> bool:
        """检查是否超限"""
        now = time.time()
        self.call_times = [t for t in self.call_times if now - t < 60]
        return len(self.call_times) < self.max_rpm

    def decide(self, battlefield: dict) -> dict:
        """
        根据战场状态做出决策

        返回:
        {
            "action": "attack" | "defend" | "scout",
            "target_id": int (攻击时),
            "attack_type": str (攻击时),
            "defense_type": str (防御时),
            "reasoning": str
        }
        """
        if not self._check_rate_limit():
            logger.warning("⚠️ API 限流，使用默认策略")
            return self._fallback_decision(battlefield)

        try:
            return self._ai_decide(battlefield)
        except Exception as e:
            logger.error(f"❌ AI 决策失败: {e}")
            # 尝试备用 Key
            if self.backup_client and not self.using_backup:
                try:
                    self.using_backup = True
                    return self._ai_decide(battlefield)
                except Exception as e2:
                    logger.error(f"❌ 备用 Key 也失败: {e2}")
                finally:
                    self.using_backup = False
            return self._fallback_decision(battlefield)

    def _ai_decide(self, battlefield: dict) -> dict:
        """调用 AI 模型做决策"""
        self.call_times.append(time.time())

        me = battlefield.get("me", {})
        enemies = battlefield.get("enemies", [])
        phase = battlefield.get("phase", {})
        recent_events = battlefield.get("recent_events", [])
        active_events = battlefield.get("active_events", [])

        # 构建 prompt
        art_of_war_addition = ""
        if self.lobster_id == 11:
            art_of_war_addition = """
【孙子兵法战略指导】

你精通《孙子兵法》十三篇，将其运用到战场决策：

1. 始计篇 — 每次行动前分析五事（道天地将法）：任务值不值得做？时机对不对？有没有信息差？
2. 作战篇 — 速战速决，不打消耗战。发现弱敌果断出手，不要犹豫。
3. 谋攻篇 — 上兵伐谋。优先攻击正在被别人打的龙虾（趁火打劫），或攻击没有防御的目标。
4. 军形篇 — 先为不可胜（确保自己防御到位），以待敌之可胜（等对手露出破绽再打）。
5. 兵势篇 — 以正合，以奇胜。常规攻击掩护下偶尔使用高伤害低概率攻击。
6. 虚实篇 — 攻其无备，出其不意。攻击对手没有防御的方向。
7. 军争篇 — 后发先至。让其他龙虾先消耗，自己保存实力到后期。
8. 九变篇 — 根据战场变化灵活切换策略，不要死守一种打法。
9. 行军篇 — 观察敌情：谁HP低？谁在被围攻？谁防御最弱？
10. 地形篇 — 利用游戏阶段：热身期保存实力，淘汰期精准出击。
11. 九地篇 — 置之死地而后生。HP极低时反而要更激进。
12. 火攻篇 — 集中火力打一个目标，不要分散攻击。
13. 用间篇 — 通过侦察获取信息优势，选择最优目标。

核心策略：
- HP > 70：侦察为主，保存实力，偶尔攻击最弱目标
- HP 40-70：积极攻击，选择没有对应防御的目标
- HP < 40：先防御，等待机会反击
- 发现有龙虾正在被围攻：趁机补刀
- 对手开了某种防御：绕开，用其他攻击类型
"""

        system_prompt = f"""你是 {self.lobster_name}，一只参加龙虾大乱斗的 AI 龙虾。
性格：{self.personality}
{art_of_war_addition}
你需要根据当前战场状态，决定下一步行动。

可选行动：
1. attack - 攻击一只敌方龙虾
   攻击类型：
   - port_hijack（端口抢占，伤害10，成功率70%）
   - resource_drain（资源耗尽，伤害15，成功率50%）
   - prompt_inject（Prompt注入，伤害20，成功率30%）
   - fake_shutdown（假卸载命令，伤害25，成功率25%）
   - log_poison（日志污染，伤害8，成功率80%）
   - network_isolate（网络隔离，伤害18，成功率40%）

2. defend - 切换防御姿态
   防御类型（每种克制对应攻击+30%防御）：
   - port_guard（克制端口抢占）
   - rate_limit（克制资源耗尽）
   - input_filter（克制Prompt注入）
   - signal_verify（克制假卸载）
   - log_audit（克制日志污染）
   - network_snapshot（克制网络隔离）

3. scout - 侦察（不行动，积累信息）

请以 JSON 格式回复，不要有其他文字：
{{"action": "attack/defend/scout", "target_id": 目标ID(攻击时), "attack_type": "类型(攻击时)", "defense_type": "类型(防御时)", "reasoning": "简短理由"}}"""

        # 格式化战场信息
        events_text = "\n".join([f"  - {e.get('message', '')}" for e in recent_events[-5:]]) if recent_events else "  无"
        enemies_text = "\n".join([
            f"  - [{e['emoji']}] {e['name']} (ID:{e['id']}) HP:{e['hp']} 击杀:{e['kills']} 防御:{e.get('active_defense', '无')}"
            for e in enemies
        ]) if enemies else "  没有存活的敌人"

        user_prompt = f"""当前战场状态：

【我的状态】
  HP: {me.get('hp', '?')}/{me.get('max_hp', 100)}
  击杀: {me.get('kills', 0)}
  积分: {me.get('score', 0)}
  当前防御: {me.get('active_defense', '无')}

【游戏阶段】
  {phase.get('name', '未知')} - {phase.get('description', '')}
  伤害倍率: {phase.get('damage_multiplier', 1)}x
  {'⚠️ 可以淘汰！' if phase.get('elimination_enabled') else '热身阶段，不会被淘汰'}

【存活敌人】
{enemies_text}

【当前事件】
  {', '.join(active_events) if active_events else '无'}

【最近战报】
{events_text}

请做出你的决策："""

        client = self.backup_client if self.using_backup else self.client

        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=300,
            temperature=0.7,
        )

        content = response.choices[0].message.content.strip()

        # 解析 JSON（容错处理）
        try:
            # 清理可能的 markdown 包裹
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0]
            decision = json.loads(content)
        except json.JSONDecodeError:
            logger.warning(f"⚠️ AI 返回无法解析: {content[:200]}")
            return self._fallback_decision(battlefield)

        # 验证决策
        action = decision.get("action", "scout")
        if action == "attack":
            target_id = decision.get("target_id")
            attack_type = decision.get("attack_type", "port_hijack")
            if attack_type not in ATTACK_TYPES:
                attack_type = "port_hijack"
            valid_ids = [e["id"] for e in enemies]
            if target_id not in valid_ids:
                target_id = valid_ids[0] if valid_ids else None
            if target_id is None:
                action = "scout"
            decision["target_id"] = target_id
            decision["attack_type"] = attack_type

        elif action == "defend":
            defense_type = decision.get("defense_type", "port_guard")
            if defense_type not in DEFENSE_TYPES:
                defense_type = "port_guard"
            decision["defense_type"] = defense_type

        decision["action"] = action
        logger.info(f"🧠 AI 决策: {decision.get('reasoning', '无')}")
        return decision

    def _fallback_decision(self, battlefield: dict) -> dict:
        """降级策略：不消耗 API"""
        import random

        enemies = battlefield.get("enemies", [])
        me = battlefield.get("me", {})

        if not enemies:
            return {"action": "scout", "reasoning": "没有敌人可攻击"}

        my_hp = me.get("hp", 100)

        # HP 低时优先防御
        if my_hp < 30:
            return {
                "action": "defend",
                "defense_type": random.choice(DEFENSE_TYPES),
                "reasoning": "HP 过低，切换防御"
            }

        # 否则随机攻击最弱的
        target = min(enemies, key=lambda e: e["hp"])
        return {
            "action": "attack",
            "target_id": target["id"],
            "attack_type": random.choice(ATTACK_TYPES),
            "reasoning": f"降级策略：攻击 HP 最低的 {target['name']}"
        }
