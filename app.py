import os
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from google.genai import types
from google.genai.errors import APIError  # Diagnostic import

app = FastAPI()

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
    return {"status": "Diagnostic audio engine is live"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("🎯 Local client connection handshake complete!")
    await websocket.send_text("SYSTEM: Connection stabilized on Render proxy.")

    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        system_instruction=types.Content(
            parts=[types.Part.from_text(text="You are a smart desktop voice friend. Give very short, human-like voice responses.")]
        )
    )

    try:
        async with client.aio.live.connect(model="gemini-3.8-live", config=config) as session:
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

            await asyncio.gather(receive_from_client(), send_to_client())
            
    except APIError as age:
        # DIAGNOSTIC LOG 1: Captures full detailed responses from Google's endpoint node
        error_detail = f"CRITICAL GOOGLE API ERROR: Status Code {age.code} | Message: {age.message}"
        print(f"❌ {error_detail}")
        try:
            await websocket.send_text(f"SYSTEM_ERROR: {error_detail}")
        except:
            pass
    except Exception as e:
        # DIAGNOSTIC LOG 2: Standard fallback catcher
        error_detail = f"Standard Session Exception: {str(e)}"
        print(f"⚠️ {error_detail}")
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
