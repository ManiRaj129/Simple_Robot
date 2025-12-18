import cv2
import numpy as np
import time
import threading
import queue
from tflite_runtime.interpreter import Interpreter
from picamera2 import Picamera2

# Intialize object detection model
MODEL_PATH = "/home/pi/tflite_models/detect.tflite"
LABEL_PATH = "/home/pi/tflite_models/labelmap.txt"
CONF_THRESHOLD = 0.5
FRAME_SIZE = (640, 480)


# Load labels
with open(LABEL_PATH, "r") as f:
    labels = [line.strip() for line in f.readlines()]

# Initialize TFLite interpreter
interpreter = Interpreter(model_path=MODEL_PATH)
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()
in_height, in_width = input_details[0]['shape'][1:3]

# Initialize Pi Camera
picam2 = Picamera2()
picam2.preview_configuration.main.size = FRAME_SIZE
picam2.preview_configuration.main.format = "RGB888"
picam2.configure("preview")
picam2.start()

# Queues for pipeline
frame_q = queue.Queue(maxsize=1)
result_q = queue.Queue(maxsize=1)
stop_flag = False

# THREAD 1 for Capture 
def capture_thread():
    global stop_flag
    while not stop_flag:
        frame = picam2.capture_array()
        if not frame_q.full():
            frame_q.put(frame)

# THREAD 2 for Inference 
def inference_thread():
    global stop_flag
    while not stop_flag:
        if not frame_q.empty():
            frame = frame_q.get()
            resized = cv2.resize(frame, (in_width, in_height))
            input_data = np.expand_dims(resized, axis=0)

            interpreter.set_tensor(input_details[0]['index'], input_data)
            start = time.time()
            interpreter.invoke()
            elapsed = time.time() - start

            boxes = interpreter.get_tensor(output_details[0]['index'])[0]
            classes = interpreter.get_tensor(output_details[1]['index'])[0]
            scores = interpreter.get_tensor(output_details[2]['index'])[0]

            result_q.put((frame, boxes, classes, scores, elapsed))

# THREAD 3 for Display 
def display_thread():
    global stop_flag
    while not stop_flag:
        if not result_q.empty():
            frame, boxes, classes, scores, elapsed = result_q.get()
            for i, score in enumerate(scores):
                if score > CONF_THRESHOLD:
                    ymin, xmin, ymax, xmax = boxes[i]
                    (x1, y1, x2, y2) = (
                        int(xmin * FRAME_SIZE[0]),
                        int(ymin * FRAME_SIZE[1]),
                        int(xmax * FRAME_SIZE[0]),
                        int(ymax * FRAME_SIZE[1]),
                    )
                    label = f"{labels[int(classes[i])]}: {int(score * 100)}%"
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(frame, label, (x1, y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)

            fps_text = f"FPS: {1/elapsed:.1f}"
            cv2.putText(frame, fps_text, (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            cv2.imshow("SSD MobileNet - TFLite (Pi)", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                stop_flag = True

# Execute Threads 
threads = [
    threading.Thread(target=capture_thread, daemon=True),
    threading.Thread(target=inference_thread, daemon=True),
    threading.Thread(target=display_thread, daemon=True)
]

for t in threads:
    t.start()

try:
    while not stop_flag:
        time.sleep(0.1)
except KeyboardInterrupt:
    stop_flag = True

picam2.stop()
cv2.destroyAllWindows()
