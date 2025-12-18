import asyncio
from enum import Enum
from robot_utils import speak
from IpcClient import WebRTC
from voice_listener import set_muted

class Medium(Enum):
    WEB = "web"
    VOICE = "voice"


#find, followMe, or Manual
class ModeController:
    def __init__(self):
        self.current_mode=None
        self.current_task =None
        self.mode_lock= asyncio.Lock()

    async def set_mode(self,ipc, mode:str, task, *args):     
        #To ensure serilized behaviour of mode changes
        async with self.mode_lock:
            set_muted(False)
            if self.current_task and not self.current_task.done():
                #terminates the task
                #it only request the cancellation 
                #the task should have at least on await call init to receive request /the cancellederror object
                self.current_task.cancel()
                try:
                    await self.current_task
                except asyncio.CancelledError:
                    print(f"{self.current_mode} mode cancelled")

                print(f"Switched to {mode}")
                
            #switch/set mode
            self.current_mode = mode
            
            self.current_task = asyncio.create_task(task(*args))


# To control how commands are given to robot (web or voice)
class MediumController:
    def __init__(self):
        self.med:Medium = None             
        self.med_lock = asyncio.Lock()
        self.last_unsuccessful_acquire:Medium =None     
    
    #requester: "web" or "voice"
    async def acquire(self, req: Medium) -> bool:
        async with self.med_lock:
            if self.med is not None:
                self.last_unsuccessful_acquire = req
                return False
            #until failed voice acquire get chance web cannot get control       
            if (self.last_unsuccessful_acquire is None or req == Medium.VOICE):
                self.med = req
                self.last_unsuccessful_acquire = None
                return True
          
            self.last_unsuccessful_acquire = req
            return False

    async def release(self, requester:Medium, face):
        if self.med == requester:
            self.med = None
            if self.last_unsuccessful_acquire is not None:
                await speak("Now, I am available to take your commands ", face)
                

