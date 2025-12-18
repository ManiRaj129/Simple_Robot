#!/usr/bin/env python3
"""
Simple Robot Face with Clear Emotions
======================================

Emotions:
1. neutral  - Relaxed, eyes slightly droopy, small smile
2. happy    - Wide eyes, big smile, rosy cheeks  
3. sad      - Droopy eyes angled down, frown, sad eyebrows
4. surprised - Very wide eyes, small "o" mouth, raised eyebrows
5. angry    - Furrowed brows (V shape over eyes), squinted eyes, grumpy mouth
"""

import cv2
import numpy as np
import time
import random
import sys
import select
from threading import Lock
import asyncio

# ================== Configuration ==================
WINDOW_NAME = "Robot Face"
SCREEN_W, SCREEN_H = 1280, 720

# Colors (BGR)
BG_COLOR = (250, 250, 252)       # Off-white background
EYE_WHITE = (255, 255, 255)      # Sclera
EYE_BLACK = (20, 20, 25)         # Pupil/iris
CHEEK_COLOR = (180, 130, 255)    # Pink cheeks (BGR)
MOUTH_COLOR = (60, 60, 80)       # Mouth outline
TONGUE_COLOR = (140, 110, 230)   # Tongue pink

EMOTION_LIST = ['neutral', 'happy', 'sad', 'surprised', 'angry', 'listening', 'sleeping']
LISTENING_CHEEK = (200, 100, 180)  # Purple cheeks for listening


# ================== Emotion Map ==================
EMOTION_MAP = {
    "neutral": 1,
    "happy": 2,
    "sad": 3,
    "surprised": 4,
    "angry": 5,
    "confused": 3,
    "listening": 6,
    "sleeping": 7,
}

# ================== Simple Face Renderer ==================
class SimpleFace:
    def __init__(self, w=SCREEN_W, h=SCREEN_H):
        self.w, self.h = w, h
        self.cx, self.cy = w // 2, h // 2
        
        # Eye positions
        self.eye_spacing = int(w * 0.22)
        self.eye_y = int(h * 0.38)
        self.eye_radius = int(min(w, h) * 0.12)
        
        # Mouth position
        self.mouth_y = int(h * 0.72)
        self.mouth_w = int(w * 0.20)
        self.is_talking = False
        
    def set_talking(self, talking: bool):
        self.is_talking = talking

    def render(self, emotion: str, mouth_open: float = 0.0, blink: float = 1.0):
        """
        Render face with given emotion.
        
        Args:
            emotion: 'neutral', 'happy', 'sad', 'surprised', 'angry'
            mouth_open: 0.0-1.0 for talking animation
            blink: 1.0 = eyes open, 0.0 = eyes closed
        """
        # Create canvas
        img = np.full((self.h, self.w, 3), BG_COLOR, dtype=np.uint8)
        
        # Draw based on emotion
        if emotion == 'happy':
            self._draw_happy(img, mouth_open if self.is_talking else 0.0, blink)
        elif emotion == 'sad':
            self._draw_sad(img, mouth_open if self.is_talking else 0.0, blink)
        elif emotion == 'surprised':
            self._draw_surprised(img, mouth_open if self.is_talking else 0.0, blink)
        elif emotion == 'angry':
            self._draw_angry(img, mouth_open if self.is_talking else 0.0, blink)
        elif emotion == 'listening':
            self._draw_listening_simple(img, blink)
        elif emotion == 'sleeping':
            self._draw_sleeping(img)
        else:  # neutral
            self._draw_neutral(img, mouth_open if self.is_talking else 0.0, blink)
        
        return img
        
        return img

    def _draw_listening_simple(self, img, blink):
        """Listening: attentive eyes, purple cheeks, small open mouth.

        Kept simple and robust to avoid nested-definition bugs.
        """
        left_x = self.cx - self.eye_spacing
        right_x = self.cx + self.eye_spacing
        # Eyes open (use blink factor)
        openness = max(0.6, blink)
        self._draw_eye(img, left_x, self.eye_y, self.eye_radius, openness)
        self._draw_eye(img, right_x, self.eye_y, self.eye_radius, openness)

        # Purple cheeks
        cheek_y = int(self.h * 0.52)
        cheek_r = int(self.eye_radius * 0.45)
        left_cx = self.cx - self.eye_spacing - int(self.eye_radius * 0.8)
        right_cx = self.cx + self.eye_spacing + int(self.eye_radius * 0.8)
        cv2.circle(img, (left_cx, cheek_y), cheek_r, LISTENING_CHEEK, -1, cv2.LINE_AA)
        cv2.circle(img, (right_cx, cheek_y), cheek_r, LISTENING_CHEEK, -1, cv2.LINE_AA)

        # Small relaxed open mouth
        mouth_h = int(self.h * 0.03)
        cv2.ellipse(img, (self.cx, self.mouth_y), (self.mouth_w // 3, mouth_h), 0, 0, 360, MOUTH_COLOR, -1, cv2.LINE_AA)

    def _draw_sleeping(self, img):
        """Sleeping: closed eyes, relaxed mouth, subtle 'Z' indicator."""
        left_x = self.cx - self.eye_spacing
        right_x = self.cx + self.eye_spacing

        # Draw closed eyelids (simple curved lines)
        brow_y = self.eye_y
        cv2.ellipse(img, (left_x, brow_y), (self.eye_radius, int(self.eye_radius * 0.3)), 0, 0, 180, (80, 80, 100), 6, cv2.LINE_AA)
        cv2.ellipse(img, (right_x, brow_y), (self.eye_radius, int(self.eye_radius * 0.3)), 0, 0, 180, (80, 80, 100), 6, cv2.LINE_AA)

        # No cheeks, relaxed mouth (small straight line)
        cv2.line(img, (self.cx - self.mouth_w // 4, self.mouth_y), (self.cx + self.mouth_w // 4, self.mouth_y), (100, 100, 120), 4, cv2.LINE_AA)

        # 'Z' letters to indicate sleeping (top-right corner)
        z_x = int(self.cx + self.eye_spacing * 1.4)
        z_y = int(self.eye_y - self.eye_radius * 0.8)
        cv2.putText(img, "Z", (z_x, z_y), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (120, 120, 160), 3, cv2.LINE_AA)
        cv2.putText(img, "Z", (z_x + 30, z_y - 30), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (150, 150, 180), 2, cv2.LINE_AA)
    
    def _draw_eye(self, img, cx, cy, radius, openness=1.0, pupil_offset_y=0):
        """Draw a simple eye with white sclera and black pupil."""
        # Sclera (white)
        cv2.circle(img, (cx, cy), radius, EYE_WHITE, -1, cv2.LINE_AA)
        cv2.circle(img, (cx, cy), radius, (200, 200, 210), 3, cv2.LINE_AA)
        
        # Pupil (black) - can be offset for looking up/down
        pupil_r = int(radius * 0.5)
        pupil_y = cy + int(pupil_offset_y * radius * 0.3)
        cv2.circle(img, (cx, pupil_y), pupil_r, EYE_BLACK, -1, cv2.LINE_AA)
        
        # Highlight
        hi_x = cx + int(radius * 0.25)
        hi_y = pupil_y - int(radius * 0.25)
        cv2.circle(img, (hi_x, hi_y), int(radius * 0.15), (255, 255, 255), -1, cv2.LINE_AA)
        
        # Eyelid cover (for blinking/squinting)
        if openness < 1.0:
            lid_drop = int(radius * 2 * (1 - openness))
            # Upper lid
            pts = np.array([
                [cx - radius - 10, cy - radius - 20],
                [cx + radius + 10, cy - radius - 20],
                [cx + radius + 10, cy - radius + lid_drop],
                [cx - radius - 10, cy - radius + lid_drop],
            ])
            cv2.fillPoly(img, [pts], BG_COLOR)
            # Lid line
            if openness > 0.1:
                cv2.line(img, (cx - radius, cy - radius + lid_drop), 
                        (cx + radius, cy - radius + lid_drop), (80, 80, 100), 3, cv2.LINE_AA)
    
    def _draw_cheeks(self, img):
        """Draw rosy cheeks."""
        cheek_y = int(self.h * 0.52)
        cheek_r = int(self.eye_radius * 0.5)
        left_x = self.cx - self.eye_spacing - int(self.eye_radius * 0.8)
        right_x = self.cx + self.eye_spacing + int(self.eye_radius * 0.8)
        cv2.circle(img, (left_x, cheek_y), cheek_r, CHEEK_COLOR, -1, cv2.LINE_AA)
        cv2.circle(img, (right_x, cheek_y), cheek_r, CHEEK_COLOR, -1, cv2.LINE_AA)
    
    def _draw_smile(self, img, intensity=1.0):
        """Draw a curved smile."""
        pts = []
        for i in range(50):
            t = i / 49
            x = int(self.cx - self.mouth_w + 2 * self.mouth_w * t)
            curve = int(self.h * 0.04 * intensity * (1 - (2*t - 1)**2))
            y = int(self.mouth_y + curve)
            pts.append([x, y])
        cv2.polylines(img, [np.array(pts)], False, MOUTH_COLOR, 5, cv2.LINE_AA)
    
    def _draw_frown(self, img, intensity=1.0):
        """Draw a curved frown."""
        pts = []
        for i in range(50):
            t = i / 49
            x = int(self.cx - self.mouth_w * 0.7 + 2 * self.mouth_w * 0.7 * t)
            curve = int(self.h * 0.03 * intensity * (1 - (2*t - 1)**2))
            y = int(self.mouth_y - curve)  # curve up = frown
            pts.append([x, y])
        cv2.polylines(img, [np.array(pts)], False, MOUTH_COLOR, 5, cv2.LINE_AA)
    
    def _draw_open_mouth(self, img, openness=0.5):
        """Draw open mouth (ellipse)."""
        mouth_h = int(self.h * 0.06 * (0.3 + openness * 0.7))
        cv2.ellipse(img, (self.cx, self.mouth_y), (self.mouth_w, mouth_h), 
                   0, 0, 360, MOUTH_COLOR, -1, cv2.LINE_AA)
        # Tongue
        if openness > 0.3:
            tongue_w = int(self.mouth_w * 0.6)
            tongue_h = int(mouth_h * 0.5)
            cv2.ellipse(img, (self.cx, self.mouth_y + int(mouth_h * 0.3)), 
                       (tongue_w, tongue_h), 0, 0, 180, TONGUE_COLOR, -1, cv2.LINE_AA)
    
    def _draw_o_mouth(self, img):
        """Draw small 'o' mouth for surprise."""
        r = int(self.h * 0.04)
        cv2.circle(img, (self.cx, self.mouth_y), r, MOUTH_COLOR, -1, cv2.LINE_AA)
    
    def _draw_eyebrow(self, img, cx, cy, angle=0, angry=False):
        """Draw an eyebrow. angle: positive = outer raised, negative = inner raised."""
        brow_w = int(self.eye_radius * 1.2)
        brow_y = cy - self.eye_radius - int(self.h * 0.04)
        
        x1 = cx - brow_w // 2
        x2 = cx + brow_w // 2
        
        # Angle the brow
        y1 = brow_y + int(angle * self.h * 0.03)
        y2 = brow_y - int(angle * self.h * 0.03)
        
        thickness = 6 if angry else 4
        cv2.line(img, (x1, y1), (x2, y2), (60, 60, 80), thickness, cv2.LINE_AA)
    
    # ================== Emotion Renders ==================
    
    def _draw_neutral(self, img, mouth_open, blink):
        """Neutral: relaxed eyes, small smile."""
        left_x = self.cx - self.eye_spacing
        right_x = self.cx + self.eye_spacing
        
        # Eyes slightly relaxed (0.85 open)
        openness = 0.85 * blink
        self._draw_eye(img, left_x, self.eye_y, self.eye_radius, openness)
        self._draw_eye(img, right_x, self.eye_y, self.eye_radius, openness)
        
        # Light cheeks
        self._draw_cheeks(img)
        
        # Small smile or open mouth
        if mouth_open > 0.1:
            self._draw_open_mouth(img, mouth_open)
        else:
            self._draw_smile(img, 0.6)
    
    def _draw_happy(self, img, mouth_open, blink):
        """Happy: wide eyes, big smile, rosy cheeks."""
        left_x = self.cx - self.eye_spacing
        right_x = self.cx + self.eye_spacing
        
        # Wide open eyes
        self._draw_eye(img, left_x, self.eye_y, self.eye_radius, blink)
        self._draw_eye(img, right_x, self.eye_y, self.eye_radius, blink)
        
        # Cheeks
        self._draw_cheeks(img)
        
        # Big smile or open happy mouth
        if mouth_open > 0.1:
            self._draw_open_mouth(img, mouth_open)
        else:
            self._draw_smile(img, 1.0)
    
    def _draw_sad(self, img, mouth_open, blink):
        """Sad: droopy eyes (angled down at outer corners), frown, no cheeks."""
        left_x = self.cx - self.eye_spacing
        right_x = self.cx + self.eye_spacing
        
        # Eyes looking down, half closed
        openness = 0.6 * blink
        self._draw_eye(img, left_x, self.eye_y, self.eye_radius, openness, pupil_offset_y=0.5)
        self._draw_eye(img, right_x, self.eye_y, self.eye_radius, openness, pupil_offset_y=0.5)
        
        # Sad eyebrows (outer down)
        self._draw_eyebrow(img, left_x, self.eye_y, angle=-0.8)
        self._draw_eyebrow(img, right_x, self.eye_y, angle=0.8)
        
        # Frown
        if mouth_open > 0.1:
            self._draw_open_mouth(img, mouth_open * 0.7)
        else:
            self._draw_frown(img, 1.0)
    
    def _draw_surprised(self, img, mouth_open, blink):
        """Surprised: very wide eyes, raised eyebrows, 'o' mouth."""
        left_x = self.cx - self.eye_spacing
        right_x = self.cx + self.eye_spacing
        
        # Big wide eyes
        big_r = int(self.eye_radius * 1.15)
        self._draw_eye(img, left_x, self.eye_y, big_r, blink, pupil_offset_y=-0.3)
        self._draw_eye(img, right_x, self.eye_y, big_r, blink, pupil_offset_y=-0.3)
        
        # Raised eyebrows (both ends up, arched)
        brow_y = self.eye_y - big_r - int(self.h * 0.06)
        brow_w = int(big_r * 1.3)
        # Draw arched brows
        for side in [-1, 1]:
            bx = self.cx + side * self.eye_spacing
            pts = []
            for i in range(30):
                t = i / 29
                x = int(bx - brow_w//2 + brow_w * t)
                arch = int(self.h * 0.02 * (1 - (2*t - 1)**2))
                y = brow_y - arch
                pts.append([x, y])
            cv2.polylines(img, [np.array(pts)], False, (60, 60, 80), 4, cv2.LINE_AA)
        
        # 'O' mouth
        self._draw_o_mouth(img)
    
    def _draw_angry(self, img, mouth_open, blink):
        """Angry: furrowed V-shaped brows, squinted eyes, grumpy mouth."""
        left_x = self.cx - self.eye_spacing
        right_x = self.cx + self.eye_spacing
        
        # Squinted eyes
        openness = 0.5 * blink
        self._draw_eye(img, left_x, self.eye_y, self.eye_radius, openness)
        self._draw_eye(img, right_x, self.eye_y, self.eye_radius, openness)
        
        # Angry V-shaped brows (inner down, outer up)
        self._draw_eyebrow(img, left_x, self.eye_y, angle=1.2, angry=True)   # left: inner down
        self._draw_eyebrow(img, right_x, self.eye_y, angle=-1.2, angry=True) # right: inner down
        
        # Grumpy straight/slight frown mouth
        if mouth_open > 0.1:
            self._draw_open_mouth(img, mouth_open * 0.6)
        else:
            # Straight grumpy line
            y = self.mouth_y
            cv2.line(img, (self.cx - int(self.mouth_w * 0.6), y), 
                    (self.cx + int(self.mouth_w * 0.6), y), MOUTH_COLOR, 5, cv2.LINE_AA)


# ================== Animation Controllers ==================

class TalkingAnimation:
    """Generates random mouth movements for talking."""
    def __init__(self):
        self.syllables = []
        self.current = 0
        self.timer = 0
        self._generate()
    
    def _generate(self):
        """Generate a new phrase pattern."""
        self.syllables = []
        for _ in range(random.randint(3, 7)):
            self.syllables.append({
                'duration': random.uniform(0.12, 0.35),
                'openness': random.uniform(0.3, 0.9)
            })
        # Pause at end
        self.syllables.append({'duration': random.uniform(0.3, 0.8), 'openness': 0.0})
        self.current = 0
        self.timer = 0
    
    def update(self, dt) -> float:
        """Update and return current mouth openness."""
        if self.current >= len(self.syllables):
            self._generate()
            return 0.0
        
        s = self.syllables[self.current]
        self.timer += dt
        
        if self.timer >= s['duration']:
            self.timer = 0
            self.current += 1
            if self.current >= len(self.syllables):
                return 0.0
            s = self.syllables[self.current]
        
        # Smooth in/out
        t = self.timer / s['duration']
        ease = t * 2 if t < 0.5 else 2 - t * 2
        return s['openness'] * ease
    
    def reset(self):
        self._generate()


class BlinkAnimation:
    """Controls periodic blinking."""
    def __init__(self, interval=3.0, duration=0.18):
        self.interval = interval
        self.duration = duration
        self.timer = 0
        self.blink_timer = -1
    
    def update(self, dt) -> float:
        """Update and return eye openness (1.0 = open, 0.0 = closed)."""
        if self.blink_timer >= 0:
            self.blink_timer += dt
            if self.blink_timer >= self.duration:
                self.blink_timer = -1
                self.timer = 0
            else:
                # Close then open
                t = self.blink_timer / self.duration
                if t < 0.4:
                    return 1.0 - (t / 0.4)
                elif t < 0.5:
                    return 0.0
                else:
                    return (t - 0.5) / 0.5
        else:
            self.timer += dt
            if self.timer >= self.interval:
                self.blink_timer = 0
        
        return 1.0


# ================== Main Robot Face Controller ==================

class RobotFace:
    """Main face controller with emotion support."""
    
    def __init__(self):
        self.face = SimpleFace()
        self.is_talking = False
        self.talking = TalkingAnimation()
        self.blink = BlinkAnimation()
        self.emotion = 'surprised'
        self.lock = Lock()
        self.last_time = time.time()
        
        # Setup window
        cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
        cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    
    def update_emotion(self, emotion_num: int):
        """
        Set emotion by number (thread-safe).
        1=neutral, 2=happy, 3=sad, 4=surprised, 5=angry, 6 = listening, 7 = sleeping
        """
        with self.lock:
            if 1 <= emotion_num <= 5:
                self.emotion = EMOTION_LIST[emotion_num - 1]
                self.talking.reset()
            elif emotion_num == 6:
                self.emotion = 'listening'
            elif emotion_num == 7:
                self.emotion = 'sleeping'
                
    def set_talking(self, talking: bool):
        """Enable/disable mouth animation while talking."""
        with self.lock:
            self.is_talking = talking
    
    def run(self):
        """Run face display loop (blocking)."""
        cv2.destroyAllWindows()
        try:
            while True:
                self.run_step()
                time.sleep(1)
        except KeyboardInterrupt:
            print("closed")
    
    async def run_face_async(self):
        """Face rendering loop."""
        while True:
            self.run_step()
            await asyncio.sleep(0.001)


    async def schedule_sleeping(self, sleepAfter:str):
        """Set face to sleeping after followup window expires."""
        await asyncio.sleep(sleepAfter+ 1)
        self.update_emotion(EMOTION_MAP.get("sleeping", 7))
    
    def run_step(self) -> bool:
        """Run one frame. Returns False if should exit."""
        now = time.time()
        dt = now - self.last_time
        self.last_time = now
        
        with self.lock:
            emotion = self.emotion
        
        # Update animations
        mouth = self.talking.update(dt) if self.is_talking else 0.0
        blink = self.blink.update(dt)
        
        # Render
        img = self.face.render(emotion, mouth, blink)
        cv2.imshow(WINDOW_NAME, img)
        
        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC
            return False
        elif key == ord('1'):
            self.update_emotion(1)
        elif key == ord('2'):
            self.update_emotion(2)
        elif key == ord('3'):
            self.update_emotion(3)
        elif key == ord('4'):
            self.update_emotion(4)
        elif key == ord('5'):
            self.update_emotion(5)
        
        # # Also check terminal input (stdin)
        # if select.select([sys.stdin], [], [], 0)[0]:
        #     line = sys.stdin.readline().strip()
        #     if line in ('1', '2', '3', '4', '5'):
        #         self.update_emotion(int(line))
        #         print(f"Emotion: {EMOTION_LIST[int(line)-1]}")
        #     elif line == 'q':
        #         return False
        #return True        
        



# ================== Main ==================

if __name__ == "__main__":
    face = RobotFace()
    # face.run()
    asyncio.run(face.run_face_async())
