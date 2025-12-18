import asyncio,json
import time
from typing import Dict
import MotorControl as motor
from Autonomous import  findObject
from Follow_me import goToTarget
from Controller import ModeController, MediumController, Medium
from robot_utils import speak, ask_llm 
from Face import EMOTION_MAP, RobotFace
from IpcClient import WebRTC
from voice_listener import get_voice_queue, set_last_bot_response, set_muted

   
FOLLOWUP_WINDOW = 0  # Match voice_listener

motor_queue = None
ipc = None
face = None
mc = None
medc=None
def setup(ipc_client:WebRTC, faceInstance: RobotFace, Mode:ModeController, Medium:MediumController):
    global ipc, motor_queue, face, mc, medc
    face = faceInstance
    mc=Mode
    medc=Medium
    motor_queue = asyncio.Queue()
    ipc = ipc_client   


async def drain_queue(q: asyncio.Queue):
    while not q.empty():
        try:
            q.get_nowait()
            q.task_done()
        except asyncio.QueueEmpty:
            break

async def Manual():
    while True:
        cmd = await motor_queue.get()
       
        direction = cmd.get("command")
        print(f"Executing motor command: {direction}")

        if direction == "front":
            motor.move_forward()
            await asyncio.sleep(0.25)
        elif direction == "back":
            motor.move_backward()
            await asyncio.sleep(0.25)
        elif direction == "left":
            motor.move_left()
            await asyncio.sleep(0.7)
        elif direction == "right":
            motor.move_right()
            await asyncio.sleep(0.7)
        else:
            motor.stop()
        
        await ipc.send({"type":"log", "command": "Robot moved "+direction})
        motor.stop()

async def web_cmd_listner():

    while True:
        face.update_emotion(EMOTION_MAP.get("neutral", 1))
        msg:json = await ipc.receive()
        if not msg:
            print("IPC disconnected")

        hasControl = medc.acquire(Medium.WEB)
        if not hasControl:
            await ipc.send({"type":"log", "command":"Robot is Busy performing Voice Commands"})

        cmd_type = msg.get("type")
        #Expected that motor commands always send in manual mode
        if cmd_type == "motor":
            await motor_queue.put(msg)
        elif cmd_type == "mode":
            cmd = msg.get("command")
            await ipc.send({"type": "mode", "command":cmd})
            if cmd == "autonomous":
               pass              
            elif cmd == "manual":
                await mc.set_mode(ipc,cmd,Manual)
            else:
                print("Unknown Mode requested")
                await ipc.send({"type":"log", "command":"Unknown Mode requested"})        
        elif cmd_type == "find":
            await handler(msg.get("command"))
        else:
            print("Unknown command:", msg)



async def voice_cmd_listner():
    voice_queue = get_voice_queue()   
    while True:
        # voice_listener outputs: (text, t_utterance_end, is_followup)
        item = await voice_queue.get()
        
        if isinstance(item, tuple):
            user_text = item[0]
            is_followup = item[2] if len(item) > 2 else False
        else:
            user_text = item
            is_followup = False
        
        if not user_text:
            continue

        hasControl = medc.acquire(Medium.VOICE)
        if not hasControl:
            await speak("I am busy performing web commands", face)
            await ipc.send({"type":"log", "command":"ignored voice command since robot performing web commands"})

            
        print(f"[VoiceHandler] Processing: {user_text} (followup={is_followup})")
        await ipc.send({"type":"log", "command":f"[VoiceHandler] Processing: {user_text} (followup={is_followup})"})
        await handler(user_text)
        


async def handler(user_text:str):
        print("handler")
        
     # Update face to thinking
        face.update_emotion(EMOTION_MAP.get("listening", 6))
        await asyncio.sleep(2)
        
        # Get LLM response
        try:
            act_cmd = await ask_llm(user_text)
            print(f"LLM response: {act_cmd}")
            await ipc.send({"type":"log", "commad":f"LLM response: {act_cmd}"})
            
            # Update face emotion
            emotion = act_cmd.get("emotion")
            face.update_emotion(EMOTION_MAP.get(emotion, 0))

             # Speak response
            text_response = act_cmd.get("response","")
            print("llm : ", text_response)
            if text_response:
                await speak(text_response, face)
                set_last_bot_response(text_response, time.time())
            
            face.update_emotion(EMOTION_MAP.get("neutral", 0))

            targetObj= act_cmd.get("find") 
            direct_motor_command =act_cmd.get("command")

            if act_cmd.get("follow"):
                await ipc.send({"type":"log", "command":"Following Person"})
                await mc.set_mode(ipc,"folloMe", goToTarget,"Person",ipc,True,face,40, 5)
                
            elif targetObj:
                print(f"Find: {targetObj}")
                await mc.set_mode(ipc,"find", findObject,targetObj,ipc,face)
                
            elif  direct_motor_command:
                await mc.set_mode(ipc,"manual",Manual)
                await motor_queue.put({"type": "motor", "command":direct_motor_command})

                                    
            # Schedule sleeping face after followup window
            #asyncio.create_task(face.schedule_sleeping(FOLLOWUP_WINDOW))
            
        except Exception as e:
            print(f"Error while Handling Command: {e}")
            face.update_emotion(EMOTION_MAP.get("sleeping", 7))



