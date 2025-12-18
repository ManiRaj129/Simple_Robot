import asyncio, json 

class WebRTC:
    def __init__(self,socket_path:str):
        self.path=socket_path
        self.reader=None
        self.writer=None
        #To prevent Corruption of text Messages 
        self.send_lock = asyncio.Lock()

    async def connect(self):
        while True:
            try:
                self.reader, self.writer= await asyncio.open_unix_connection(self.path)
                print("IPC connection Established")
                return
            except (ConnectionRefusedError, FileNotFoundError):
                print("Failed, trying again!")
                await asyncio.sleep(1)
    
    async def send(self, obj:json):
        async with self.send_lock:
            if not self.writer:
                print("ipc writer not intialised")
                return
            msg=json.dumps(obj) +"\n"
            self.writer.write(msg.encode())
            await self.writer.drain()
            print(f"sent:{msg.strip()}")
    
    async def receive(self):
        data= await self.reader.read(1024)
        if not data:
            print("ipc disconnected")
            return data   
        try:
            msg=json.loads(data.decode())
            print("received:",msg) 
            return msg                 
        except json.JSONDecodeError:
            print("Invalid JSON:",data)
            await self.send({"type":"log", "command":"Incorrect Request Format; expected JSON"})

       

