import asyncio
import MotorControl as motor
import ObstaclePrediction as sensor
from obj_detection_k import object_track
from IpcClient import WebRTC
from Face import EMOTION_MAP, RobotFace
from robot_utils import speak
from voice_listener import set_muted

class RecurringPattern:
    """Detects if robot is stuck in a recurring movement pattern"""
    def __init__(self):       
        self.q = asyncio.Queue(maxsize=4)
    
    async def add_movement(self, binary):       
        if self.q.full():
            await self.q.get()
        await self.q.put(binary)
    
    def is_recurring(self):
        if self.q.qsize() == 4:
            items = list(self.q._queue)
            mov1, mov2, mov3, mov4 = items
            if ((mov1 + mov2 == 1) and (mov3 + mov4 == 1) and 
                mov1 == mov3 and mov2 == mov4):
                while not self.q.empty():
                    try:
                        self.q.get_nowait()
                    except:
                        break
                return True
        return False


async def goToTarget( target:str, ipc:WebRTC, isFollow:bool, face, safeD,maxF):
    set_muted(True)
    pattern = RecurringPattern()
    lost_count = 0
    # Configuration
    SAFE_DISTANCE = safeD  # cm - minimum safe distance from target
    DISTANCE_TOLERANCE = 10  # cm - tolerance range for safe distance
    MAX_LOST_FRAMES = maxF

    try:      
        while True:
            # Get target direction from camera (cpu heavy)
            # loop = asyncio.get_running_loop()
            direction, _ =  object_track(target)
            
            # Get distances from ultrasonic sensors
            distances = await sensor.get_all_distances()
            front_distance = distances["front"]
            left_distance = distances["left"]
            right_distance = distances["right"]
            back_distance = distances["back"]
            
            print(f"Distances - Front: {front_distance}cm, Left: {left_distance}cm, Right: {right_distance}cm")
            
            # target not detected
            if direction is None:
                lost_count += 1
                print(f"target not visible ({lost_count}/{MAX_LOST_FRAMES})")
                await ipc.send({"type":"log", "command":f"{target} not visible ({lost_count}/{MAX_LOST_FRAMES})"})
                
                if lost_count >= MAX_LOST_FRAMES:
                    print("target lost. Stopping and searching...")
                    await ipc.send({"type":"log", "command": f"{target} lost. Stopping and searching..."})
                
                    motor.stop()
                    await asyncio.sleep(0.5)
                    
                    # Slow rotation to search for target
                    motor.move_right()
                    await asyncio.sleep(0.4)
                    motor.stop()
                    lost_count = 0
                else:
                    motor.stop()
                
                await asyncio.sleep(0.2)
                continue
            
            # target detected - reset lost counter
            lost_count = 0
            
            # Check if stuck in pattern
            if pattern.is_recurring():
                print("Robot stuck in pattern - breaking free with large turn")
                await ipc.send({"type":"log", "command":"Robot stuck in pattern - breaking free with large turn"})
                motor.move_right()
                await asyncio.sleep(1.2)
                motor.stop()
                await asyncio.sleep(0.3)
                continue
            
            # Emergency stop if too close
            if front_distance != -1 and front_distance < 30:
                print("EMERGENCY: Too close! Backing up...")
                await ipc.send({"type":"log", "command":"EMERGENCY: Too close! Backing up..."})
                motor.move_backward()
                await asyncio.sleep(0.5)
                motor.stop()
                await pattern.add_movement(2)
                await asyncio.sleep(0.3)
                continue
            
            # Main decision logic based on direction and distance
            print(f"{target} detected: {direction} | Front distance: {front_distance}cm")
            await ipc.send({"type":"log", "command":f"{target} detected: {direction} | Front distance: {front_distance}cm"})
            
            # target is to the LEFT
            if direction == "left":
                # Check if turn is significant enough
                print("target on LEFT - turning left")
                await ipc.send({"type":"log", "command":f"{target} on LEFT - turning left"})
                motor.move_left()
                await asyncio.sleep(0.2)
                motor.stop()
                await pattern.add_movement(0)
                await asyncio.sleep(0.05)
            
            # target is to the RIGHT
            elif direction == "right":
                print("target on RIGHT - turning right")
                await ipc.send({"type":"log", "command":f"{target} on RIGHT - turning right"})
                motor.move_right()
                await asyncio.sleep(0.2)
                motor.stop()
                await pattern.add_movement(1)
                await asyncio.sleep(0.05)
            
            # target is CENTERED
            else:
                print("target CENTERED - adjusting distance")
                await ipc.send({"type":"log", "command":"{target} CENTERED - adjusting distance"})
                
                # target too far - move forward
                if front_distance == -1 or front_distance > (SAFE_DISTANCE + DISTANCE_TOLERANCE):
                    print(f"Moving FORWARD - distance: {front_distance}cm (target: {SAFE_DISTANCE}cm)")
                    await ipc.send({"type":"log", "command":f"Moving FORWARD - distance: {front_distance}cm ({target}: {SAFE_DISTANCE}cm)"})
                    motor.move_forward()
                    await asyncio.sleep(0.5)
                    motor.stop()
                    await pattern.add_movement(-1)
                
                # target too close - move backward
                elif front_distance < (SAFE_DISTANCE - DISTANCE_TOLERANCE):
                    print(f"Moving BACKWARD - distance: {front_distance}cm (target: {SAFE_DISTANCE}cm)")
                    await ipc.send({"type":"log", "command":f"Moving BACKWARD - distance: {front_distance}cm ({target}: {SAFE_DISTANCE}cm)"})
                    motor.move_backward()
                    await asyncio.sleep(0.5)
                    motor.stop()
                    await pattern.add_movement(2)
                
                # target at safe distance - stay put
                else:
                    await asyncio.sleep(0.3)
                    if not isFollow:
                        return 
                    print(f"MAINTAINING POSITION - distance: {front_distance}cm (safe zone)")
                    await speak(f"I am following you", face)
                    motor.stop()
                    await pattern.add_movement(-1)


                
                await asyncio.sleep(0.05)
            
            # Small delay between iterations
            await asyncio.sleep(0.05)
    
    except KeyboardInterrupt:
        print(f"\n\nStopping {target} follow()")



if __name__ == "__main__":
    asyncio.run(goToTarget("person"))