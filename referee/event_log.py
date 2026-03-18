"""事件日志系统 - 记录所有战斗事件"""

import json
import time
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field, asdict
from collections import deque
from pathlib import Path


@dataclass
class GameEvent:
    """游戏事件"""
    timestamp: float
    event_type: str  # attack, defense, elimination, heartbeat, random_event, phase_change
    source_id: Optional[int]  # 发起者
    target_id: Optional[int]  # 目标
    detail: dict = field(default_factory=dict)
    message: str = ""

    def to_dict(self):
        d = asdict(self)
        d["time_str"] = datetime.fromtimestamp(self.timestamp).strftime("%m-%d %H:%M:%S")
        return d


class EventLog:
    """事件日志管理器"""

    def __init__(self, max_events: int = 5000):
        self.events: deque[GameEvent] = deque(maxlen=max_events)
        self.log_dir = Path("/app/data/logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def add(self, event_type: str, source_id: Optional[int] = None,
            target_id: Optional[int] = None, detail: dict = None,
            message: str = "") -> GameEvent:
        """添加事件"""
        event = GameEvent(
            timestamp=time.time(),
            event_type=event_type,
            source_id=source_id,
            target_id=target_id,
            detail=detail or {},
            message=message
        )
        self.events.append(event)
        self._write_to_file(event)
        return event

    def get_recent(self, count: int = 50, event_type: str = None) -> list[dict]:
        """获取最近的事件"""
        events = list(self.events)
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return [e.to_dict() for e in events[-count:]]

    def get_since(self, since_timestamp: float) -> list[dict]:
        """获取某时间之后的所有事件"""
        return [e.to_dict() for e in self.events if e.timestamp > since_timestamp]

    def _write_to_file(self, event: GameEvent):
        """写入日志文件"""
        try:
            date_str = datetime.fromtimestamp(event.timestamp).strftime("%Y-%m-%d")
            log_file = self.log_dir / f"events_{date_str}.jsonl"
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
        except Exception:
            pass  # 日志写入失败不影响游戏
