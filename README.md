# sd01_simple_robot

## Environment SetUp (the following setup is for Linux OS)

- **Python**:
  Command:
  `bash
     sudo apt install python3 python3-pip -y
     `
- **Python packages**

  1. RPI.GPIO (by default installed on raspberryPI)

  2. ultralytics (YOLO object detection),OpenCV (Image processing for camera frames), Numpy (Preprocessing camera frames, Scaling pixel values)

  - Command:

  ```bash
  pip3 install ultralytics, python3-opencv, python3-numpy
  ```

- **Virtual Camera**
  1.  v4l2loopback for creating virtual camera
  ```
  sudo apt install v4l2loopback-dkms v4l2loopback-utils
  ```
  **_usgae_**
  To find Available video device number:
  ```
  v4l2-ctl --list-devices
  ```
  Used 8 in following example:
  ```
  sudo modprobe v4l2loopback devices=1 video_nr=8 card_label=ProcessedCam max_buffers=4 exclusive_caps=1
  ```
- **GIT**

  ```
  sudo apt install git
  ```

- **MOSQUITTO local Server (optional could use cloud services like HiveMQ)**

  ```
  sudp apt install mosquitto
  ```

  After Install:

  ```
  sudo systemctl enable mosquitto
  sudo systemctl start mosquitto

  ```

- **WEBRTC Framework**
  1.PI-WEBRTC Binary

  ```
  git clone https://github.com/TzuHuanTai/RaspberryPi-WebRTC.git
  ```

  **_binary usage (bash file[run-webrtc.sh] provided for this project usage)_**

  ```
  ./pi-webrtc -h
  ```

- **NGINX for Reverse Proxy, hosting backend and frontend**

  ```
  sudo apt install nginx -y
  ```

  After Install:

  ```
  sudo systemctl enable nginx
  sudo systemctl start nginx
  ```

- **Security Certificates**

  1. openssl

  ```
  sudo apt install openssl -y
  ```

  **_usage_**

  ```
  sudo openssl req -x509 -nodes -days 365 \
  -newkey rsa:2048 \
  -keyout /etc/ssl/private/[Name].key \
  -out /etc/ssl/certs/[Name].crt
  ```

- **AI models**:
  **Speech-to-Text (STT)**
   - **Cloud**: OpenAI Whisper (whisper-1) — Very high quality, handles accents and background noise. 1-3 seconds response time. ~33 queries per 1 cent (basically free).
     ```
     pip install openai
     export OPENAI_API_KEY="your-openai-api-key"
     ```
   - **Local**: faster-whisper base.en — Fair quality, but slow. 5-10 seconds response time. Free.
     ```
     pip install faster-whisper
     ```

   **Text-to-Speech (TTS)**
   - **Cloud**: OpenAI TTS (gpt-4o-mini-tts) — Natural, human-like. 1-2 seconds response time. ~44 queries per 1 cent (basically free).
     ```
     pip install openai
     export OPENAI_API_KEY="your-openai-api-key"
     ```
   - **Local**: Piper lessac-medium — Clear but robotic, can't pronounce certain phrases. 2-4 seconds response time. Free.
     ```
     pip install piper-tts
     ```

   **Large Language Model (LLM)**
   - Cloud: Groq (llama-3.3-70b-versatile) — 70 Billion parameters. < 1 second response time. Free.
     ```
     pip install groq
     export GROQ_API_KEY="your-groq-api-key"
     ```
   - **Local**: TinyLlama — 1.1 Billion parameters. 10 seconds response time. Free.
     ```
     pip install llama-cpp-python
     ```

     Edit config.py to switch between local/cloud compute.


