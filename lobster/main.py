"""龙虾主程序 - 生存循环"""

import os
import asyncio
import random
import logging
import httpx

from brain import LobsterBrain
from attack import AttackModule
from defense import DefenseModule
from heartbeat import HeartbeatModule

# 日志配置
lobster_name = os.environ.get("LOBSTER_NAME", "Unknown")
lobster_emoji = os.environ.get("LOBSTER_EMOJI", "🦞")
logging.basicConfig(
    level=logging.INFO,
    format=f"%(asctime)s [{lobster_emoji} {lobster_name}] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("lobster")


class Lobster:
    """龙虾 Agent"""

    def __init__(self):
        self.lobster_id = int(os.environ.get("LOBSTER_ID", "0"))
        self.name = os.environ.get("LOBSTER_NAME", "Unknown")
        self.emoji = os.environ.get("LOBSTER_EMOJI", "🦞")
        self.referee_url = os.environ.get("REFEREE_URL", "http://referee:8000")
        self.heartbeat_interval = int(os.environ.get("HEARTBEAT_INTERVAL", "10"))
        self.decision_min = int(os.environ.get("DECISION_MIN", "30"))
        self.decision_max = int(os.environ.get("DECISION_MAX", "60"))

        # 模块
        self.brain = LobsterBrain()
        self.attack_mod = AttackModule(self.referee_url, self.lobster_id)
        self.defense_mod = DefenseModule(self.referee_url, self.lobster_id)
        self.heartbeat_mod = HeartbeatModule(self.referee_url, self.lobster_id)

        self.alive = True

    async def run(self):
        """主循环"""
        logger.info(f"🦞 {self.emoji} {self.name} 上线了！准备战斗！")

        # 等待裁判服务启动
        await self._wait_for_referee()

        # 并行运行心跳和决策循环
        await asyncio.gather(
            self._heartbeat_loop(),
            self._decision_loop(),
        )

    async def _wait_for_referee(self):
        """等待裁判服务就绪"""
        client = httpx.AsyncClient(timeout=5)
        for attempt in range(60):
            try:
                resp = await client.get(f"{self.referee_url}/health")
                if resp.status_code == 200:
                    logger.info("✅ 裁判服务已就绪")
                    await client.aclose()
                    return
            except Exception:
                pass
            logger.info(f"⏳ 等待裁判服务... ({attempt + 1}/60)")
            await asyncio.sleep(2)

        await client.aclose()
        logger.error("❌ 裁判服务超时，但继续运行")

    async def _heartbeat_loop(self):
        """心跳循环"""
        while self.alive:
            result = await self.heartbeat_mod.ping()

            if not result.get("alive", True):
                self.alive = False
                logger.warning("💀 收到淘汰通知，游戏结束")
                break

            await asyncio.sleep(self.heartbeat_interval)

    async def _decision_loop(self):
        """决策循环"""
        # 初始等待，让所有龙虾启动
        await asyncio.sleep(random.randint(5, 15))

        while self.alive:
            try:
                await self._make_decision()
            except Exception as e:
                logger.error(f"❌ 决策异常: {e}")

            # 随机间隔
            interval = random.randint(self.decision_min, self.decision_max)
            await asyncio.sleep(interval)

    async def _make_decision(self):
        """做出一次决策并执行"""
        # 获取战场信息
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{self.referee_url}/battlefield/{self.lobster_id}")
                battlefield = resp.json()
        except Exception as e:
            logger.error(f"❌ 获取战场信息失败: {e}")
            return

        # AI 决策
        decision = self.brain.decide(battlefield)
        action = decision.get("action", "scout")

        if action == "attack":
            target_id = decision.get("target_id")
            attack_type = decision.get("attack_type", "port_hijack")
            if target_id:
                logger.info(f"⚔️ 决定攻击目标 {target_id}，方式: {attack_type}")
                logger.info(f"💭 理由: {decision.get('reasoning', '无')}")
                await self.attack_mod.execute(target_id, attack_type)

        elif action == "defend":
            defense_type = decision.get("defense_type", "port_guard")
            logger.info(f"🛡️ 切换防御: {defense_type}")
            logger.info(f"💭 理由: {decision.get('reasoning', '无')}")
            await self.defense_mod.set_defense(defense_type)

        elif action == "scout":
            logger.info(f"👀 侦察中...")
            logger.info(f"💭 理由: {decision.get('reasoning', '无')}")

    async def cleanup(self):
        """清理资源"""
        await self.attack_mod.close()
        await self.defense_mod.close()
        await self.heartbeat_mod.close()


async def main():
    lobster = Lobster()
    try:
        await lobster.run()
    finally:
        await lobster.cleanup()
        logger.info("👋 龙虾下线")


if __name__ == "__main__":
    asyncio.run(main())
