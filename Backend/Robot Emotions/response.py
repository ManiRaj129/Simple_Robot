from RobotEmotions import RobotFace
import time

face = RobotFace()

# Example: cycle through emotions 1–5
emotions_to_test = [5,5,5, 5]

for emotion_number in emotions_to_test:
    face.update_emotion(emotion_number)
    print(f"Emotion {emotion_number}")
    start = time.time()
    while time.time() - start < 3:  # run for 3 seconds per emotion
        if not face.run_step():
            exit(0)  # ESC pressed
