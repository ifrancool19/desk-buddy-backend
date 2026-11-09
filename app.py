import os
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from google import genai
from google.genai import types

app = FastAPI()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

@app.get("/")
async def root():
    return {"status": "Always-on backend is active"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("ESP32-C3 Desk Buddy connected.")

    config = types.LiveConnectConfig(
        response_modalities=[types.LiveModality.AUDIO],
        system_instruction=types.Content(
            parts=[types.Part.from_text(text="You are a concise voice-activated desk buddy. Respond with short replies.")]
        )
    )

    try:
        async with client.aio.live.connect(model="gemini-2.5-flash", config=config) as session:
            async def receive_from_esp():
                try:
                    while True:
                        data = await websocket.receive_bytes()
                        await session.send(input={"data": data, "mime_type": "audio/pcm;rate=16000"}, end_of_turn=False)
                except WebSocketDisconnect:
                    print("Hardware disconnected.")

            async def send_to_esp():
                try:
                    async for response in session.receive():
                        server_content = response.server_content
                        if server_content and server_content.model_turn:
                            for part in server_content.model_turn.parts:
                                if part.inline_data:
                                    await websocket.send_bytes(part.inline_data.data)
                except Exception as e:
                    print(f"Error: {e}")

            await asyncio.gather(receive_from_esp(), send_to_esp())
    except Exception as e:
        print(f"Session closed: {e}")
