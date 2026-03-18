"""Dashboard 服务 - 实时战况展示"""

import os
import json
import asyncio
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

REFEREE_URL = os.environ.get("REFEREE_URL", "http://referee:8000")


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("📊 Dashboard 启动！")
    yield


app = FastAPI(title="🦞 龙虾大乱斗 - 实时战况", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def index():
    """主页"""
    return FileResponse("static/index.html")


@app.get("/api/status")
async def proxy_status():
    """代理裁判状态"""
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(f"{REFEREE_URL}/status")
            return resp.json()
        except Exception as e:
            return {"error": str(e)}


@app.get("/api/events")
async def proxy_events(count: int = 50):
    """代理事件日志"""
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(f"{REFEREE_URL}/events", params={"count": count})
            return resp.json()
        except Exception as e:
            return {"error": str(e)}


# WebSocket 连接管理
connected_clients: list[WebSocket] = []


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 实时推送"""
    await websocket.accept()
    connected_clients.append(websocket)
    try:
        while True:
            # 每 3 秒推送状态
            async with httpx.AsyncClient(timeout=10) as client:
                try:
                    resp = await client.get(f"{REFEREE_URL}/status")
                    data = resp.json()
                    await websocket.send_json(data)
                except Exception:
                    await websocket.send_json({"error": "裁判服务连接失败"})

            await asyncio.sleep(3)
    except WebSocketDisconnect:
        connected_clients.remove(websocket)
    except Exception:
        if websocket in connected_clients:
            connected_clients.remove(websocket)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "dashboard"}
