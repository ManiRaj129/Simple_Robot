import MotorControl as motor
import ObstaclePrediction as sensor
import asyncio
import queue
from robot_utils import get_objects_at
from typing import Dict
from IpcClient import WebRTC
from Follow_me import goToTarget
from Face import EMOTION_MAP, RobotFace
from robot_utils import speak
from voice_listener import set_muted
    
class RecurringPattern:

    def __init__(self):       
        self.q = queue.Queue(maxsize=4)   
    
    # Add action movement in binary
    def addMovementBinary(self, binary):       
        if self.q.qsize() == 4:
            self.q.get()
        self.q.put(binary)
 
	# Determines if there is a recurring pattern between movement actions
	# (1 2) & (3 4)
	# @return true if recurring pattern found, false otherwise
    def isRecurringPattern(self):
        if self.q.qsize() == 4:           
            mov1 = self.q.queue[0]
            mov2 = self.q.queue[1]
            mov3 = self.q.queue[2]
            mov4 = self.q.queue[3]

            if ((mov1 + mov2 == 1) and 
				(mov3 + mov4 == 1) and 
				mov1 == mov3 and mov2 == mov4):

                while not self.q.empty():
                    self.q.get()           
                return True
        return False


# Smartly explore one step ahead when the target object is not in visible range
async def move(pattern:RecurringPattern):

    distances = await sensor.get_all_distances()
    front = distances["front"]
    left = distances["left"]
    right = distances["right"]
    back = distances["back"]

    threshold = 30  
    sideThreshold = 30  
    rearThreshold = 15

    if pattern.isRecurringPattern():
        print("Robot might be stuck. Making LARGE clockwise turn >>>>")
        motor.move_right()
        await asyncio.sleep(1.0)
        motor.stop()
        return

    # FRONT OBSTACLE
    if front != -1 and front < threshold and left > sideThreshold and right > sideThreshold:
        
        motor.stop()
        await asyncio.sleep(0.3)
        motor.move_backward()
        await asyncio.sleep(0.3)
        motor.move_right()
        await asyncio.sleep(0.5)
        motor.stop()
        return

    # BOTH SIDES BLOCKED
    if left < sideThreshold and right < sideThreshold:
        motor.stop()
        await asyncio.sleep(0.3)

        if back > rearThreshold:
            motor.move_backward()
            await asyncio.sleep(0.2)
            motor.stop()

        motor.move_right()
        pattern.addMovementBinary(1)
        await asyncio.sleep(0.6)
        motor.stop()
        return

    # LEFT BLOCKED
    if left != -1 and left < sideThreshold:
        motor.stop()
        await asyncio.sleep(0.3)

        if back > rearThreshold:
            motor.move_backward()
            await asyncio.sleep(0.2)
            motor.stop()

        motor.move_right()
        pattern.addMovementBinary(1)
        await asyncio.sleep(0.6)
        motor.stop()
        return

    # RIGHT BLOCKED
    if right != -1 and right < sideThreshold:
        motor.stop()
        await asyncio.sleep(0.3)

        if back > rearThreshold:
            motor.move_backward()
            await asyncio.sleep(0.2)
            motor.stop()

        motor.move_left()
        pattern.addMovementBinary(0)
        await asyncio.sleep(0.6)
        motor.stop()
        return

    # PATH CLEAR
    motor.move_forward()
    pattern.addMovementBinary(-1)
    await asyncio.sleep(0.3)
    motor.stop()


async def isObjDetected(objs:Dict, target:str):
    for obj in objs:
        if obj.get("name").strip().casefold()== target.strip().casefold():
            return True
    return False

async def toObjList(objs:Dict, target:str):
    found= False
    objList =[]
    for obj in objs:
        objName=obj.get("name")
        objList.append(objName)
        if objName.strip().casefold()== target.strip().casefold():
            found= True
    return (found, objList)


async def findDirection(obj:str, ipc:WebRTC):
    directions = ["front", "right", "back", "left"]

    for direction in directions:
        print(f"Scanning {direction}...")
        objects= None
        #Max Frames
        i=0
        while objects is None and i<5:
            objects = await get_objects_at()
            found, objList = await toObjList(objects,obj) 
            print("objects detected:", objList)
            i +=1
        await ipc.send({"type":"objects", "command": objList})

        if found:
             print(f"Object found in {direction}")
             return True
        await asyncio.sleep(0.2)
        
        motor.move_right()
        await asyncio.sleep(0.3)
        motor.stop()
    return False
  
async def goToObject(target:str,ipc:WebRTC):
    set_muted(True)
    SAFETY_SIDE = 18     
    TARGET_DISTANCE = 50 
    while True:
        distances = await sensor.get_all_distances()
        front = distances["front"]
        left = distances["left"]      
        right = distances["right"] 

        print("Distances:", distances)

        if front != -1 and front <= TARGET_DISTANCE:
            print("Reached object")
            motor.stop()
            set_muted(False)
            return

        # left wall too close
        elif left != -1 and left < SAFETY_SIDE:
            print("Left wall too close, slightly steer right")
            motor.move_right()          
            await asyncio.sleep(0.15)
            motor.stop()

        #  right wall too close 
        elif right != -1 and right < SAFETY_SIDE:
            print("Right wall too close, slightly steer left")
            motor.move_left()           
            await asyncio.sleep(0.15)
            motor.stop()            

        # move forward 
        elif front != -1 and front > TARGET_DISTANCE:
            print("Approaching object…")
            motor.move_forward()
            await asyncio.sleep(0.25)
            motor.stop()
        
        objects = await get_objects_at()
        if not await isObjDetected(objects,target):
            findDirection(target,ipc)
    
   
            
 
async def findObject(targetObj: str, ipc:WebRTC, face: RobotFace):
    # motor.initialSetUp()
    # motor.setup()
    # await sensor.setup()

    pattern = RecurringPattern()

    while True:        
        await ipc.send({"type":"log", "command" : "Finding "+ targetObj})
        # Scan all 4 directions       
        if await findDirection(targetObj, ipc):
             await goToObject(targetObj,ipc)           
             await ipc.send({"type":"log","command": targetObj +" found"})
             print("found: ", targetObj)
             await speak(f"I found {targetObj}", face)
             return True
        # object not seen/visible 
        else:
            await move(pattern)
        await asyncio.sleep(0.2)
    


async def autonomousExplore(pattern):
    distances =await sensor.get_all_distances()
    print(distances)

    front = distances["front"]
    left = distances["left"]
    right = distances["right"]
    back = distances["back"]

    threshold = 30  # cm
    leftRightThreshold = 30  # cm
    rearThreshold = 15

    if (pattern.isRecurringPattern()):
        print("Robot might be stuck. Making large clockwise turn >>>>>\n")
        motor.move_right()
        await asyncio.sleep(1.0)
        motor.stop()
    else:
        print("Not stuck")

    await asyncio.sleep(0.5)
    # Resolve front obstacle detection
    if front != -1 and front < threshold and left > leftRightThreshold and right > leftRightThreshold:
        print("Obstacle detected ahead! Backing up, turning clockwise >>>>>\n")
        motor.stop()
        await asyncio.sleep(0.3)

        motor.move_backward()
        await asyncio.sleep(0.3)

        motor.move_right()
        await asyncio.sleep(0.5)
        motor.stop()

    # Resolve both left and right obstacle detection
    elif left != -1 and left < leftRightThreshold and right != -1 and right < leftRightThreshold:
        print("Left and right obstacle detected. Turning clockwise >>>>>\n")
        motor.stop()
        await asyncio.sleep(0.3)

        if back != -1 and back > rearThreshold:
            motor.move_backward()
            await asyncio.sleep(0.2)
            motor.stop()
            await asyncio.sleep(0.3)

        motor.move_right()
        pattern.addMovementBinary(1)
        await asyncio.sleep(0.6)
        motor.stop()

    # Resolve left obstacle detection
    elif left != -1 and left < leftRightThreshold:
        print("Left obstacle detected. Turning clockwise >>>>>\n")
        motor.stop()
        await asyncio.sleep(0.3)

        if back != -1 and back > rearThreshold:
            motor.move_backward()
            await asyncio.sleep(0.2)
            motor.stop()
            await asyncio.sleep(0.3)

        motor.move_right()
        pattern.addMovementBinary(1)
        await asyncio.sleep(0.6)
        motor.stop()

    # Resolve right obstacle detection
    elif right != -1 and right < leftRightThreshold:
        print("Right obstacle detected. Turning counter-clockwise <<<<<\n")
        motor.stop()
        await asyncio.sleep(0.3)

        if back != -1 and back > rearThreshold:
            motor.move_backward()
            await asyncio.sleep(0.2)
            motor.stop()
            await asyncio.sleep(0.3)

        motor.move_left()
        pattern.addMovementBinary(0)
        await asyncio.sleep(0.6)
        motor.stop()

    else:
        print("Path clear, moving forward.\n")
        motor.move_forward()
        pattern.addMovementBinary(-1)
        await asyncio.sleep(0.3)
        motor.stop()


#Test
async def autonomousRandomExplore():
    print("Autonomous Exploration started")
    motor.initialSetUp()
    motor.setup()
    await sensor.setup()
    pattern = RecurringPattern()

    try:
        while(True):

            distances =await sensor.get_all_distances()
            print(distances)

            front = distances["front"]
            left = distances["left"]
            right = distances["right"]
            back = distances["back"]

            threshold = 30  # cm
            leftRightThreshold = 30  # cm
            rearThreshold = 15

            if (pattern.isRecurringPattern()):
                print("Robot might be stuck. Making large clockwise turn >>>>>\n")
                motor.move_right()
                await asyncio.sleep(1.0)
                motor.stop()
            else:
                print("Not stuck")

            await asyncio.sleep(0.5)
            # Resolve front obstacle detection
            if front != -1 and front < threshold and left > leftRightThreshold and right > leftRightThreshold:
                print("Obstacle detected ahead! Backing up, turning clockwise >>>>>\n")
                motor.stop()
                await asyncio.sleep(0.3)

                motor.move_backward()
                await asyncio.sleep(0.3)

                motor.move_right()
                await asyncio.sleep(0.5)
                motor.stop()

            # Resolve both left and right obstacle detection
            elif left != -1 and left < leftRightThreshold and right != -1 and right < leftRightThreshold:
                print("Left and right obstacle detected. Turning clockwise >>>>>\n")
                motor.stop()
                await asyncio.sleep(0.3)

                if back != -1 and back > rearThreshold:
                    motor.move_backward()
                    await asyncio.sleep(0.2)
                    motor.stop()
                    await asyncio.sleep(0.3)

                motor.move_right()
                pattern.addMovementBinary(1)
                await asyncio.sleep(0.6)
                motor.stop()

            # Resolve left obstacle detection
            elif left != -1 and left < leftRightThreshold:
                print("Left obstacle detected. Turning clockwise >>>>>\n")
                motor.stop()
                await asyncio.sleep(0.3)

                if back != -1 and back > rearThreshold:
                    motor.move_backward()
                    await asyncio.sleep(0.2)
                    motor.stop()
                    await asyncio.sleep(0.3)

                motor.move_right()
                pattern.addMovementBinary(1)
                await asyncio.sleep(0.6)
                motor.stop()

            # Resolve right obstacle detection
            elif right != -1 and right < leftRightThreshold:
                print("Right obstacle detected. Turning counter-clockwise <<<<<\n")
                motor.stop()
                await asyncio.sleep(0.3)

                if back != -1 and back > rearThreshold:
                    motor.move_backward()
                    await asyncio.sleep(0.2)
                    motor.stop()
                    await asyncio.sleep(0.3)

                motor.move_left()
                pattern.addMovementBinary(0)
                await asyncio.sleep(0.6)
                motor.stop()

            else:
                print("Path clear, moving forward.\n")
                motor.move_forward()
                pattern.addMovementBinary(-1)
                await asyncio.sleep(0.3)
                motor.stop()
    except KeyboardInterrupt:
        print("Forced to stop Exploration")
    finally:
        motor.cleanup()

if __name__ =="__main__":
    asyncio.run(autonomousRandomExplore())
   
    #  asyncio.run(findObject("bottle"))