import json
import os
import requests

from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

app = FastAPI()

html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <h1>WebSocket Chat</h1>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
            const urlParams = new URLSearchParams(window.location.search);
            const token = urlParams.get('token');
            var ws = new WebSocket(`ws://localhost:8000/ws/${token}`);
            ws.onmessage = function(event) {
                var messages = document.getElementById('messages')
                var message = document.createElement('li')
                var content = document.createTextNode(event.data)
                message.appendChild(content)
                messages.appendChild(message)
            };
            function sendMessage(event) {
                var input = document.getElementById("messageText")
                ws.send(input.value)
                input.value = ''
                event.preventDefault()
            }
        </script>
    </body>
</html>
"""


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()


@app.get("/")
async def get():
    return HTMLResponse(html)


@app.websocket("/ws/{token}")
async def websocket_endpoint(websocket_connection: WebSocket, token: str):
    await manager.connect(websocket_connection)
    url = os.getenv('API_BASE_URL') +"/api/users/1/info"

    headers = {
        'Accept': 'application/ld+json',
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + token
    }

    response = requests.get(url, headers=headers, verify=False)

    if response.status_code == 200:
        # récup du nickname
        print("Requête réussie", response.status_code)
        data = json.loads(response.text)
        nickname = data.get("nickname")
        print('Nickname:', nickname)
        try:
            while True:
                data = await websocket_connection.receive_text()
                # await manager.send_personal_message(f"You wrote: {data}", websocket_connection)
                await manager.broadcast(f"{nickname}: {data}")
        except WebSocketDisconnect:
            manager.disconnect(websocket_connection)
            await manager.broadcast(f"{nickname} left the chat")
    else:
        print("Requête échouée", response.status_code)
