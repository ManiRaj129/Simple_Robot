import cv2
import numpy as np
import time
import random
from threading import Lock

# ---- Emotions ----
EMOTIONS = {
    'neutral':   {'eye_openness': 0.85, 'pupil_x': 0.0, 'pupil_y': 0.00}, 
    'happy':     {'eye_openness': 0.85, 'pupil_x': 0.0, 'pupil_y': 0.00},  
    'sad':       {'eye_openness': 0.55, 'pupil_x': 0.0, 'pupil_y': 0.20},
    'surprised': {'eye_openness': 1.00, 'pupil_x': 0.0, 'pupil_y':-0.20},
    'angry':     {'eye_openness': 0.50, 'pupil_x': 0.0, 'pupil_y': 0.10},
}
EMOTION_LIST = ['neutral', 'happy', 'sad', 'surprised', 'angry']

# ---- Renderer ----
class RobotRenderer:
    def __init__(self, w=1280, h=720):
        self.w, self.h = w, h
        self.cx, self.cy = w // 2, h // 2

        self.FACE_COL   = (248, 248, 252)   # off-white
        self.LID_FILL   = self.FACE_COL     # match face EXACTLY during blink
        self.LID_EDGE   = (60, 60, 78)      # edge lines (disabled during blink)
        self.RIM_COLOR  = (235, 235, 240)   # sclera rim (outer)
        self.RING_COLOR = (205, 210, 220)   # sclera ring (inner)
        self.IRIS_COLOR = (15, 15, 20)
        self.HI_COLOR   = (255, 255, 255)

        # Line styles
        self.EDGE_AA   = cv2.LINE_AA  # use AA for outermost edges when not blinking
        self.EDGE_FLAT = cv2.LINE_8   # crisp (no AA) for interior fills

    # ---------- closed eye for "neutral-as-still" ----------
    def _draw_closed_eye_with_lashes(self, img, center_x, center_y, side_sign):
        lid_half_w = int(self.w * 0.12)
        lid_thick  = max(3, int(self.h * 0.010))
        pts = []
        for i in range(41):
            t = i / 40.0
            x = int(center_x - lid_half_w + 2 * lid_half_w * t)
            drop = int(self.h * 0.012 * (1 - (2 * t - 1) ** 2))
            y = center_y + drop
            pts.append((x, y))
        cv2.polylines(img, [np.array(pts)], False, (20, 20, 20), lid_thick, lineType=self.EDGE_AA)

        # Lashes = flat (keeps them crisp)
        lash_len  = int(self.h * 0.045)
        lash_thk  = max(2, int(self.h * 0.008))
        for o in [-0.45, -0.22, 0.0, 0.22, 0.45]:
            x0 = int(center_x + o * (2 * lid_half_w))
            t = (o + 1) / 2.0
            base_drop = int(self.h * 0.012 * (1 - (2 * t - 1) ** 2))
            y0 = center_y + base_drop
            outward = int(side_sign * (self.w * 0.012) * (0.4 + abs(o)))
            x1, y1 = x0 + outward, y0 + lash_len
            cv2.line(img, (x0, y0), (x1, y1), (25, 25, 25), lash_thk, lineType=self.EDGE_FLAT)

    # ---------- eye base (returns iris center) ----------
    def _draw_eye(self, img, cx, cy, r, px_off, py_off, hi_scale=1.0, aa=True):
        line_type = self.EDGE_AA if aa else self.EDGE_FLAT
        cv2.circle(img, (cx, cy), r + 7, self.RIM_COLOR, -1, lineType=line_type)
        cv2.circle(img, (cx, cy), r + 4, self.RING_COLOR, -1, lineType=line_type)

        ex = cx + int(px_off * r * 0.45)
        ey = cy + int(py_off * r * 0.45)
        cv2.circle(img, (ex, ey), r, self.IRIS_COLOR, -1, lineType=line_type)

        hi_r1 = int(r * 0.26 * hi_scale)
        hi_r2 = int(r * 0.12 * hi_scale)
        cv2.circle(img, (ex + int(r * 0.34), ey - int(r * 0.34)), hi_r1, self.HI_COLOR, -1, lineType=line_type)
        cv2.circle(img, (ex + int(r * 0.12), ey - int(r * 0.42)), hi_r2, self.HI_COLOR, -1, lineType=line_type)

        return ex, ey

    # ---------- sparkle for 'surprised' (solid white; no alpha) ----------
    def _add_surprise_sparkle(self, img, ex, ey, r, aa=True):
        lt = self.EDGE_AA if aa else self.EDGE_FLAT
        # two small dots
        cv2.circle(img, (ex - int(0.22*r), ey - int(0.06*r)), max(1, int(0.05*r)), self.HI_COLOR, -1, lineType=lt)
        cv2.circle(img, (ex + int(0.12*r), ey + int(0.16*r)), max(1, int(0.04*r)), self.HI_COLOR, -1, lineType=lt)
        # tiny plus-star
        s = max(2, int(0.10*r))
        cx, cy = ex - int(0.10*r), ey - int(0.12*r)
        cv2.line(img, (cx - s, cy), (cx + s, cy), self.HI_COLOR, 2, lineType=lt)
        cv2.line(img, (cx, cy - s), (cx, cy + s), self.HI_COLOR, 2, lineType=lt)

    # --------- OPAQUE eyelids with blink-aware edge toggle ----------
    def _draw_eyelids(self, img, cx, cy, r, openness, style='normal', side_sign=0,
                      draw_upper=True, draw_lower=True, edge_on=True,
                      upper_scale=1.05, lower_scale=0.45):
        close_amt = clamp(1.0 - clamp(openness, 0.05, 1.0), 0.0, 1.0)

        # style tuning
        if style == 'happy':
            upper_scale, lower_scale = 0.70, 0.00
        elif style == 'sad':
            upper_scale, lower_scale = 1.30, 0.70
        elif style == 'angry':
            upper_scale, lower_scale = 1.45, 0.00   # upper-only
        elif style == 'surprised':
            upper_scale, lower_scale = 0.18, 0.08

        upper = close_amt * upper_scale if draw_upper else 0.0
        lower = close_amt * lower_scale if draw_lower else 0.0

        sad_bias   = r * 0.24
        angry_bias = r * 0.28

        xL, xR = cx - r - 10, cx + r + 10

        # ----- Upper lid -----
        cover_u = int(r * upper)
        if cover_u > 0:
            steps = 56
            arc_u = []
            for i in range(steps + 1):
                t = i / steps
                x = int(lerp(xL, xR, t))
                if style == 'angry':
                    mid = (xL + xR)//2
                    slope = -0.28 if (side_sign == -1 and x <= mid) or (side_sign == +1 and x >= mid) else 0.12
                    y = (cy - r) + int(cover_u * (1 - ((x - cx) / float(r)) ** 2)) + int(slope * abs(x - cx))
                    if side_sign != 0:
                        inner_weight = (t if side_sign == -1 else (1 - t))
                        y += int(angry_bias * inner_weight * 0.45)
                else:
                    y = (cy - r) + int(cover_u * (1 - ((x - cx) / float(r)) ** 2))
                    if style == 'sad':
                        y += int(sad_bias * abs(2*t - 1) * 0.30)
                arc_u.append((x, y))

            fill_poly = [(xL, 0), (xR, 0)] + arc_u[::-1]
            cv2.fillPoly(img, [np.array(fill_poly, np.int32)], self.LID_FILL, lineType=self.EDGE_FLAT)

            if edge_on:
                cv2.polylines(img, [np.array(arc_u, np.int32)], False, self.LID_EDGE, 3, lineType=self.EDGE_AA)

        # ----- Lower lid -----
        cover_l = int(r * lower)
        if cover_l > 0:
            steps_l = 44
            arc_l = []
            for i in range(steps_l + 1):
                t = i / steps_l
                x = int(lerp(xL, xR, t))
                y = (cy + r) - int(cover_l * (1 - ((x - cx) / float(r)) ** 2))
                if style == 'sad':
                    y -= int(sad_bias * abs(2*t - 1) * 0.20)
                arc_l.append((x, y))

            fill_poly = [(xL, self.h), (xR, self.h)] + arc_l
            cv2.fillPoly(img, [np.array(fill_poly, np.int32)], self.LID_FILL, lineType=self.EDGE_FLAT)

            if edge_on:
                cv2.polylines(img, [np.array(arc_l, np.int32)], False, self.LID_EDGE, 2, lineType=self.EDGE_AA)

    # ---------- mouths ----------
    def _draw_mouth_closed_smile(self, img, mx, my, width, intensity=1.0):
        pts = []
        curve = int(self.h * 0.05 * intensity)
        for i in range(50):
            t = i / 49
            x = int(mx - width + 2 * width * t)
            y = int(my + curve * (1 - (2 * t - 1) ** 2))
            pts.append((x, y))
        cv2.polylines(img, [np.array(pts)], False, (40, 40, 40), 6, lineType=self.EDGE_AA)

    def _draw_mouth_with_tongue(self, img, mx, my, width, amount):
        mouth_h  = int(self.h * (0.10 + 0.10 * amount))
        tongue_h = int(mouth_h * 0.55)
        tongue_w = int(width * 0.55)
        cv2.ellipse(img, (mx, my), (width, mouth_h), 0, 0, 180, (80, 60, 160), -1, lineType=self.EDGE_AA)
        cv2.ellipse(img, (mx, my + mouth_h // 2), (tongue_w, tongue_h), 0, 0, 180, (140, 110, 230), -1, lineType=self.EDGE_AA)
        cv2.ellipse(img, (mx, my), (width, mouth_h), 0, 0, 180, (70, 70, 90), 3, lineType=self.EDGE_AA)

    # ---------- main render ----------
    def render(self, p, emotion_name='neutral'):
        c = np.ones((self.h, self.w, 3), np.uint8)
        c[:] = self.FACE_COL

        # Eye anchors
        eye_y_open   = int(self.cy - self.h * 0.18)
        eye_y_closed = int(self.cy - self.h * 0.12)
        eye_x_off    = int(self.w * 0.23)
        eye_radius   = int(min(self.w, self.h) * 0.11)

        is_blinking = p.get('is_blinking', False)

        if p.get('closed_eyes', False):
            # Neutral behaves like STILL now: closed lids + lashes only (no eyeballs drawn anywhere).
            self._draw_closed_eye_with_lashes(c, self.cx - eye_x_off, eye_y_closed, -1)
            self._draw_closed_eye_with_lashes(c, self.cx + eye_x_off, eye_y_closed, +1)
        else:
            # Eye base (AA OFF during blink to avoid bands)
            hi_scale = 1.0
            if emotion_name == 'sad': hi_scale = 0.82
            elif emotion_name == 'surprised': hi_scale = 1.15

            lx, ly = self._draw_eye(c, self.cx - eye_x_off, eye_y_open, eye_radius,
                                    p['pupil_x'], p['pupil_y'], hi_scale=hi_scale, aa=not is_blinking)
            rx, ry = self._draw_eye(c, self.cx + eye_x_off, eye_y_open, eye_radius,
                                    p['pupil_x'], p['pupil_y'], hi_scale=hi_scale, aa=not is_blinking)

            # Surprise-only sparkle (skip during blink)
            if emotion_name == 'surprised' and not is_blinking:
                self._add_surprise_sparkle(c, lx, ly, eye_radius, aa=True)
                self._add_surprise_sparkle(c, rx, ry, eye_radius, aa=True)

            # Eyelids — during blink: edge_off + fills equal to face color
            edge_on = not is_blinking

            if emotion_name == 'neutral':
                # STILL-like: no lids overlay path here; eyes are never rendered in this branch
                # because neutral is handled above via closed_eyes True (in RobotFace).
                pass
            elif emotion_name == 'happy':
                # Normally: no eyelids (old neutral look).
                # BUT: during a blink, we must draw lids so the blink is visible.
                if is_blinking:
                    self._draw_eyelids(c, self.cx - eye_x_off, eye_y_open, eye_radius,
                                       p['eye_openness'], style='normal',
                                       side_sign=-1, draw_upper=True, draw_lower=True, edge_on=edge_on)
                    self._draw_eyelids(c, self.cx + eye_x_off, eye_y_open, eye_radius,
                                       p['eye_openness'], style='normal',
                                       side_sign=+1, draw_upper=True, draw_lower=True, edge_on=edge_on)
                # If not blinking → do nothing (eyes stay fully visible)
            elif emotion_name == 'sad':
                self._draw_eyelids(c, self.cx - eye_x_off, eye_y_open, eye_radius, p['eye_openness'],
                                   style='sad', side_sign=-1, draw_upper=True, draw_lower=True, edge_on=edge_on)
                self._draw_eyelids(c, self.cx + eye_x_off, eye_y_open, eye_radius, p['eye_openness'],
                                   style='sad', side_sign=+1, draw_upper=True, draw_lower=True, edge_on=edge_on)
            elif emotion_name == 'angry':
                self._draw_eyelids(c, self.cx - eye_x_off, eye_y_open, eye_radius, p['eye_openness'],
                                   style='angry', side_sign=-1, draw_upper=True, draw_lower=False, edge_on=edge_on)
                self._draw_eyelids(c, self.cx + eye_x_off, eye_y_open, eye_radius, p['eye_openness'],
                                   style='angry', side_sign=+1, draw_upper=True, draw_lower=False, edge_on=edge_on)
                self._add_angry_forehead_wrinkles(c)
            elif emotion_name == 'surprised':
                self._draw_eyelids(c, self.cx - eye_x_off, eye_y_open, eye_radius, p['eye_openness'],
                                   style='surprised', side_sign=-1, draw_upper=True, draw_lower=True, edge_on=edge_on)
                self._draw_eyelids(c, self.cx + eye_x_off, eye_y_open, eye_radius, p['eye_openness'],
                                   style='surprised', side_sign=+1, draw_upper=True, draw_lower=True, edge_on=edge_on)
            else:
                self._draw_eyelids(c, self.cx - eye_x_off, eye_y_open, eye_radius, p['eye_openness'], style='normal', edge_on=edge_on)
                self._draw_eyelids(c, self.cx + eye_x_off, eye_y_open, eye_radius, p['eye_openness'], style='normal', edge_on=edge_on)

        # Cheeks (skip for SAD and ANGRY)
        if emotion_name not in ('sad', 'angry'):
            screen_margin = int(self.w * 0.06)
            eye_inner_x = self.cx - eye_x_off
            cheek_left_x  = (screen_margin + eye_inner_x) // 2
            cheek_right_x = self.w - cheek_left_x
            cheek_y = int(self.cy + self.h * 0.04)
            cheek_r = int(min(self.w, self.h) * 0.055)
            cheek_color = (180, 120, 255)
            cv2.circle(c, (cheek_left_x,  cheek_y), cheek_r, cheek_color, -1, lineType=self.EDGE_AA)
            cv2.circle(c, (cheek_right_x, cheek_y), cheek_r, cheek_color, -1, lineType=self.EDGE_AA)

        # Mouth
        mx, my = self.cx, int(self.cy + self.h * 0.28)
        mouth_w = int(self.w * 0.26)
        if p.get('closed_eyes', False):
            self._draw_mouth_closed_smile(c, mx, my, mouth_w, intensity=1.0)
        else:
            self._draw_mouth_with_tongue(c, mx, my, mouth_w, p['mouth_open'])

        return c

    # Angry forehead wrinkles (simple lines)
    def _add_angry_forehead_wrinkles(self, img):
        span_x = int(self.w * 0.56)
        xL = self.cx - span_x // 2
        xR = self.cx + span_x // 2
        base_y = int(self.cy - self.h * 0.30)
        gap = int(self.h * 0.025)
        num_lines = 3
        edge_col  = (40, 40, 60)
        edge_th   = 3
        for k in range(num_lines):
            y0 = base_y - k * gap
            pts = []
            steps = 64
            for i in range(steps + 1):
                t = i / steps
                x = int(lerp(xL, xR, t))
                arch = int(self.h * 0.010 * (1 - (2*t - 1)**2))
                y = y0 - arch
                pts.append((x, y))
            cv2.polylines(img, [np.array(pts, np.int32)], False, edge_col, edge_th, lineType=self.EDGE_AA)

# ---- Talking animation ----
class TalkingPattern:
    def __init__(self): self.reset()
    def reset(self):
        self.syllables, self.current_syllable, self.syllable_timer = [], 0, 0
        self.generate_phrase()
    def generate_phrase(self):
        for _ in range(random.randint(3, 8)):
            duration, openness = random.uniform(0.15, 0.4), random.uniform(0.3, 0.9)
            self.syllables.append({'duration': duration, 'openness': openness})
        self.syllables.append({'duration': random.uniform(0.4, 1.0), 'openness': 0.0})
    def get_mouth_openness(self, dt):
        if self.current_syllable >= len(self.syllables):
            self.reset(); return 0.0
        s = self.syllables[self.current_syllable]; self.syllable_timer += dt
        if self.syllable_timer >= s['duration']:
            self.syllable_timer = 0; self.current_syllable += 1
            if self.current_syllable >= len(self.syllables): return 0.0
            s = self.syllables[self.current_syllable]
        t = self.syllable_timer / s['duration']
        return s['openness'] * (t*2 if t < 0.5 else (2 - 2*t))

# ---- Blink Controller (equal-interval, eased) ----
class BlinkController:
    def __init__(self, period=3.0, duration=0.20, min_hold=0.02):
        self.period = float(period)
        self.duration = float(duration)
        self.min_hold = float(min_hold)
        self.timer = 0.0
        self.blink_t = -1.0

    def update(self, dt, allow=True):
        if not allow:
            self.timer = 0.0
            self.blink_t = -1.0
            return 1.0, False

        if self.blink_t >= 0.0:
            self.blink_t += dt
            if self.blink_t >= self.duration:
                self.blink_t = -1.0
                self.timer = 0.0
        else:
            self.timer += dt
            if self.timer >= self.period:
                self.blink_t = 0.0

        if self.blink_t < 0.0:
            return 1.0, False

        u = clamp(self.blink_t / max(1e-6, self.duration), 0.0, 1.0)
        close_phase = 0.45
        open_phase  = 0.45
        hold_phase  = 1.0 - (close_phase + open_phase)

        if u < close_phase:
            t = u / close_phase
            return 1.0 - smooth01(t), True
        elif u < close_phase + hold_phase:
            return 0.0, True
        else:
            t = (u - close_phase - hold_phase) / open_phase
            return smooth01(t), True

# ---- Utility helpers ----
def lerp(a, b, t): return a + (b - a) * t
def clamp(x, mi, ma): return max(mi, min(ma, x))
def smooth01(t):
    t = clamp(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)

# ---- Robot Face Controller ----
class RobotFace:
    WINDOW = "Robot Face"
    def __init__(self):
        self.renderer = RobotRenderer()
        self.talking = TalkingPattern()
        self.blink = BlinkController(period=3.0, duration=0.20, min_hold=0.02)
        self.params = {
            'eye_openness': 0.85, 'pupil_x': 0.0, 'pupil_y': 0.0,
            'mouth_open': 0.0, 'closed_eyes': False, 'is_blinking': False
        }
        self.current_emotion = 'neutral'  # 1 = neutral (now STILL-like)
        self.lock = Lock()
        self.last_time = time.time()
        cv2.namedWindow(self.WINDOW, cv2.WINDOW_NORMAL)
        cv2.setWindowProperty(self.WINDOW, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        try:
            cv2.setWindowProperty(self.WINDOW, cv2.WND_PROP_TOPMOST,1)
        except Exception:
            pass

    # External call to set emotion (1..5)
    def update_emotion(self, emotion_number:int):
        if 1 <= emotion_number <= 5:
            with self.lock:
                self.current_emotion = EMOTION_LIST[emotion_number - 1]
                if self.current_emotion != 'neutral':
                    self.talking.reset()

    def run(self):
        while True:
            if not self.run_step(): break
        cv2.destroyAllWindows()

    def run_step(self):
        dt = time.time() - self.last_time
        self.last_time = time.time()

        with self.lock:
            e_name = self.current_emotion
            e = EMOTIONS[e_name]

            # Blink only when NOT 'neutral' (since neutral behaves like STILL)
            blink_mult, is_blinking = self.blink.update(dt, allow=(e_name != 'neutral'))

            base_open = e['eye_openness']
            self.params['eye_openness'] = clamp(base_open * blink_mult, 0.0, 1.0)
            self.params['is_blinking'] = is_blinking

            self.params['pupil_x'] = e['pupil_x']
            self.params['pupil_y'] = e['pupil_y']

            if e_name == 'neutral':
                # still-like: hard close + no mouth movement
                self.params['closed_eyes'] = True
                self.params['mouth_open'] = 0.0
            else:
                self.params['closed_eyes'] = False
                self.params['mouth_open'] = self.talking.get_mouth_openness(dt)

        img = self.renderer.render(self.params, emotion_name=self.current_emotion)
        cv2.imshow("Robot Face", img)
        key = cv2.waitKey(1)
        if key == 27:
            cv2.destroyAllWindows(); return False
        return True

# ---- Run ----
if __name__ == "__main__":
    face = RobotFace()
    # Example: face.update_emotion(1)  # 1=neutral(STILL-like), 2=happy(old neutral), 3=sad, 4=surprised, 5=angry
    face.run()

