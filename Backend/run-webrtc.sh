
./pi-webrtc --camera=v4l2:8 \
  --v4l2-format=yuyv \
  --fps=30 \
  --width=1280 \
  --height=720 \
  --use-mqtt \
  --mqtt-host=localhost \
  --mqtt-port=1883 \
  --uid=Mekk \
  --no-audio \
  --enable-ipc \
  --ipc-channel=reliable

