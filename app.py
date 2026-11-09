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
    return {"status": "Live API Stream Bridge is Active"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("🎯 Hardware/Simulator Client Connected to WebSocket!")

    # Standard configuration for real-time audio interaction
    config = types.LiveConnectConfig(
        response_modalities=[types.LiveModality.AUDIO],
        system_instruction=types.Content(
            parts=[types.Part.from_text(text="You are a real-time smart desk buddy. Respond with short, friendly voice answers.")]
        )
    )

    try:
        # Establish the live channel to Gemini
        async with client.aio.live.connect(model="gemini-2.5-flash", config=config) as session:
            
            async def receive_from_client():
                try:
                    while True:
                        data = await websocket.receive_bytes()
                        # Ensure we don't send empty buffer fragments
                        if len(data) > 0:
                            await session.send(
                                input={"data": data, "mime_type": "audio/pcm;rate=16000"},
                                end_of_turn=False
                            )
                except WebSocketDisconnect:
                    print("Client disconnected cleanly.")
                except Exception as e:
                    print(f"Error reading client stream: {e}")

            async def send_to_client():
                try:
                    async for response in session.receive():
                        server_content = response.server_content
                        if server_content and server_content.model_turn:
                            for part in server_content.model_turn.parts:
                                if part.inline_data:
                                    # Forward Gemini's speech bytes back down to speakers
                                    await websocket.send_bytes(part.inline_data.data)
                except Exception as e:
                    print(f"Error reading Gemini stream: {e}")

            # Execute input and output loops concurrently
            await asyncio.gather(receive_from_client(), send_to_client())
            
    except Exception as e:
        print(f"⚠️ Session exception occurred: {e}")
    finally:
        try:
            await websocket.close()
        except:
            pass
        print("🔌 Session closed.")
