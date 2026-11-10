import os
import asyncio
import json
import base64
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import websockets

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

@app.get("/")
async def root():
    return {"status": "Queue-buffered WebSocket proxy engine is live"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("🎯 Local client connection handshake complete!")
    await websocket.send_text("SYSTEM: Connection stabilized on Render proxy.")

    if not GEMINI_API_KEY:
        print("❌ ERROR: GEMINI_API_KEY environment variable is missing on Render!")
        await websocket.send_text("SYSTEM_ERROR: GEMINI_API_KEY is missing on server settings.")
        await websocket.close()
        return

    gemini_url = f"wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent?key={GEMINI_API_KEY}"

    try:
        print("🔗 Connecting directly to Google Gemini Live WebSocket node...")
        async with websockets.connect(gemini_url) as gemini_ws:
            print("🚀 Secure voice session with Google AI created successfully!")
            await websocket.send_text("SYSTEM: Connected to Google Gemini Live API.")

            # Standard structured session config block targeting the live model
            setup_config = {
                "setup": {
                    "model": "models/gemini-2.5-flash",
                    "generationConfig": {
                        "responseModalities": ["AUDIO"],
                        "speechConfig": {
                            "voiceConfig": {
                                "prebuiltVoiceConfig": {}
                            }
                        }
                    },
                    "systemInstruction": {
                        "parts": [{"text": "You are a smart desktop voice friend. Give very short, human-like voice responses."}]
                    }
                }
            }
            await gemini_ws.send(json.dumps(setup_config))
            print("📝 Session configurations sent to Gemini.")
            await asyncio.sleep(0.5)

            # FIX: Introduce an explicit asyncio Queue to buffer rapid client microphone packets
            audio_queue = asyncio.Queue()

            # Task 1: Read data instantly from the local laptop websocket and push to the queue
            async def read_from_client_ws():
                try:
                    while True:
                        data = await websocket.receive_bytes()
                        if data and len(data) > 0:
                            await audio_queue.put(data)
                except WebSocketDisconnect:
                    print("Local laptop disconnected.")
                    raise
                except Exception as e:
                    print(f"Error reading from client WS: {e}")
                    raise

            # Task 2: Consume from the queue, format, and push to Google Gemini at a stable pace
            async def forward_to_gemini():
                try:
                    while True:
                        data = await audio_queue.get()
                        audio_b64 = base64.b64encode(data).decode("utf-8")
                        realtime_input = {
                            "realtimeInput": {
                                "mediaChunks": [
                                    {
                                        "mimeType": "audio/pcm;rate=16000",
                                        "data": audio_b64
                                    }
                                ]
                            }
                        }
                        await gemini_ws.send(json.dumps(realtime_input))
                        audio_queue.task_done()
                        # Yield control to prevent CPU spin/network flooding
                        await asyncio.sleep(0.005)
                except Exception as e:
                    print(f"Error forwarding to Gemini: {e}")
                    raise

            # Task 3: Handle the output stream coming back down from Gemini to the laptop speakers
            async def send_to_client():
                try:
                    async for message in gemini_ws:
                        response_data = json.loads(message)
                        if "serverContent" in response_data:
                            model_turn = response_data["serverContent"].get("modelTurn", {})
                            for part in model_turn.get("parts", []):
                                if "inlineData" in part:
                                    raw_audio_bytes = base64.b64decode(part["inlineData"]["data"])
                                    await websocket.send_bytes(raw_audio_bytes)
                except Exception as e:
                    print(f"Output channel handling exception: {e}")
                    raise

            # Execute all structural tasks concurrently
            await asyncio.gather(
                read_from_client_ws(), 
                forward_to_gemini(), 
                send_to_client()
            )

    except Exception as e:
        error_detail = f"Direct Gateway Session Exception: {str(e)}"
        print(f"❌ {error_detail}")
        try:
            await websocket.send_text(f"SYSTEM_ERROR: {error_detail}")
        except:
            pass
    finally:
        try:
            await websocket.close()
        except:
            pass
        print("🔌 Pipeline disconnected.")
