"""裁判服务 - 龙虾大乱斗核心"""

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


# 全局游戏引擎
engine: GameEngine = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    global engine
    engine = GameEngine()
    print("🦞 裁判服务启动！龙虾大乱斗准备就绪")

    # 启动随机事件定时器
    task = asyncio.create_task(random_event_scheduler())
    yield
    task.cancel()


app = FastAPI(title="🦞 龙虾大乱斗 - 裁判服务", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===== 请求模型 =====

class HeartbeatRequest(BaseModel):
    lobster_id: int

class AttackRequest(BaseModel):
    attacker_id: int
    target_id: int
    attack_type: str

class DefenseRequest(BaseModel):
    lobster_id: int
    defense_type: str

class AllianceRequest(BaseModel):
    lobster_id: int
    target_id: int


# ===== API 路由 =====

@app.post("/heartbeat")
async def heartbeat(req: HeartbeatRequest):
    """龙虾心跳"""
    return engine.heartbeat(req.lobster_id)


@app.post("/attack")
async def attack(req: AttackRequest):
    """提交攻击"""
    return engine.process_attack(req.attacker_id, req.target_id, req.attack_type)


@app.post("/defense")
async def defense(req: DefenseRequest):
    """设置防御"""
    return engine.set_defense(req.lobster_id, req.defense_type)


@app.post("/alliance")
async def alliance(req: AllianceRequest):
    """提议结盟"""
    return engine.propose_alliance(req.lobster_id, req.target_id)


@app.post("/alliance/break")
async def break_alliance(req: AllianceRequest):
    """背刺！撕毁盟约"""
    return engine.break_alliance(req.lobster_id, req.target_id)


@app.get("/status")
async def status():
    """获取游戏状态"""
    return engine.get_status()


@app.get("/battlefield/{lobster_id}")
async def battlefield(lobster_id: int):
    """获取龙虾视角战场"""
    data = engine.get_battlefield(lobster_id)
    if not data:
        raise HTTPException(404, "龙虾不存在")
    return data


@app.get("/events")
async def events(count: int = 50, event_type: str = None):
    """获取事件日志"""
    return engine.event_log.get_recent(count, event_type)


@app.get("/events/stream")
async def event_stream():
    """SSE 事件流"""
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


# ===== 管理 API =====

@app.post("/admin/start")
async def admin_start():
    """开始游戏"""
    return engine.start_game()


@app.post("/admin/pause")
async def admin_pause():
    """暂停/恢复"""
    return engine.pause_game()


@app.post("/admin/random-event")
async def admin_random_event():
    """手动触发随机事件"""
    return engine.trigger_random_event()


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok", "service": "referee"}


# ===== 随机事件调度器 =====

async def random_event_scheduler():
    """定时触发随机事件"""
    while True:
        await asyncio.sleep(600)  # 每 10 分钟检查一次
        if engine.game_started and not engine.game_paused:
            # 30% 概率触发随机事件
            import random
            if random.random() < 0.3:
                engine.trigger_random_event()
