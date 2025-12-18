import cv2
import threading
import subprocess
import time
import numpy as np
from ultralytics import YOLO

class CameraManager:
    #ls -l /dev/v4l/by-id/ (should choose lowest index video device)
    CAMERA_PATH = "/dev/v4l/by-id/usb-046d_HD_Pro_Webcam_C920_33DA883F-video-index0"

    def __init__(self, src=CAMERA_PATH, width=1280, height=720, fps=30, virt_cam="/dev/video8"):
        self.src = src
        self.width = width
        self.height = height
        self.fps = fps
        self.virt_cam = virt_cam
        self.model = YOLO("yolov8n.pt")

        # --- OpenCV camera using V4L2 (owns the camera exclusively) ---
        self.cap = cv2.VideoCapture(self.src, cv2.CAP_V4L2)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_FPS, fps)
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"YUYV"))

        if not self.cap.isOpened():
            raise RuntimeError(f"ERROR: Cannot open camera {self.src}")

        # --- FFmpeg process writing to virtual camera ---
        self.ffmpeg = subprocess.Popen(
            [
                "ffmpeg",
                "-loglevel", "error",
                "-y",
                "-f", "rawvideo",
                "-pix_fmt", "bgr24",     # from OpenCV
                "-s", f"{width}x{height}",
                "-r", str(fps),
                "-i", "-",               # stdin
                "-f", "v4l2",
                "-pix_fmt", "yuyv422",
                self.virt_cam,
            ],
            stdin=subprocess.PIPE
        )

        self.latest = None
        self._running = True

        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def _loop(self):
        """Continuously read frames and feed the virtual camera."""
        wait = 1.0 / self.fps

        while self._running:
            ret, frame = self.cap.read()
            if not ret:
                continue

            # Store for YOLO/detection use
            self.latest = frame  

            # Stream to virtual camera using ffmpeg
            try:
                self.ffmpeg.stdin.write(frame.tobytes())
            except BrokenPipeError:
                print("FFmpeg pipe closed")
                break

            time.sleep(wait)

    def get_frame(self):
        """Return the most recent frame."""
        return self.latest
    
    def get_yolo(self):
        return self.model

    def stop(self):
        self._running = False
        
        try:
            self.thread.join(timeout=1)
            self.cap.release()
            self.ffmpeg.stdin.close()
            self.ffmpeg.terminate()
        except:
            pass


#Need to move to the main
camera = CameraManager() 

# Test
if __name__=="__main__":
    camera = CameraManager() 

    try:
        while True:
            frame = camera.get_frame()
            if frame is None:
                continue

            # Run YOLO here
            # results = model(frame)

            # Show for debug
            cv2.imshow("Live", frame)
            
    except KeyboardInterrupt:
        print("Stopping ")
    finally:
        camera.stop()
        

