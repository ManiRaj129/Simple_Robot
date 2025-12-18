import { ChannelId, PiCamera } from "picamera.js";
import { useEffect, type RefObject, useRef } from "react";

interface WebRTCProps {

	piCameraRef: RefObject<PiCamera | null>;
	isConnected: boolean;
	setIsConnected: React.Dispatch<React.SetStateAction<boolean>>;
	setIsLive: React.Dispatch<React.SetStateAction<boolean>>;
	setResponseMessage: (message: string) => void;
	refreshConnection: number;
	setRefreshConnection: React.Dispatch<React.SetStateAction<number>>;
}

function WebRTC({ piCameraRef, isConnected, setIsConnected,
				  setIsLive, setResponseMessage, refreshConnection,
				  setRefreshConnection }
				  :
				  WebRTCProps) {

	const videoRef = useRef<HTMLVideoElement>(null);
	useEffect(() => {

		/**
		 * Manual disconnect
		 */
		if (piCameraRef.current != null && refreshConnection == 4) {

			piCameraRef.current.terminate();
			setIsConnected(false);
			setIsLive(false);
			setRefreshConnection(3);
			return;
		}

		if (refreshConnection == 3 || refreshConnection == 0) return;
		else console.log('Manual connection refresh');

		/**
		 * If dissconnected or forced reconnection
		 *  host: window.location.hostname
		 */
		if (!isConnected || refreshConnection == 1){

			const connection = new PiCamera({
				deviceUid: 'Mekk',
				mqttHost:  window.location.hostname,
				mqttPath: '/mqtt',
				mqttPort: 8443,
				ipcMode: 'reliable',
				datachannelOnly: false,
				
			});

			connection.onStream = (stream: MediaStream) => {

				if(stream){

					console.log("Video stream received")
					if (videoRef.current) {

						videoRef.current.srcObject = stream ?? null;
						setIsLive(true);
						setRefreshConnection(0);
					}
				}
				else{
					console.log("Video stream stopped")
				}
				
			};

			connection.onTimeout = () => {

				console.log('Connection attempt timed out');
				setIsLive(false);
				setRefreshConnection(2);
			}

			connection.onConnectionState = (state: RTCPeerConnectionState) => {

				console.log(`Connection state changed to ${state}`);

				if (state === 'connected') {setIsConnected(true); setRefreshConnection(0)};
				if (state === 'failed' || state === 'disconnected' || state === 'closed') {setIsConnected(false); setIsLive(false); setRefreshConnection(2)};
			};

			connection.onDatachannel = (id: ChannelId) => {

				if (id === ChannelId.Reliable) {
					console.log("DataChannel is open")
				}
			}

			connection.onMessage = (message: string) => {
				const jsonObjects = message.split("\n");
				if (jsonObjects !=null) {
					jsonObjects.forEach(str => {
					try {
						if(str.trim() !="")
						{							
							setResponseMessage(str);
							console.log(`Getting onMessage ${str}`);
						}						
					} catch (e) {
						console.error("Error onMessage: ", str, e);
					}
					});
				}				
			}

			connection.connect();
			piCameraRef.current = connection;
		}
	}, [isConnected, refreshConnection]);

	return (
		<video
		className="rounded-xl"
		ref={videoRef}
		id="piCameraVideoElement"
		autoPlay
		playsInline
		muted>
	</video>
	)
}
export default WebRTC;