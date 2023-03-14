import json
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
        <h2>Your ID: <span id="ws-id"></span></h2>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
            var token = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJpYXQiOjE2NzgzNjIwNTEsImV4cCI6MTY3ODM2NTY1MSwicm9sZXMiOlsiUk9MRV9VU0VSIl0sInVzZXJuYW1lIjoic3RyaW5nQHN0cmkubmcifQ.twkFbUHqZG2bNVCLpSts1QxSZzGXkR4TY2VKYX88gHJ7WN5LcHWbGUjMi3CLC7GKvJsURxP6qaFSY0AU9kR9OWSEwQKvXaR2bI9YmluclNXRv-It13S6lAxtKiGeqAc8pUvbi5eabp5VKc_vxVj4rhFtYaXt-e2AbXu26EF9ta8AcNW_AEy_esX59eZ9Cf7Mn1Bh0b_54L4BovQV-9quagbWwD8NICC7axxPH4XeiZI5TmDXrEGrcI7Il951EVoVyL4z-UipY1cA1BVxxAVXoTuMXcTDvE9AUX1ySv_qTXyHMjh6PPCjiMtilcQTgusQ1GqKEhtHuL5aQyyMpgIF0A'
            document.querySelector("#ws-id").textContent = token;
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
    url = "https://127.0.0.1:8001/api/users/1/info"

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
