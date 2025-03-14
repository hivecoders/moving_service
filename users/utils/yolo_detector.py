import torch
import cv2
import numpy as np
from ultralytics import YOLO
from pathlib import Path
from utils.volume_weight_estimates import VOLUME_WEIGHT_ESTIMATES  # List of volume and weight of objects

# Load the YOLO model
MODEL_PATH = r"C:\Users\ASUS\Downloads\moving_service-6f1fe82e1dae23fffe41b846cbfef9d00562f496\moving_service-6f1fe82e1dae23fffe41b846cbfef9d00562f496\users\utils\yolov8x.pt"
  # file direction YOLOv8x
model = YOLO(MODEL_PATH)

def detect_objects(image_path, order):
    """
    Image processing for object recognition with YOLO and weight and volume estimation.
    """
    results = model(image_path)  # Running YOLO on the input image
    detected_items = []
    
    img = cv2.imread(image_path)  # Loading an image with OpenCV
    height, width, _ = img.shape  

    for result in results:
        for box in result.boxes.data:
            class_id = int(box[5].item())  # Identified class
            item_name = model.names[class_id]  # Identified class name
            confidence = float(box[4].item())  # YOLO confidence level

            # Estimate weight and volume from database
            item_data = VOLUME_WEIGHT_ESTIMATES.get(item_name, {"volume": 0.5, "weight": 10.0})
            volume = item_data["volume"]
            weight = item_data["weight"]

            # Get box coordinates
            x1, y1, x2, y2 = map(int, box[:4])  
            
            # Draw a box on the image
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(img, f"{item_name} ({confidence:.2f})", (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            # Save detected data
            detected_items.append({
                "item": item_name,
                "volume": volume,
                "weight": weight,
                "confidence": confidence,
                "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2}
            })

    # Save the processed image.
    processed_image_path = f"media/processed/{Path(image_path).stem}_processed.jpg"
    cv2.imwrite(processed_image_path, img)

    return detected_items, processed_image_path
