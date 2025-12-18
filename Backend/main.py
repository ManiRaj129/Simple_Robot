import asyncio
from IpcClient import WebRTC
from CommandHandler import setup, Manual, web_cmd_listner, voice_cmd_listner
import MotorControl as motor
import ObstaclePrediction as sensor
from Controller import ModeController, MediumController
from concurrent.futures import ThreadPoolExecutor
from ExecUtil import run_webrtc_script, stream_webrtc_process
from voice_listener import start_listener
from Face import RobotFace, EMOTION_MAP
import cv2
from Camera import camera

async def main():
    #GPIO setup
    motor.initialSetUp()
    motor.setup()
    await sensor.setup()

    loop = asyncio.get_running_loop()
    # executor for threaded code, change workers to 3 if necessary
    executor = ThreadPoolExecutor(max_workers=2)
    loop.set_default_executor(executor)

    #To ensure all modules use one instance (Singleton Pattern)
    ipc = WebRTC("/tmp/pi-webrtc-ipc.sock")
    mc = ModeController()
    medc= MediumController()

    # Robot Face Initialization
    face= RobotFace()
    face.update_emotion(EMOTION_MAP["sleeping"])
    face_task= asyncio.create_task(face.run_face_async())
    
    # voice listner
    listener_ready = asyncio.Event()
    listener_task = asyncio.create_task(start_listener(ready=listener_ready))
    await listener_ready.wait()

    #Pi WebRTC 
    proc = await run_webrtc_script()
    webrtc_task = asyncio.create_task(stream_webrtc_process(proc))

    # socket connect for messaging
    await ipc.connect()
    print("IPC connected!")

    #command handler setup
    setup(ipc,face,mc,medc)

    await mc.set_mode(ipc, "manual", Manual)
    print(f"Current Mode: Manual")
    await ipc.send({"type":"log", "command":"Currently In Manual Mode"})
    await asyncio.sleep(0.2)

    try:
        tasks = [
            asyncio.create_task(web_cmd_listner()),   
            asyncio.create_task(voice_cmd_listner())     
        ]
        await asyncio.gather(face_task,webrtc_task,listener_task, *tasks)


    except KeyboardInterrupt:
        print("Cancelling tasks...")
        for t in tasks:
            t.cancel()
        # waiting for tasks to cancel
        await asyncio.gather(*tasks, return_exceptions=True)
        print("All tasks cancelled.")
    finally:
        motor.cleanup()
        cv2.destroyAllWindows()
        camera.stop()


if __name__ == "__main__":
    asyncio.run(main())
