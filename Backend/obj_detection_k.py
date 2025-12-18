from ultralytics import YOLO
from Camera import camera

# Load YOLO model
model = camera.get_yolo()

def object_track(target_name:str):
    """
    Returns:
      direction: 'left', 'center', 'right', or None
      area: size of bounding box (used for distance)
    """
    frame = camera.get_frame()
    results = model(frame)

    best_box = None
    best_area = 0

    for r in results:
        for box in r.boxes:
            cls = int(box.cls[0])
            name:str = model.names[cls]

            if name.casefold() != target_name.casefold():
                continue

            x1, y1, x2, y2 = box.xyxy[0]
            area = (x2 - x1) * (y2 - y1)

            # keep the biggest detection (closest)
            if area > best_area:
                best_area = area
                best_box = (x1, y1, x2, y2)

    if best_box is None:
        print("returned nothjing")
        return None, None

    # find center of object
    x1, y1, x2, y2 = best_box
    x_center = (x1 + x2) / 2

    # decide LEFT / CENTER / RIGHT
    if x_center < 640 * 0.33:
        direction = "left"
    elif x_center > 640 * 0.66:
        direction = "right"
    else:
        direction = "center"
    print("gotoTarget: direction")
    return direction, best_area



if __name__ == "__main__":
    print("Starting obstacle detection... Press Ctrl+C to stop.")
    while True:
        frame = picam2.capture_array()
        results = model(frame)

        det_names = []
        for r in results:
            for box in r.boxes:
                cls = int(box.cls[0])
                name = model.names[cls]
                det_names.append(name)

        if det_names:
            print("Detected:", det_names)
        else:
            print("No obstacle detected")
