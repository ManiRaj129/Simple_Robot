import RPi.GPIO as GPIO
import asyncio
import time

sensors = {
    "front": {"TRIG": 14, "ECHO": 15},
    "back": {"TRIG": 10, "ECHO": 9},
    "left": {"TRIG": 5, "ECHO": 6},
    "right": {"TRIG": 16, "ECHO": 26},
}

async def setup():
    for s in sensors.values():
        GPIO.setup(s["TRIG"], GPIO.OUT)
        GPIO.setup(s["ECHO"], GPIO.IN)
        GPIO.output(s["TRIG"], False)
    await asyncio.sleep(2) 

async def measure_distance(TRIG, ECHO):
    GPIO.output(TRIG, True)
    #Trigger time need to precise where asyncio time is not
    time.sleep(0.00001)
    GPIO.output(TRIG, False)

    pulse_start = time.time()
    timeout_start = time.time()
    while GPIO.input(ECHO) == 0:
        pulse_start = time.time()
        if time.time() - timeout_start > 0.02:
            return -1

    pulse_end = time.time()
    timeout_start = time.time()
    while GPIO.input(ECHO) == 1:
        pulse_end = time.time()
        if time.time() - timeout_start > 0.02:
            return -1

    pulse_duration = pulse_end - pulse_start
    distance = pulse_duration * 17150  # cm
    return round(distance, 2)


async def get_all_distances():
    distances = {}
    for name, pins in sensors.items():
        dist = await measure_distance(pins["TRIG"], pins["ECHO"])
        i=0
        while(i<3 and dist == -1):
            dist =await measure_distance(pins["TRIG"], pins["ECHO"])
            i +=1
        distances[name] = dist 
        await asyncio.sleep(0.05)
    return distances

#Test
async def main():
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        print("Setting up sensors...")
        await setup()
        print("Setup complete.")

        while True:
            distances = await get_all_distances()
            print("Distances:", distances)
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        print("Stopped by user.")

    finally:
        GPIO.cleanup()
        print("GPIO cleaned up.")

if __name__ == "__main__":
    asyncio.run(main())