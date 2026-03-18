"""心跳模块 - 定期向裁判报到"""

import logging
import httpx

logger = logging.getLogger("lobster.heartbeat")


class HeartbeatModule:
    """心跳模块"""

    def __init__(self, referee_url: str, lobster_id: int):
        self.referee_url = referee_url
        self.lobster_id = lobster_id
        self.client = httpx.AsyncClient(timeout=10)
        self.alive = True

    async def ping(self) -> dict:
        """发送心跳"""
        try:
            resp = await self.client.post(
                f"{self.referee_url}/heartbeat",
                json={"lobster_id": self.lobster_id}
            )
            result = resp.json()

            if not result.get("alive", True):
                self.alive = False
                logger.warning("💀 我已经被淘汰了...")

            return result
        except Exception as e:
            logger.error(f"❌ 心跳发送失败: {e}")
            return {"ok": False, "message": str(e)}

    async def close(self):
        await self.client.aclose()
