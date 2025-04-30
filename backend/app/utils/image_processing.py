import cv2
import numpy as np
import math
import os
import uuid
from fastapi import HTTPException
from PIL import Image

UPLOAD_FOLDER = "uploads"  


def detect_shape_from_drawn_object(image_path, square_tolerance=0.1):
    image = cv2.imread(image_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Threshold to get binary image
    _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)

    # Find contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        print("No shapes found.")
        return None  # Explicitly return None

    # Assume the largest contour is the shape
    largest_contour = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(largest_contour)

    print(f"Detected shape dimensions: width={w} px, height={h} px")
    
    ratio = w / h
    print(f"Width/Height Ratio: {ratio:.2f}")

    if abs(ratio - 1) <= square_tolerance:
        shape = "SQUARE"
    else:
        shape = "RECTANGLE"

    print(f"Detected shape is: {shape}")
    
    # Convert pixels to cm if needed, for example assuming 37.8 px = 1 cm (for 96 DPI):
    px_per_cm = 37.8
    width_cm = round(w / px_per_cm, 2)
    height_cm = round(h / px_per_cm, 2)

    return width_cm, height_cm, shape


    