import os
import asyncio
import json
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
    return {"status": "Direct WebSocket proxy engine is live"}

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

    # Direct production routing string for the Multimodal Live API
    # Bypasses internal SDK path formatting entirely
    gemini_url = f"wss://://googleapis.com{GEMINI_API_KEY}"

    try:
        print("🔗 Connecting directly to Google Gemini Live WebSocket node...")
        async with websockets.connect(gemini_url) as gemini_ws:
            print("🚀 Secure voice session with Google AI created successfully!")
            await websocket.send_text("SYSTEM: Connected to Google Gemini Live API.")

            # Send the initial session configuration frame as a JSON text string
            setup_config = {
                "setup": {
                    "model": "models/gemini-2.0-flash-exp",
                    "generationConfig": {
                        "responseModalities": ["AUDIO"],
                        "speechConfig": {
                            "voiceConfig": {
                                "prebuiltVoiceConfig": {
                                    "voiceName": "Puck" # Friendly desk buddy voice
                                }
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

            # Task A: Forward raw audio chunks from laptop mic up to Google Gemini
            async def receive_from_client():
                try:
                    while True:
                        data = await websocket.receive_bytes()
                        if data and len(data) > 0:
                            # Format binary PCM bytes into the exact JSON envelope Gemini expects
                            import base64
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
                except WebSocketDisconnect:
                    print("Local app disconnected cleanly.")
                except Exception as e:
                    print(f"Input channel handling exception: {e}")

            # Task B: Receive responses from Google Gemini and push down to laptop/hardware
            async def send_to_client():
                try:
                    async for message in gemini_ws:
                        response_data = json.loads(message)
                        
                        # Parse out the binary audio stream data segments
                        if "serverContent" in response_data:
                            model_turn = response_data["serverContent"].get("modelTurn", {})
                            for part in model_turn.get("parts", []):
                                if "inlineData" in part:
                                    import base64
                                    raw_audio_bytes = base64.b64decode(part["inlineData"]["data"])
                                    await websocket.send_bytes(raw_audio_bytes)
                except Exception as e:
                    print(f"Output channel handling exception: {e}")

            await asyncio.gather(receive_from_client(), send_to_client())

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
