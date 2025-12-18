import time
import MotorControl as motor
import ObstaclePrediction as sensor
from enum import Enum, auto
import asyncio 

class Movement:

    class Directions(Enum):
        FORWARD = auto()
        REVERSE = auto()
        LEFT = auto()
        RIGHT = auto()

    distanceThreshold = 30 # cm
    estimateMovementDistance = 10 # Robot estimated to move 10cm at a time

    async def getSensorDistances():
        return await sensor.get_all_distances()

    def checkThreshold(distance):
        if (distance < Movement.distanceThreshold):
            return False
        else:
            return True
        
    def checkAllThreshold(distances):
        print(f"Getting distances: {distances}")
        if (distances["front"] < Movement.distanceThreshold and distances["back"] < Movement.distanceThreshold and distances["left"] < Movement.distanceThreshold and distances["right"] < Movement.distanceThreshold):
            return False
        else:
            return True

    def getMoveDistanceTime(currentNode, distances):
        currentDistance = 0

        print(f"Getting parent movement of: {currentNode.parentMovement}")

        match currentNode.parentMovement:
            case Movement.Directions.FORWARD:
                currentDistance = distances["front"]

            case Movement.Directions.REVERSE:
                currentDistance = distances["back"]

            case Movement.Directions.LEFT:
                currentDistance = distances["left"]
                return 0.5
            
            case Movement.Directions.RIGHT:
                currentDistance = distances["right"]
                return 0.5
        
        allowedDistance = currentDistance - Movement.distanceThreshold

        if (allowedDistance > 16):
            currentNode.movementDistanceTime = 0.25
            return 0.25
        elif (allowedDistance < 0):
            currentNode.movementDistanceTime = 0
            return 0
        else:
            print(f"Robot movement exceeds threshold. Moving only {allowedDistance} cm instead of {Movement.estimateMovementDistance}")
            currentNode.movementDistanceTime = (allowedDistance * 0.022) + 0.033
            return (allowedDistance * 0.022) + 0.033 # 0.022s = 1cm of movement, added extra 1.5cm to exceed to threshold
        
    async def forward(timeOfSleep):

        print(f"Going forward at time: {timeOfSleep}")
        motor.move_forward()
        await asyncio.sleep(timeOfSleep)
        motor.stop()
        await asyncio.sleep(0.3)

    async def reverse(timeOfSleep):
        motor.move_backward()
        await asyncio.sleep(timeOfSleep)
        motor.stop()
        await asyncio.sleep(0.3)

    async def left(timeOfSleep):
        motor.move_left()
        await asyncio.sleep(timeOfSleep)
        motor.stop()
        await asyncio.sleep(0.3)

    async def right(timeOfSleep):
        motor.move_right()
        await asyncio.sleep(timeOfSleep)
        motor.stop()
        await asyncio.sleep(0.3)

    async def turn180():
        motor.move_right()
        await asyncio.sleep(1.5)
        motor.stop()
        await asyncio.sleep(0.3)

    async def returnToParent(currentNode):
        match currentNode.parentMovement:
            case Movement.Directions.FORWARD:
                print("Moving backward to parent at time: {parentMovementTime}")
                await Movement.reverse(currentNode.movementDistanceTime)

            case Movement.Directions.REVERSE:
                print("Turning around and moving forward to parent at time: {parentMovementTime}")
                await Movement.turn180()
                await Movement.forward(currentNode.movementDistanceTime)

            case Movement.Directions.LEFT:
                print("Moving right to parent at time: {parentMovementTime}")
                await Movement.right(currentNode.movementDistanceTime)

            case Movement.Directions.RIGHT:
                print("Moving left to parent at time: {parentMovementTime}")
                await Movement.left(currentNode.movementDistanceTime)

class Node:

    def __init__(self):
        self.parent = None
        self.parentMovement = None
        self.explored = False
        self.depth = 0

        self.frontChild = None
        self.leftChild = None
        self.rightChild = None
        self.backChild = None

        self.movementDistanceTime = 0
        self.objectDetected = None
    
    def createChildNodes(self, distances):
        if (self.frontChild == None and Movement.checkThreshold(distances["front"]) and Movement.checkThreshold(distances["left"]) and Movement.checkThreshold(distances["right"])):
            frontDistance = distances["front"]
            print(f"Creating front child node. Distance left: {frontDistance}")

            frontNode = Node()
            frontNode.parent = self
            frontNode.parentMovement = Movement.Directions.FORWARD

            self.frontChild = frontNode

        if (self.backChild == None and Movement.checkThreshold(distances["back"])):
            backDistance = distances["back"]
            print(f"Creating back child node. Distance left: {backDistance}")
            backNode = Node()
            backNode.parent = self
            backNode.parentMovement = Movement.Directions.REVERSE

            self.backChild = backNode

        if (self.leftChild == None and Movement.checkThreshold(distances["left"])):
            leftDistance = distances["left"]
            print(f"Creating left child node. Distance left: {leftDistance}")
            leftNode = Node()
            leftNode.parent = self
            leftNode.parentMovement = Movement.Directions.LEFT

            self.leftChild = leftNode

        if (self.rightChild == None and Movement.checkThreshold(distances["right"])):
            rightDistance = distances["right"]
            print(f"Creating right child node. Distance left: {rightDistance}")
            rightNode = Node()
            rightNode.parent = self
            rightNode.parentMovement = Movement.Directions.RIGHT

            self.rightChild = rightNode

        if (self.parentMovement):
            match self.parentMovement:
                case Movement.Directions.FORWARD:
                    self.backChild = None

                case Movement.Directions.REVERSE:
                    self.frontChild = None

                case Movement.Directions.LEFT:
                    self.rightChild = None

                case Movement.Directions.RIGHT:
                    self.leftChild = None

    async def DFS(self, maxDepth):

        nodeStack = []
        nodeStack.append(self)

        while (len(nodeStack) != 0):
            
            currentNode = nodeStack.pop()
            currentNode.explored = True
            print(f"Exploring depth of: {currentNode.depth}")
            if currentNode.depth > maxDepth:
                continue

            print(f"Does current node have parent: {currentNode.parent}")
            if currentNode.parent:
                match currentNode.parentMovement:
                    case Movement.Directions.FORWARD:
                        print("Exploring front child")
                        await Movement.forward(Movement.getMoveDistanceTime(currentNode, await Movement.getSensorDistances()))

                    case Movement.Directions.REVERSE:
                        print("Exploring back child")
                        await Movement.reverse(Movement.getMoveDistanceTime(currentNode, await Movement.getSensorDistances()))

                    case Movement.Directions.LEFT:
                        print("Exploring left child")
                        await Movement.left(Movement.getMoveDistanceTime(currentNode, await Movement.getSensorDistances()))

                    case Movement.Directions.RIGHT:
                        print("Exploring right child")
                        await Movement.right(Movement.getMoveDistanceTime(currentNode, await Movement.getSensorDistances()))

            currentNode.createChildNodes(await Movement.getSensorDistances())

            childrenCreated = 0

            if currentNode.backChild:
                nodeStack.append(currentNode.backChild)
                currentNode.backChild.depth = currentNode.depth + 1
                childrenCreated += 1
            if currentNode.rightChild:
                nodeStack.append(currentNode.rightChild)
                currentNode.rightChild.depth = currentNode.depth + 1
                childrenCreated += 1
            if currentNode.leftChild:
                nodeStack.append(currentNode.leftChild)
                currentNode.leftChild.depth = currentNode.depth + 1
                childrenCreated += 1
            if currentNode.frontChild:
                nodeStack.append(currentNode.frontChild)
                currentNode.frontChild.depth = currentNode.depth + 1
                childrenCreated += 1
            
            if childrenCreated == 0:
                print("This node has been explored")
                Movement.returnToParent(currentNode)


async def main():

    motor.initialSetUp()
    motor.setup()
    await sensor.setup()

    try:
        root = Node()
        objectDetected = False
        maxDepth = 5

        while (not objectDetected):
            if (Movement.checkAllThreshold(await Movement.getSensorDistances())):

                print("Exploring from root node")
                await root.DFS(maxDepth)

            else:
                print("Robot block from all sides at root node.")

            maxDepth += 1

    except KeyboardInterrupt:
        print("\nExploration stopped by user\n")
    finally:
        motor.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
