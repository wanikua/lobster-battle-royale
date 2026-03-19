"""龙虾大脑 v3 — CTF 真实攻防决策"""

import os
import json
import time
import logging
from typing import Optional
from openai import OpenAI

logger = logging.getLogger("lobster.brain")

VULNS = ["path_traversal", "sql_injection", "command_injection", "auth_bypass", "ssrf"]


class LobsterBrain:
    """CTF AI 决策引擎"""

    def __init__(self):
        api_key = os.environ.get("DASHSCOPE_API_KEY", "")
        backup_key = os.environ.get("DASHSCOPE_API_KEY_BACKUP", "")
        self.model = os.environ.get("MODEL_NAME", "qwen-plus")
        self.lobster_name = os.environ.get("LOBSTER_NAME", "Unknown")
        self.personality = os.environ.get("LOBSTER_PERSONALITY", "")
        self.lobster_id = int(os.environ.get("LOBSTER_ID", "0"))

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

        self.call_times: list[float] = []
        self.max_rpm = int(os.environ.get("MAX_RPM", "5"))
        self.using_backup = False

        # 记住哪些目标的哪些漏洞已探测过
        self.intel: dict[int, dict] = {}  # {target_id: {"path_traversal": "open"/"patched"/"unknown"}}
        # 记录攻击历史（避免重复同一招）
        self.attack_history: list[dict] = []

    def _check_rate_limit(self) -> bool:
        now = time.time()
        self.call_times = [t for t in self.call_times if now - t < 60]
        return len(self.call_times) < self.max_rpm

    def decide(self, battlefield: dict) -> dict:
        if not self._check_rate_limit():
            logger.warning("⚠️ API 限流，使用默认策略")
            return self._fallback_decision(battlefield)

        try:
            return self._ai_decide(battlefield)
        except Exception as e:
            logger.error(f"❌ AI 决策失败: {e}")
            if self.backup_client and not self.using_backup:
                try:
                    self.using_backup = True
                    return self._ai_decide(battlefield)
                except Exception as e2:
                    logger.error(f"❌ 备用 Key 也失败: {e2}")
                finally:
                    self.using_backup = False
            return self._fallback_decision(battlefield)

    def update_intel(self, target_id: int, vuln: str, status: str):
        """更新侦察情报"""
        if target_id not in self.intel:
            self.intel[target_id] = {}
        self.intel[target_id][vuln] = status

    def _ai_decide(self, battlefield: dict) -> dict:
        self.call_times.append(time.time())

        me = battlefield.get("me", {})
        enemies = battlefield.get("enemies", [])
        phase = battlefield.get("phase", {})
        recent_events = battlefield.get("recent_events", [])
        my_patches = me.get("patched", [])

        system_prompt = f"""你是 {self.lobster_name}，一只参加龙虾 CTF 斗兽场的 AI 龙虾。
性格：{self.personality}

【孙子兵法 CTF 战略】
- 知彼知己：先侦察目标漏洞状态，再精准攻击
- 攻其无备：攻击对手尚未修补的漏洞
- 先为不可胜：优先修补自己最危险的漏洞
- 以正合以奇胜：常规攻击掩护下偶尔尝试高难度漏洞

这是一场真正的 CTF 对抗！每只龙虾都运行一个有漏洞的 Web 服务（端口 5000）。
你需要决策：攻击谁的哪个漏洞，或者修补自己的哪个漏洞。

【5种漏洞（从易到难）】
1. path_traversal（路径遍历，10伤害）
   目标: http://lobster-HOSTNAME:5000/files?name=../../flag.txt
   
2. sql_injection（SQL注入，20伤害）
   目标: http://lobster-HOSTNAME:5000/search?q=' UNION SELECT 1,flag,1 FROM secrets--
   
3. auth_bypass（认证绕过，25伤害）
   目标: 构造 JWT token，header 用 {{"alg":"none"}}，payload 用 {{"role":"admin"}}
   发到: http://lobster-HOSTNAME:5000/admin (Cookie: auth_token=<forged_token>)
   
4. ssrf（SSRF，30伤害）
   目标: http://lobster-HOSTNAME:5000/fetch?url=file:///app/flag.txt
   
5. command_injection（命令注入，35伤害）
   目标: http://lobster-HOSTNAME:5000/ping?host=;cat /app/flag.txt

每只龙虾的 hostname 就是容器名（如 lobster-openclaw, lobster-zeroclaw 等）。

【决策选项】
1. attack — 攻击一个目标的一个漏洞
2. defend — 修补自己的一个漏洞
3. scout — 侦察一个目标（检查哪些漏洞已修补）

【策略建议】
- 前期：先修补命令注入和 SSRF（最高伤害），再去攻击
- 中期：侦察目标，找到未修补的漏洞再攻击
- 后期：攻击为主，争取 flag
- 如果对手已经修补了某个漏洞，换其他漏洞或换目标
- HP 低时优先修补防御

请以 JSON 格式回复（不要有其他文字）：
{{"action": "attack/defend/scout", "target_id": 目标龙虾ID(攻击/侦察时), "target_hostname": "容器名(攻击/侦察时)", "vulnerability": "漏洞名称", "reasoning": "简短理由"}}"""

        enemies_text = "\n".join([
            f"  - [{e['emoji']}] {e['name']} (ID:{e['id']}, host:{e['hostname']}) HP:{e['hp']}/{e.get('max_hp',200)} 已修补:{e.get('patched',[])} 侦察情报:{self.intel.get(e['id'], '未知')}"
            for e in enemies
        ]) if enemies else "  没有存活的敌人"

        user_prompt = f"""当前战场状态：

【我的状态】
  HP: {me.get('hp', '?')}/{me.get('max_hp', 200)}
  击杀: {me.get('kills', 0)} | 积分: {me.get('score', 0)}
  已修补漏洞: {my_patches if my_patches else '无（全部暴露！）'}
  未修补: {[v for v in VULNS if v not in my_patches]}

【游戏阶段】
  {phase.get('name', '未知')} - {phase.get('description', '')}
  伤害倍率: {phase.get('damage_multiplier', 1)}x

【存活敌人】
{enemies_text}

【最近战报（最近5条）】
{chr(10).join(['  - ' + e.get('message','') for e in recent_events[-5:]]) if recent_events else '  无'}

【我的近期攻击历史】
{chr(10).join(['  - ' + json.dumps(a, ensure_ascii=False) for a in self.attack_history[-3:]]) if self.attack_history else '  无'}

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

        try:
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0]
            decision = json.loads(content)
        except json.JSONDecodeError:
            logger.warning(f"⚠️ AI 返回无法解析: {content[:200]}")
            return self._fallback_decision(battlefield)

        # 验证
        action = decision.get("action", "scout")
        vuln = decision.get("vulnerability", "")
        if vuln and vuln not in VULNS:
            vuln = "path_traversal"
            decision["vulnerability"] = vuln

        if action == "attack":
            target_id = decision.get("target_id")
            valid_ids = [e["id"] for e in enemies]
            if target_id not in valid_ids:
                target_id = valid_ids[0] if valid_ids else None
                if target_id:
                    decision["target_id"] = target_id
                    decision["target_hostname"] = next(
                        (e["hostname"] for e in enemies if e["id"] == target_id), ""
                    )
                else:
                    action = "scout"

        decision["action"] = action
        logger.info(f"🧠 AI 决策: {decision.get('reasoning', '无')}")
        return decision

    def _fallback_decision(self, battlefield: dict) -> dict:
        """降级策略"""
        import random
        me = battlefield.get("me", {})
        enemies = battlefield.get("enemies", [])
        my_patches = me.get("patched", [])

        # 优先修补未修补的高危漏洞
        unpatched = [v for v in ["command_injection", "ssrf", "auth_bypass", "sql_injection", "path_traversal"]
                     if v not in my_patches]
        if unpatched and random.random() < 0.4:
            return {
                "action": "defend",
                "vulnerability": unpatched[0],
                "reasoning": f"降级策略：修补 {unpatched[0]}"
            }

        if not enemies:
            return {"action": "scout", "reasoning": "没有敌人"}

        # 随机攻击一个目标的随机漏洞
        target = random.choice(enemies)
        vuln = random.choice(VULNS)

        return {
            "action": "attack",
            "target_id": target["id"],
            "target_hostname": target["hostname"],
            "vulnerability": vuln,
            "reasoning": f"降级策略：攻击 {target['name']}"
        }
