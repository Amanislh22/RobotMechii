import cv2
import numpy as np
import math
import os
import uuid
from fastapi import HTTPException

UPLOAD_FOLDER = "uploads"  # Match the UPLOAD_FOLDER from main.py

def detect_path_commands(image_path, scale_factor=1.0):
    """
    Detect a path in the image and generate movement commands.
    """
    # Read and preprocess the image
    img = cv2.imread(image_path)
    if img is None:
        raise HTTPException(status_code=400, detail="Could not read image")

    # Resize for faster processing
    max_dim = 1000
    height, width = img.shape[:2]
    if max(height, width) > max_dim:
        scale = max_dim / max(height, width)
        img = cv2.resize(img, (int(width * scale), int(height * scale)))

    # Convert to grayscale and apply blur
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Apply adaptive thresholding to isolate the path
    thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)

    # Edge detection
    edges = cv2.Canny(thresh, 50, 150)

    # Reduce noise
    kernel = np.ones((3, 3), np.uint8)
    edges = cv2.dilate(edges, kernel, iterations=1)
    edges = cv2.erode(edges, kernel, iterations=1)

    # Find contours
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        raise HTTPException(status_code=400, detail="No path detected")

    # Select the largest contour (assumed to be the path)
    path_contour = max(contours, key=cv2.contourArea)

    # Simplify the contour
    epsilon = 0.01 * cv2.arcLength(path_contour, False)
    approx = cv2.approxPolyDP(path_contour, epsilon, False)

    # Extract points
    points = [point[0] for point in approx]
    if len(points) < 2:
        raise HTTPException(status_code=400, detail="Insufficient points to form a path")

    # Calculate segments and angles
    commands = []
    for i in range(len(points) - 1):
        p1 = points[i]
        p2 = points[i + 1]

        # Calculate distance
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        distance = math.sqrt(dx**2 + dy**2) * scale_factor
        commands.append(f"forward: {round(distance, 2)}m")

        # Calculate angle to next segment (if not the last segment)
        if i < len(points) - 2:
            p3 = points[i + 2]
            v1 = np.array([p2[0] - p1[0], p2[1] - p1[1]])
            v2 = np.array([p3[0] - p2[0], p3[1] - p2[1]])

            dot = np.dot(v1, v2)
            mag1 = np.linalg.norm(v1)
            mag2 = np.linalg.norm(v2)

            if mag1 * mag2 == 0:
                angle = 0
            else:
                cos_angle = max(min(dot / (mag1 * mag2), 1.0), -1.0)
                angle = math.degrees(math.acos(cos_angle))

            # Determine turn direction
            cross = v1[0] * v2[1] - v1[1] * v2[0]
            turn = "Right" if cross < 0 else "Left"
            if abs(angle) > 5:  # Ignore small angles
                commands.append(f"{turn}: {round(angle, 2)}°")

    # Annotate the image
    output_img = img.copy()
    for i, point in enumerate(points):
        cv2.circle(output_img, tuple(point), 5, (0, 0, 255), -1)
        if i < len(points) - 1:
            cv2.line(output_img, tuple(points[i]), tuple(points[i + 1]), (0, 255, 0), 2)

    # Save the annotated image directly to the uploads folder
    annotated_filename = f"{uuid.uuid4()}_{os.path.basename(image_path).replace('.', '_annotated.')}"
    output_path = os.path.join(UPLOAD_FOLDER, annotated_filename)
    cv2.imwrite(output_path, output_img)

    return {
        "shape": "Path",
        "commands": commands,
        "annotated_image": output_path
    }
