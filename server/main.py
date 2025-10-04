from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, List, Optional
from collections import deque
from datetime import datetime

app = FastAPI()

# Enable CORS for Figma plugin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory queue
message_queue = deque(maxlen=1000)  # Limit queue size

class Message(BaseModel):
    type: str
    topicTitle: str

    content: Optional[Any] = None
    color: Optional[Any] = None
    width: Optional[int] = None
    height: Optional[int] = None
    center: Optional[List[float]] = None
    font: Optional[str] = None
    size: Optional[int] = None
    spacing: Optional[int] = None

@app.post("/push")
async def push_message(message: Message):
    """Your app pushes messages here"""
    message_queue.append(message.model_dump())
    return {"status": "ok", "queue_size": len(message_queue)}


@app.get("/poll")
async def poll_messages(limit: int = 50) -> List[dict]:
    """Figma plugin polls messages here"""
    messages = []
    for _ in range(min(limit, len(message_queue))):
        if message_queue:
            messages.append(message_queue.popleft())
    return messages


@app.get("/peek")
async def peek_queue(limit: int = 10) -> List[dict]:
    """Check queue without removing messages"""
    return list(message_queue)[:limit]


@app.get("/status")
async def get_status():
    """Check queue status"""
    return {
        "queue_size": len(message_queue),
        "max_size": message_queue.maxlen
    }


@app.delete("/clear")
async def clear_queue():
    """Clear all messages"""
    message_queue.clear()
    return {"status": "cleared"}


def start_server(host="0.0.0.0", port=8000, messages=[]):
    """Start FastAPI server in background thread"""
    import uvicorn
    import threading
    global message_queue
    message_queue = deque(messages, maxlen=1000)
    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    return server, thread


if __name__ == "__main__":
    import json
    import uvicorn
    message_queue = deque(json.load(open('to-figma-messages-2025-10-04-08-03-11.json', 'r')), maxlen=1000)
    # message_queue = deque(json.load(open('test.json', 'r')), maxlen=1000)
    uvicorn.run(app, host="0.0.0.0", port=8080)