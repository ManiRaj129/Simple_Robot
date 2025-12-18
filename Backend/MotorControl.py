import RPi.GPIO as GPIO


# Motor pin setup
LEFT_FORWARD = 8
LEFT_BACKWARD = 7
RIGHT_FORWARD = 20
RIGHT_BACKWARD = 21
ENA = 25
ENB = 19

pwm_left = None
pwm_right = None

def initialSetUp(): 
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
def setup():
    global pwm_left, pwm_right
    GPIO.setup([LEFT_FORWARD, LEFT_BACKWARD, RIGHT_FORWARD, RIGHT_BACKWARD, ENA, ENB], GPIO.OUT)

    pwm_left = GPIO.PWM(ENA, 3000)
    pwm_right = GPIO.PWM(ENB, 3000)
    pwm_left.start(100)
    pwm_right.start(100)

def stop():
    GPIO.output([LEFT_FORWARD, LEFT_BACKWARD, RIGHT_FORWARD, RIGHT_BACKWARD], False)

def move_forward():
    GPIO.output(LEFT_FORWARD, True)
    GPIO.output(LEFT_BACKWARD, False)
    GPIO.output(RIGHT_FORWARD, True)
    GPIO.output(RIGHT_BACKWARD, False)

def move_backward():
    GPIO.output(LEFT_FORWARD, False)
    GPIO.output(LEFT_BACKWARD, True)
    GPIO.output(RIGHT_FORWARD, False)
    GPIO.output(RIGHT_BACKWARD, True)

def move_left():
    GPIO.output(LEFT_FORWARD, True)
    GPIO.output(LEFT_BACKWARD, False)
    GPIO.output(RIGHT_FORWARD, False)
    GPIO.output(RIGHT_BACKWARD, True)
    
def move_right():
    GPIO.output(LEFT_FORWARD, False)
    GPIO.output(LEFT_BACKWARD, True)
    GPIO.output(RIGHT_FORWARD, True)
    GPIO.output(RIGHT_BACKWARD, False)
    
    
def cleanup():
    stop()
    pwm_left.stop()
    pwm_right.stop()
    GPIO.cleanup()

