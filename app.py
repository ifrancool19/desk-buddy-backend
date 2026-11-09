import os
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware  # <-- ADD THIS IMPORT
from google import genai
from google.genai import types

app = FastAPI()

# 🛠️ ADD THIS BLOCK TO ALLOW CROSS-ORIGIN WEBSOCKETS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

@app.get("/")
async def root():
    return {"status": "Always-on audio queue engine is live"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("🎯 Local client connection handshake complete!")
    
    # Send an immediate text frame to satisfy Render's router path and stabilize the line
    await websocket.send_text("SYSTEM: Connection stabilized on Render proxy.")

    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        system_instruction=types.Content(
            parts=[types.Part.from_text(text="You are a smart desktop voice friend. Give very short, human-like voice responses.")]
        )
    )

    try:
        # FIX: Swapped to the active production real-time voice streaming identifier
        async with client.aio.live.connect(model="gemini-2.0-flash-exp", config=config) as session:
            print("🚀 Secure voice session with Google AI created!")
            await websocket.send_text("SYSTEM: Connected to Google Gemini Live API.")
            
            async def receive_from_client():
                try:
                    while True:
                        data = await websocket.receive_bytes()
                        if data and len(data) > 0:
                            await session.send(
                                input={"data": data, "mime_type": "audio/pcm;rate=16000"},
                                end_of_turn=False
                            )
                except WebSocketDisconnect:
                    print("Local app disconnected cleanly.")
                except Exception as e:
                    print(f"Input channel handling exception: {e}")

            async def send_to_client():
                try:
                    async for response in session.receive():
                        server_content = response.server_content
                        if server_content and server_content.model_turn:
                            for part in server_content.model_turn.parts:
                                if part.inline_data:
                                    await websocket.send_bytes(part.inline_data.data)
                except Exception as e:
                    print(f"Output channel handling exception: {e}")

            # Run both background streams concurrently without blocking the port
            await asyncio.gather(receive_from_client(), send_to_client())
            
    except Exception as e:
        print(f"⚠️ Live session dropped: {e}")
        try:
            await websocket.send_text(f"SYSTEM_ERROR: Session dropped: {str(e)}")
        except:
            pass
    finally:
        try:
            await websocket.close()
        except:
            pass
        print("🔌 Pipeline disconnected.")
