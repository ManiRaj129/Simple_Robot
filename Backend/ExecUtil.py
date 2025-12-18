import asyncio

async def set_face_display_screen(ready:asyncio.Event):
    proc = await asyncio.create_subprocess_exec(
        "/bin/bash", "display_face.sh",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    while True:
        line =await proc.stdout.readline()
        if not line:
            continue
        decoded = line.decode().rstrip()
        print(decoded)
        if "successfully" in decoded:
            ready.set()
            return

async def run_webrtc_script():
    #Ensuring the bash file is in same directory
    proc = await asyncio.create_subprocess_exec(
        "/bin/bash", "run-webrtc.sh",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    while True:
        line = await proc.stdout.readline()
        if not line:
            continue

        decoded = line.decode().rstrip()
        print("WebRTC:", decoded)
        #based on the ouput produced by the webrtc binary when ready
        # if "sensor" in decoded:
        #     break
        break
         
    return proc

async def stream_webrtc_process(proc):
    while True:
        line = await proc.stdout.readline()
        if not line:
            break
        print("WebRTC:", line.decode().rstrip())
