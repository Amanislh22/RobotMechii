from fastapi import FastAPI, File, UploadFile, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os
import uuid
import tempfile
import paho.mqtt.publish as publish
import cv2
import json
import numpy as np
from .utils.image_processing import  detect_shape_from_drawn_object

app = FastAPI(title="RobotMechi Path Generator")

# Enable CORS for frontend (to be updated in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://localhost", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Folders
UPLOAD_FOLDER = "uploads"
ORIGINAL_FOLDER = os.path.join(UPLOAD_FOLDER, "originals")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(ORIGINAL_FOLDER, exist_ok=True)

@app.get("/")
def home():
    return {"message": "Upload a path image to generate movement commands for RobotMechi"}


@app.post("/generate-path-commands/")
async def generate_path_commands(file: UploadFile = File(...), scale_factor: float = 0.01, force_shape: str = Body(None)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_file_path = os.path.join(temp_dir, f"{uuid.uuid4()}_{file.filename}")
        content = await file.read()

        with open(temp_file_path, "wb") as buffer:
            buffer.write(content)

        original_file_path = os.path.join(ORIGINAL_FOLDER, f"{uuid.uuid4()}_{file.filename}")
        with open(original_file_path, "wb") as original_file:
            original_file.write(content)

        # Detect shape and generate commands
        dimensions = detect_shape_from_drawn_object(original_file_path, square_tolerance=0.1)
        if not dimensions:
            return {"error": "Could not retrieve image dimensions"}

        width_cm, height_cm, shape_type = dimensions
        commandsS = []

        if shape_type == "SQUARE":
            side_length = (width_cm + height_cm) / 2
            commandsS.append(f"forward: {side_length}m")
            for _ in range(4):
                commandsS.append("Right: 90°")
                commandsS.append(f"forward: {side_length}m")

        elif shape_type == "RECTANGLE":
            long_side = max(width_cm, height_cm)
            short_side = min(width_cm, height_cm)
            commandsS += [
                f"forward: {long_side}m", "Right: 90°",
                f"forward: {short_side}m", "Right: 90°",
                f"forward: {long_side}m", "Right: 90°",
                f"forward: {short_side}m"
            ]

        print("Generated commands:", commandsS)

        # Only extract the annotated image now
        try:
            # Read and annotate image 
            img = cv2.imread(original_file_path)
            if img is None:
                raise HTTPException(status_code=400, detail="Could not read image")

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                           cv2.THRESH_BINARY_INV, 11, 2)
            edges = cv2.Canny(thresh, 50, 150)
            kernel = np.ones((3, 3), np.uint8)
            edges = cv2.dilate(edges, kernel, iterations=1)
            edges = cv2.erode(edges, kernel, iterations=1)

            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                raise HTTPException(status_code=400, detail="No path detected")

            path_contour = max(contours, key=cv2.contourArea)
            epsilon = 0.01 * cv2.arcLength(path_contour, False)
            approx = cv2.approxPolyDP(path_contour, epsilon, False)

            points = [pt[0] for pt in approx]
            if len(points) < 2:
                raise HTTPException(status_code=400, detail="Insufficient points to form a path")

            output_img = img.copy()
            for i, point in enumerate(points):
                cv2.circle(output_img, tuple(point), 5, (0, 0, 255), -1)
                if i < len(points) - 1:
                    cv2.line(output_img, tuple(points[i]), tuple(points[i + 1]), (0, 255, 0), 2)

            annotated_filename = f"{uuid.uuid4()}_{os.path.basename(original_file_path).replace('.', '_annotated.')}"
            output_path = os.path.join(UPLOAD_FOLDER, annotated_filename)
            cv2.imwrite(output_path, output_img)

            # MQTT
            broker = "10.10.4.123"
            topic = "robotmechi/commands"
            payload = json.dumps({"commands": commandsS})
            try:
                publish.single(topic, payload, hostname=broker, qos=1, retain=False)
                print("Commands published to MQTT broker successfully")
            except Exception as e:
                print(f"[MQTT] Error: {str(e)}")

            return {
                "shape": shape_type,
                "commands": commandsS,
                "annotated_image": output_path
            }

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
