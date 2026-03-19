"""裁判服务 v3 — CTF 真实攻防"""

import asyncio
import json
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional

from game_engine import GameEngine

engine: GameEngine = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global engine
    engine = GameEngine()
    print("🏴‍☠️ CTF 裁判服务启动！龙虾斗兽场 v3 准备就绪")
    task = asyncio.create_task(random_event_scheduler())
    yield
    task.cancel()


app = FastAPI(title="🦞 龙虾 CTF 斗兽场 - 裁判", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===== 请求模型 =====

class HeartbeatRequest(BaseModel):
    lobster_id: int

class FlagSubmitRequest(BaseModel):
    attacker_id: int
    target_id: int
    flag: str
    vulnerability: str

class AttackFailedRequest(BaseModel):
    attacker_id: int
    target_id: int
    vulnerability: str
    reason: str = ""

class DefenseRequest(BaseModel):
    lobster_id: int
    vulnerability: str


# ===== API 路由 =====

@app.post("/heartbeat")
async def heartbeat(req: HeartbeatRequest):
    return engine.heartbeat(req.lobster_id)

@app.post("/submit_flag")
async def submit_flag(req: FlagSubmitRequest):
    """提交 flag — CTF 核心"""
    return engine.submit_flag(req.attacker_id, req.target_id, req.flag, req.vulnerability)

@app.post("/attack_failed")
async def attack_failed(req: AttackFailedRequest):
    """记录攻击失败"""
    return engine.attack_failed(req.attacker_id, req.target_id, req.vulnerability, req.reason)

@app.post("/defense")
async def defense(req: DefenseRequest):
    """记录修补漏洞"""
    return engine.record_defense(req.lobster_id, req.vulnerability)

@app.get("/status")
async def status():
    return engine.get_status()

@app.get("/battlefield/{lobster_id}")
async def battlefield(lobster_id: int):
    data = engine.get_battlefield(lobster_id)
    if not data:
        raise HTTPException(404, "龙虾不存在")
    return data

@app.get("/events")
async def events(count: int = 50, limit: int = None):
    n = limit or count
    return engine.event_log.get_recent(n)

@app.get("/events/stream")
async def event_stream():
    async def generate():
        last_time = time.time()
        while True:
            events = engine.event_log.get_since(last_time)
            if events:
                last_time = events[-1]["timestamp"]
                for event in events:
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            await asyncio.sleep(2)
    return StreamingResponse(generate(), media_type="text/event-stream")

# ===== 管理 =====

@app.post("/admin/start")
async def admin_start():
    return engine.start_game()

@app.post("/admin/pause")
async def admin_pause():
    return engine.pause_game()

@app.post("/admin/random-event")
async def admin_random_event():
    return engine.trigger_random_event()

@app.post("/admin/rotate-flags")
async def admin_rotate_flags():
    engine.rotate_flags()
    return {"ok": True, "message": "Flag 已轮换"}

@app.get("/health")
async def health():
    return {"status": "ok", "service": "referee-ctf-v3"}


async def random_event_scheduler():
    while True:
        await asyncio.sleep(300)
        if engine.game_started and not engine.game_paused:
            import random
            if random.random() < 0.4:
                engine.trigger_random_event()
