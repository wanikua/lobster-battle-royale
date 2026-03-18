"""防御模块 - 设置防御姿态"""

import logging
import httpx

logger = logging.getLogger("lobster.defense")


class DefenseModule:
    """防御模块"""

    def __init__(self, referee_url: str, lobster_id: int):
        self.referee_url = referee_url
        self.lobster_id = lobster_id
        self.client = httpx.AsyncClient(timeout=10)
        self.current_defense = None

    async def set_defense(self, defense_type: str) -> dict:
        """设置防御"""
        try:
            resp = await self.client.post(
                f"{self.referee_url}/defense",
                json={
                    "lobster_id": self.lobster_id,
                    "defense_type": defense_type,
                }
            )
            result = resp.json()

            if result.get("ok"):
                self.current_defense = defense_type
                logger.info(f"🛡️ 防御已切换至: {defense_type}")
            else:
                logger.warning(f"❌ 防御切换失败: {result.get('message', '')}")

            return result
        except Exception as e:
            logger.error(f"❌ 防御请求异常: {e}")
            return {"ok": False, "message": str(e)}

    async def close(self):
        await self.client.aclose()
