from fastapi import FastAPI, File, UploadFile, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os
import uuid
import tempfile
import paho.mqtt.publish as publish
import serial
import json
from .utils.image_processing import detect_path_commands

app = FastAPI(title="RobotMechi Path Generator")

# Enable CORS for frontend (to be updated in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://localhost", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.get("/")
def home():
    return {"message": "Upload a path image to generate movement commands for RobotMechi"}

@app.post("/generate-path-commands/")
async def generate_path_commands(file: UploadFile = File(...), scale_factor: float = 0.01):
    """
    Upload an image of a path to generate movement commands.
    scale_factor: Pixels-to-meters conversion (default: 100 pixels = 1 meter).
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    # Use temporary directory for secure file handling
    with tempfile.TemporaryDirectory() as temp_dir:
        file_path = os.path.join(temp_dir, f"{uuid.uuid4()}_{file.filename}")
        with open(file_path, "wb") as buffer:
            # Read the file content and write to the buffer
            content = await file.read()
            buffer.write(content)

        try:
            # Process the image to generate commands
            result = detect_path_commands(file_path, scale_factor)
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/images/{filename}")
async def get_image(filename: str):
    """
    Serve annotated images from the uploads folder.
    """
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(file_path)

@app.post("/send-commands-mqtt/")
async def send_commands_mqtt(commands: list[str] = Body(...), broker: str = "localhost", topic: str = "robotmechi/commands"):
    """
    Send commands to the PathFollower via MQTT.
    """
    try:
        payload = json.dumps({"commands": commands})
        publish.single(topic, payload, hostname=broker)
        return {"status": "Commands published successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MQTT communication failed: {str(e)}")

@app.post("/send-commands-uart/")
async def send_commands_uart(commands: list[str] = Body(...), port: str = "COM3", baudrate: int = 9600):
    """
    Send commands to the PathFollower via UART.
    """
    try:
        with serial.Serial(port, baudrate, timeout=1) as ser:
            for command in commands:
                ser.write(f"{command}\n".encode())
            return {"status": "Commands sent successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"UART communication failed: {str(e)}")
