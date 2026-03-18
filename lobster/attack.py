"""攻击模块 - 向裁判提交攻击请求"""

import logging
import httpx

logger = logging.getLogger("lobster.attack")


class AttackModule:
    """攻击模块"""

    def __init__(self, referee_url: str, lobster_id: int):
        self.referee_url = referee_url
        self.lobster_id = lobster_id
        self.client = httpx.AsyncClient(timeout=10)

    async def execute(self, target_id: int, attack_type: str) -> dict:
        """执行攻击"""
        try:
            resp = await self.client.post(
                f"{self.referee_url}/attack",
                json={
                    "attacker_id": self.lobster_id,
                    "target_id": target_id,
                    "attack_type": attack_type,
                }
            )
            result = resp.json()

            if result.get("ok"):
                if result.get("success"):
                    logger.info(f"⚔️ 攻击成功！{result.get('message', '')}")
                else:
                    logger.info(f"🛡️ 攻击未命中：{result.get('message', '')}")
            else:
                logger.warning(f"❌ 攻击失败：{result.get('message', '')}")

            return result
        except Exception as e:
            logger.error(f"❌ 攻击请求异常: {e}")
            return {"ok": False, "message": str(e)}

    async def close(self):
        await self.client.aclose()
