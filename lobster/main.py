"""龙虾主循环 v3 — CTF 模式"""

import os
import sys
import time
import asyncio
import random
import logging
import threading
import httpx

from brain import LobsterBrain
from attacker import execute_attack, scout_target

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format=f'%(asctime)s [{os.environ.get("LOBSTER_NAME", "?")}] %(message)s'
)
logger = logging.getLogger("lobster")

REFEREE_URL = os.environ.get("REFEREE_URL", "http://referee:8000")
LOBSTER_ID = int(os.environ.get("LOBSTER_ID", "0"))
LOBSTER_NAME = os.environ.get("LOBSTER_NAME", "Unknown")
HEARTBEAT_INTERVAL = int(os.environ.get("HEARTBEAT_INTERVAL", "10"))
DECISION_MIN = int(os.environ.get("DECISION_MIN", "15"))
DECISION_MAX = int(os.environ.get("DECISION_MAX", "30"))

# 容器名到ID的映射（由环境变量提供）
HOSTNAME_MAP = {}


async def heartbeat(client: httpx.AsyncClient) -> dict:
    """发送心跳"""
    try:
        resp = await client.post(f"{REFEREE_URL}/heartbeat", json={"lobster_id": LOBSTER_ID})
        return resp.json()
    except Exception as e:
        logger.error(f"❌ 心跳失败: {e}")
        return {"ok": False}


async def get_battlefield(client: httpx.AsyncClient) -> dict:
    """获取战场信息"""
    try:
        resp = await client.get(f"{REFEREE_URL}/battlefield/{LOBSTER_ID}")
        return resp.json()
    except Exception as e:
        logger.error(f"❌ 获取战场信息失败: {e}")
        return {}


async def do_defend(client: httpx.AsyncClient, vulnerability: str):
    """执行防御（修补漏洞）"""
    try:
        resp = await client.post(
            "http://localhost:5000/patch",
            json={"vulnerability": vulnerability}
        )
        result = resp.json()
        logger.info(f"🛡️ 修补 {vulnerability}: {result.get('message', '')}")
        
        # 通知裁判
        await client.post(f"{REFEREE_URL}/defense", json={
            "lobster_id": LOBSTER_ID,
            "vulnerability": vulnerability,
        })
    except Exception as e:
        logger.error(f"❌ 修补失败: {e}")


async def do_scout(brain: LobsterBrain, target_hostname: str, target_id: int):
    """执行侦察"""
    logger.info(f"🔍 侦察 {target_hostname}...")
    result = scout_target(target_hostname)
    
    if result.get("online"):
        patched = result.get("patched", [])
        all_vulns = ["path_traversal", "sql_injection", "command_injection", "auth_bypass", "ssrf"]
        for v in all_vulns:
            status = "patched" if v in patched else "open"
            brain.update_intel(target_id, v, status)
        logger.info(f"🔍 侦察结果 {target_hostname}: patched={patched}")
    else:
        logger.info(f"🔍 {target_hostname} 不在线")


async def main_loop():
    """主决策循环"""
    brain = LobsterBrain()
    
    async with httpx.AsyncClient(timeout=15) as client:
        # 等待裁判启动
        logger.info(f"🦞 {LOBSTER_NAME} 启动！等待裁判...")
        for _ in range(30):
            try:
                resp = await client.get(f"{REFEREE_URL}/health")
                if resp.status_code == 200:
                    break
            except:
                pass
            await asyncio.sleep(2)
        
        logger.info(f"🦞 {LOBSTER_NAME} 就绪！开始 CTF 对抗！")
        
        while True:
            # 心跳
            hb = await heartbeat(client)
            if not hb.get("ok"):
                if hb.get("alive") is False:
                    logger.info("💀 我已被淘汰！退出...")
                    # 继续心跳但不做决策
                    await asyncio.sleep(HEARTBEAT_INTERVAL)
                    continue
                await asyncio.sleep(5)
                continue

            # 等待游戏开始
            if not hb.get("game_started", False):
                await asyncio.sleep(5)
                continue
            
            # 决策间隔
            await asyncio.sleep(random.randint(DECISION_MIN, DECISION_MAX))
            
            # 获取战场信息
            battlefield = await get_battlefield(client)
            if not battlefield:
                continue
            
            # AI 决策
            decision = brain.decide(battlefield)
            action = decision.get("action", "scout")
            
            if action == "attack":
                target_hostname = decision.get("target_hostname", "")
                target_id = decision.get("target_id")
                vulnerability = decision.get("vulnerability", "path_traversal")
                
                if target_hostname and target_id:
                    logger.info(f"⚔️ 攻击 {target_hostname} ({vulnerability}) — {decision.get('reasoning','')}")
                    result = await execute_attack(target_hostname, target_id, vulnerability)
                    
                    # 更新攻击历史
                    brain.attack_history.append({
                        "target": target_hostname,
                        "vuln": vulnerability,
                        "success": result.get("ok", False),
                        "time": time.strftime("%H:%M:%S"),
                    })
                    if len(brain.attack_history) > 10:
                        brain.attack_history = brain.attack_history[-10:]
                    
                    # 根据结果更新情报
                    if not result.get("ok") and "patched" in str(result.get("reason", "")):
                        brain.update_intel(target_id, vulnerability, "patched")
                    elif result.get("ok"):
                        brain.update_intel(target_id, vulnerability, "open")

            elif action == "defend":
                vulnerability = decision.get("vulnerability", "")
                if vulnerability:
                    logger.info(f"🛡️ 修补 {vulnerability} — {decision.get('reasoning','')}")
                    await do_defend(client, vulnerability)

            elif action == "scout":
                target_hostname = decision.get("target_hostname", "")
                target_id = decision.get("target_id")
                if target_hostname and target_id:
                    await do_scout(brain, target_hostname, target_id)
                else:
                    # 随机侦察
                    enemies = battlefield.get("enemies", [])
                    if enemies:
                        target = random.choice(enemies)
                        await do_scout(brain, target["hostname"], target["id"])


def start_web_service():
    """在后台线程启动漏洞 web 服务"""
    from services.vuln_app import run_server
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    logger.info("🌐 漏洞 Web 服务启动于 :5000")
    # 等一会让 Flask 启动
    time.sleep(3)


if __name__ == "__main__":
    # 启动漏洞 web 服务
    start_web_service()
    
    # 启动决策循环
    asyncio.run(main_loop())
