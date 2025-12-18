import React, { useState, useRef, useEffect } from "react";
import SRLogo from '../assets/logo/SimpleRobotLogo.svg';
import { useNavigate } from "react-router-dom";
import { PiCamera } from 'picamera.js';
import WebRTC from "../components/WebRTC"
import { toast } from "react-toastify";
import 'react-toastify/dist/ReactToastify.css'

type CommandBarData = {
  textCommand: string;
};

type LiveFeedData = {
  textLog: string[];
};

function Interaction() {
  const [userCommand, setUserCommand] = useState<CommandBarData>({
    textCommand: "",
  });

  const [robotLog, setRobotLog] = useState<LiveFeedData>({
    textLog: [
      `${new Date().toLocaleTimeString()} - Opened remote control website`,
    ],
  });

  const [objectsFound, setObjetsFound] = useState<Set<string>>(new Set());

  return (
    <>
      <DisplayHeader />
      <InteractionBody userCommand={userCommand} setUserCommand={setUserCommand} 
                       robotLog={robotLog} setRobotLog={setRobotLog}
                       objectsFound={objectsFound} setObjectsFound={setObjetsFound}/>
    </>
  );
}
export default Interaction;

function DisplayHeader() {
  let navigation = useNavigate();

  return (
    <>
      <div className="header-container flex items-center justify-center border-b-1 shadow-md">
        <div className="logo-container cursor-pointer">
          <img
            className="w-[100px]"
            src={SRLogo}
            alt="SimpleRobotLogo"
            onClick={() => navigation("/home")}
          />
        </div>
        <div className="p-5" />
        <p className="text-3xl">Simple Robot</p>
      </div>
    </>
  );
}

interface InteractionBodyProps {
  userCommand: CommandBarData;
  setUserCommand: React.Dispatch<React.SetStateAction<CommandBarData>>;
  robotLog: LiveFeedData;
  setRobotLog: React.Dispatch<React.SetStateAction<LiveFeedData>>;
  objectsFound: Set<string>;
  setObjectsFound: React.Dispatch<React.SetStateAction<Set<string>>>;
};

function InteractionBody({ userCommand, setUserCommand, robotLog, 
                           setRobotLog, objectsFound, setObjectsFound }
                          :
                          InteractionBodyProps) {

  const [isTextAreaFocus, setIsTextAreaFocus] = useState<boolean>(false);
  /**
   * 0-connection established 1-establishing connection 2-connection timeout 3-waiting for input 4-disconnect
   */
  const [refreshConnection, setRefreshConnection] = useState<number>(3);
  const [responseMessage, setResponseMessage] = useState<string>("");
  // initially in autonoous state
  const [manualAutonomous, setManualAutonomous] = useState<boolean>(true);

  const piCameraRef = useRef<PiCamera | null>(null);
  const [isConnected, setIsConnected] = useState<boolean>(false);

  /**
   * For sending movement commands to RPi
   * @param command desired command type and description in json strigified format
   * @returns 
   */
  const sendCommand = (command: string) => {

    if (!isConnected) {
      console.log('Not connected for command sending');
      toast.error("Not connected to robot for command sending")
      return;
    }

    if (piCameraRef.current) {
      piCameraRef.current.sendMessage(command);
      console.log(`Sending command: ${command}`)
    }
  };

  return (
    <div className="interaction-body-container flex flex-col p-5 sm:px-10 2xl:px-40">
      <div className="live-camera-feed-container flex flex-col lg:flex-row">
        <div className="live-camera-container flex flex-[2.3] shadow-md rounded-xl">
          <DisplayLiveCamera piCameraRef={piCameraRef} isConnected={isConnected} setIsConnected={setIsConnected}
                             sendCommand={sendCommand} isTextAreaFocus={isTextAreaFocus} refreshConnection={refreshConnection}
                             setRefreshConnection={setRefreshConnection} setResponseMessage={setResponseMessage} manualAutonomous={manualAutonomous}/>
        </div>
        <div className="p-3" />
        <div
          className="live-feed-nearest-object-command-bar-container flex flex-col lg:flex-1 
								border-1 shadow-md rounded-xl p-4 h-[550px] lg:h-[600px]">
          <DisplayLiveFeed robotLog={robotLog}/>
          <DisplayNearestObject objectsFound={objectsFound} setObjectsFound={setObjectsFound} responseMessage={responseMessage}
                                setResponseMessage={setResponseMessage} manualAutonomous={manualAutonomous}/>
          <div className="p-2" />
          <DisplayCommandBar userCommand={userCommand} setUserCommand={setUserCommand} setRobotLog={setRobotLog} 
                             setIsTextAreaFocus={setIsTextAreaFocus} sendCommand={sendCommand} responseMessage={responseMessage}
                             setResponseMessage={setResponseMessage} manualAutonomous={manualAutonomous} isConnected={isConnected}/>
        </div>
      </div>
      <div className="p-3" />
      <div className="connect-disconnect-container">
        <DisplayConnectDisconnect refreshConnection={refreshConnection} setRefreshConnection={setRefreshConnection} setRobotLog={setRobotLog}
                                  isConnected={isConnected} sendCommand={sendCommand} responseMessage={responseMessage}
                                  manualAutonomous={manualAutonomous} setManualAutonomous={setManualAutonomous}/>
      </div>
    </div>
  );
}

interface DisplayLiveCameraProps {
  piCameraRef: React.RefObject<PiCamera | null>;
  isConnected: boolean;
  setIsConnected: React.Dispatch<React.SetStateAction<boolean>>;
  sendCommand: (command: string) => void;
  isTextAreaFocus: boolean;
  refreshConnection: number;
  setRefreshConnection: React.Dispatch<React.SetStateAction<number>>;
  setResponseMessage: (response: string) => void;
  manualAutonomous: boolean;
}

function DisplayLiveCamera({ piCameraRef, isConnected, setIsConnected, sendCommand, 
                             isTextAreaFocus, refreshConnection, setRefreshConnection,
                             setResponseMessage, manualAutonomous }
                             :
                             DisplayLiveCameraProps) {

  const [isLive, setIsLive] = useState<boolean>(false);
  

  const containerRef = useRef<HTMLDivElement>(null);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      if (containerRef.current) {
        containerRef.current.requestFullscreen().then(() => {
          setIsFullscreen(true);
        }).catch(err => {
          console.error("Failed to enter fullscreen:", err);
        });
      }
    } else {
      document.exitFullscreen().then(() => {
        setIsFullscreen(false);
      }).catch(err => {
        console.error("Failed to exit fullscreen:", err);
      });
    }
  };

  const [isPressedW, setIsPressedW] = useState<boolean>(false);
  const [isPressedA, setIsPressedA] = useState<boolean>(false);
  const [isPressedD, setIsPressedD] = useState<boolean>(false);
  const [isPressedS, setIsPressedS] = useState<boolean>(false);
  const [isKeyDown, setIsKeyDown] = useState<boolean>(false);

  const handlePress = (button: number) => {

    if (manualAutonomous == false) return;
    // prevent continuous input on key hold
    if (isKeyDown) return;

    switch (button) {
      case 0:
        setIsPressedW(true);
        setIsKeyDown(true);
        console.log("W");
        console.log('Command send attempt: move forward');
        sendCommand('{"type": "motor", "command": "front"}');
        break;
      case 1:
        setIsPressedA(true);
        setIsKeyDown(true);
        console.log("A");
        console.log('Command send attempt: move left');
        sendCommand('{"type": "motor", "command": "left"}');
        break;
      case 2:
        setIsPressedD(true);
        setIsKeyDown(true);
        console.log("D");
        console.log('Command send attempt: move right');
        sendCommand('{"type": "motor", "command": "right"}');
        break;
      case 3:
        setIsPressedS(true);
        setIsKeyDown(true);
        console.log("S");
        console.log('Command send attempt: move backward');
        sendCommand('{"type": "motor", "command": "back"}');
        break;
      default:
        break;
    }
  }

  const handleRelease = (button: number) => {

    if (manualAutonomous == false) return;

    switch (button) {
      case 0:
        setIsPressedW(false);
        setIsKeyDown(false);
        break;
      case 1:
        setIsPressedA(false);
        setIsKeyDown(false);
        break;
      case 2:
        setIsPressedD(false);
        setIsKeyDown(false);
        break;
      case 3:
        setIsPressedS(false);
        setIsKeyDown(false);
        break;
      default:
        break;
    }
  }

  useEffect(() => {

    if (manualAutonomous == false) return;

    if (isTextAreaFocus) return;

    const handleKeyDown = (event: KeyboardEvent): void => {

      if (event.key == 'w' || event.key == 'W' && !isKeyDown) {
        handlePress(0);
      }
      if (event.key == 'a' || event.key == 'A' && !isKeyDown) {
        handlePress(1);
      }
      if (event.key == 'd' || event.key == 'D' && !isKeyDown) {
        handlePress(2);
      }
      if (event.key == 's' || event.key == 'S' && !isKeyDown) {
        handlePress(3);
      }
    };

    const handleKeyUp = (event: KeyboardEvent): void => {

      if (event.key == 'w' || event.key == 'W'){
        handleRelease(0);
      }
      if (event.key == 'a' || event.key == 'A'){
        handleRelease(1);
      }
      if (event.key == 'd' || event.key == 'D'){
        handleRelease(2);
      }
      if (event.key == 's' || event.key == 'S'){
        handleRelease(3);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
    };

  }, [isKeyDown, isTextAreaFocus]);

  return (
    <>
      <div
        ref={containerRef}
        className="live-camera-main-container relative flex w-full h-[600px] flex-col justify-center items-center"
      >
        <div className="video-container absolute w-full bg-black rounded-xl flex justify-center h-full">
          <WebRTC piCameraRef={piCameraRef} isConnected={isConnected} setIsConnected={setIsConnected}
              setIsLive={setIsLive} setResponseMessage={setResponseMessage} refreshConnection={refreshConnection}
              setRefreshConnection={setRefreshConnection}/>
        </div>
        <div
          className={`live-status-container absolute top-[10px] right-[10px] border-1 
                py-3 px-8 rounded-xl text-white
                ${isLive ? "bg-[#D50000]" : "bg-[#2e2e2e]"}`}
        >
          <p>LIVE</p>
        </div>
        {manualAutonomous && <div className="robot-movement-commands-container absolute bottom-[10px] left-[10px] flex-col
                        text-white bg-[#2e2e2e] text-3xl p-2 items-center flex rounded-xl shadow-md">
            <button className={`p-2 border-1 rounded-md w-[50px] hover:bg-white hover:text-black ease-in-out
                              transition duration-100 cursor-pointer shadow-md h-[50px]
                              ${isPressedW ?
                              "scale-95 transform -translate-y-1 bg-white text-black"
                              :
                              "scale-100"}
                              `}
                    onMouseDown={() => handlePress(0)}
                    onMouseUp={() => handleRelease(0)}
                    onMouseLeave={() => handleRelease(0)}>
              W
            </button>
            <div className="left-right-buttons-container flex-row flex">
              <button className={`p-2 border-1 rounded-md w-[50px] hover:bg-white hover:text-black ease-in-out
                                transition duration-100 cursor-pointer shadow-md h-[50px]
                                ${isPressedA ?
                                "scale-95 transform -translate-x-1 bg-white text-black"
                                :
                                "scale-100"}
                                `}
                      onMouseDown={() => handlePress(1)}
                      onMouseUp={() => handleRelease(1)}
                      onMouseLeave={() => handleRelease(1)}>
                A
              </button>
              <div className="w-[50px]"/>
              <button className={`p-2 border-1 rounded-md w-[50px] hover:bg-white hover:text-black ease-in-out
                                transition duration-100 cursor-pointer shadow-md h-[50px]
                                ${isPressedD ?
                                "scale-95 transform translate-x-1 bg-white text-black"
                                :
                                "scale-100"}
                                `}
                      onMouseDown={() => handlePress(2)}
                      onMouseUp={() => handleRelease(2)}
                      onMouseLeave={() => handleRelease(2)}>
                D
              </button>
            </div>
            <button className={`p-2 border-1 rounded-md w-[50px] hover:bg-white hover:text-black ease-in-out
                              transition duration-100 cursor-pointer shadow-md h-[50px]
                              ${isPressedS ?
                              "scale-95 transform translate-y-1 bg-white text-black"
                              :
                              "scale-100"}
                              `}
                    onMouseDown={() => handlePress(3)}
                    onMouseUp={() => handleRelease(3)}
                    onMouseLeave={() => handleRelease(3)}>
              S
            </button>
        </div>}

        {isLive ? (
          <>
            <button
              onClick={toggleFullscreen}
              className="absolute bottom-4 right-4 bg-[#D50000] text-white px-4 py-2 rounded shadow-md hover:bg-white hover:text-[#D50000] transition duration-200 ease-in-out cursor-pointer"
            >
              {isFullscreen ? "Exit Fullscreen" : "Fullscreen"}
            </button>
          </>
        ) : (
          refreshConnection == 1 ? (
            <div className="connection-message-container flex flex z-[1] text-white">
              <p className="text-3xl text-center">Establishing connection...</p>
            </div>
          ) : (
            refreshConnection == 3 ? (
              <div className="connection-message-container flex z-[1] text-white">
                <p className="text-3xl text-center">Press connect to establish connection</p>
              </div>
            ) : (
              <div className="connection-message-container flex z-[1] text-white">
                <p className="text-3xl text-center">Connection timed out. Please try again</p>
              </div>
            )
          )
        )}
      </div>
    </>
  );
}

type DisplayLiveFeedProps = {
  robotLog: LiveFeedData;
};

function DisplayLiveFeed({ robotLog }: DisplayLiveFeedProps) {

  const liveFeedContainerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {

    if (liveFeedContainerRef.current) {
      liveFeedContainerRef.current.scrollTop = liveFeedContainerRef.current.scrollHeight;
    }
  }, [robotLog]);

  return (
    <>
      <div className="text-xl text-center mb-2">
        <p>Robot Log</p>
      </div>
      <div className="live-feed-main-container flex flex-2 flex-col border-1 rounded-tl-md p-2
                      rounded-tr-md overflow-auto shadow-md"
           ref={liveFeedContainerRef}>
        <div className="live-feed-text">
          {robotLog.textLog.map((text: string, index: number) => (
            <p key={index}>{text}</p>
          ))}
        </div>
      </div>
    </>
    
  );
}

type DisplayNearestObjectProps = {
  objectsFound: Set<string>;
  setObjectsFound: React.Dispatch<React.SetStateAction<Set<string>>>;
  responseMessage: string;
  setResponseMessage: (response: string) => void;
  manualAutonomous: boolean;
};

function DisplayNearestObject({ objectsFound, setObjectsFound, responseMessage,
                                setResponseMessage, manualAutonomous } 
                              :
                              DisplayNearestObjectProps) {

  const [nearestObject, setNearestObject] = useState<string>("No nearest object detected");

  

  useEffect(() => {

    if (manualAutonomous){
      setNearestObject("Switch to autonomous mode to see nearest object(s) detected");
    }
    else {
      if (nearestObject.trim() === ""){
        setNearestObject("No nearest object detected");
      }
    }
  }, [manualAutonomous])

  useEffect(() => {

    if (responseMessage.trim() === ""){
      console.log("response string is empty")
    }
    else {

      try {
        const jsonObject = JSON.parse(responseMessage)

        if (jsonObject.type == "objects") {
          console.log(`Receive log jsonObject: type: ${jsonObject.type}, command: ${jsonObject.command}`)
          
          setObjectsFound((prev) => {

            const updatedSet = new Set([...prev, ...jsonObject.command]);
            return updatedSet;
          });
          
          setNearestObject(jsonObject.command.sort().join(", "));
          setResponseMessage("")
        }
        
      } catch (error) {
        console.error("Error parsing JSON:", error)
      }
    }
  }, [responseMessage])

  return (
    <>
      <div className="text-xl text-center p-2">
        <p>Nearest Object</p>
      </div>
      <div
        className="nearest-object-main-container flex flex-[0.5] border-1  
                   px-2 shadow-md py-[0.5] overflow-auto py-2"
      >
        <p>{nearestObject}</p>
      </div>
      <div className="text-xl text-center p-2">
        <p>Objects Found</p>
      </div>
      <div className="all-objects-main-container flex flex-[0.7] border-1 rounded-bl-md 
              rounded-br-md px-2 shadow-md py-[0.5] overflow-auto py-2 whitespace-pre">
          {manualAutonomous ?
            <p>Switch to autonomous mode to see all objects found</p>
            :
            <p>{Array.from(objectsFound).sort().join("\n")}</p>
          }
      </div>
    </>
  );
}

type DisplayCommandBarProps = {
  userCommand: CommandBarData;
  setUserCommand: React.Dispatch<React.SetStateAction<CommandBarData>>;
  setRobotLog: React.Dispatch<React.SetStateAction<LiveFeedData>>;
  setIsTextAreaFocus: React.Dispatch<React.SetStateAction<boolean>>;
  sendCommand: (command: string) => void;
  responseMessage: string;
  setResponseMessage: (response: string) => void;
  manualAutonomous: boolean;
  isConnected: boolean;
};

function DisplayCommandBar({ userCommand, setUserCommand, setRobotLog,
                             setIsTextAreaFocus, sendCommand, responseMessage,
                             setResponseMessage, manualAutonomous, isConnected }
                            :
                            DisplayCommandBarProps) {
  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setUserCommand({
      textCommand: e.target.value,
    });
    // debug
    //console.log(e.target.value);
  };

  useEffect(() => {

    if (responseMessage.trim() === ""){
      console.log("response string is empty")
    }
    else {

      try {
        const jsonObject = JSON.parse(responseMessage)

        if (jsonObject.type == "log") {
          console.log(`Receive log jsonObject: type: ${jsonObject.type}, command: ${jsonObject.command}`)

          setRobotLog((prevLog) => ({
            ...prevLog,
            textLog: [...prevLog.textLog, 
                      `${new Date().toLocaleTimeString()} - ${jsonObject.command}`],
          }));
           setResponseMessage("")
        }
       
      } catch (error) {
        console.error("Error parsing JSON:", error)
      }
    }
  }, [responseMessage])

  const [sendIsPressed, setSendIsPressed] = useState(false);

  const handlePress = () => setSendIsPressed(true);
  const handleRelease = () => setSendIsPressed(false);

  return (
    <div className="command-bar-main-container flex flex-1 border-1 rounded-md relative">
      <textarea
        className="bg-white px-2 w-full rounded-md m-1 p-2"
        name="textCommand"
        value={userCommand.textCommand}
        placeholder={manualAutonomous ? "Switch to autonomous mode to use robot commands" : "Type your robot commands here"}
        onChange={handleChange}
        required
        onFocus={() => {setIsTextAreaFocus(true); console.log("focus true")}}
        onBlur={() => {setIsTextAreaFocus(false); console.log("focus false")}}
      />

      {manualAutonomous == false && <button className={`absolute right-[4px] bottom-[4px] bg-[#2e2e2e] p-2 px-4 text-white 
                         rounded-md cursor-pointer hover:bg-white hover:text-black border-1
                         transition ease-in-out duration-100 text-md
                         ${sendIsPressed ?
                          "scale-87"
                          :
                          "scale-100"
                         }`}
              onMouseDown={handlePress}
              onMouseUp={handleRelease}
              onMouseLeave={handleRelease}
              onClick={() => {
                isConnected && setUserCommand({
                  textCommand: '',
                });
                sendCommand(`{"type": "find", "command": "${userCommand.textCommand}"}`)
              }}>
        Send
      </button>}
    </div>
  );
}

interface DisplayManualAutonomousProps {
  isConnected: boolean;
  sendCommand: (command: string) => void;
  setRobotLog: React.Dispatch<React.SetStateAction<LiveFeedData>>;
  responseMessage: string;
  manualAutonomous: boolean;
  setManualAutonomous: React.Dispatch<React.SetStateAction<boolean>>;
}

function DisplayManualAutonomous({ isConnected, sendCommand, setRobotLog, responseMessage,
                                   manualAutonomous, setManualAutonomous }
                                   :
                                   DisplayManualAutonomousProps){

  useEffect(() => {

    if (responseMessage.trim() === ""){
      console.log("response string is empty")
    }
    else {
      console.log("mode :"+ responseMessage)
      try {
        const jsonObject = JSON.parse(responseMessage)
          
          if (jsonObject.type == "mode") {

            console.log(`Receive mode jsonObject: type: ${jsonObject.type} command: ${jsonObject.command}`)

            if (jsonObject.command == "manual"){
              setManualAutonomous(true)
              toast.success("Robot exploration mode set to manual")
            }
            else if (jsonObject.command == "autonomous") {
              console.log(`Changing mode to autonomous with command: ${jsonObject.command}`)
              toast.success("Robot exploration mode set to autonomous")
              setManualAutonomous(false)
            }

            setRobotLog((prevLog) => ({
              ...prevLog,
              textLog: [...prevLog.textLog, 
                        `${new Date().toLocaleTimeString()} - Exploration mode switched to ${jsonObject.command}`],
            }));
        }
      } catch (error) {
        console.error("Error parsing JSON:", error)
      }
    }
  }, [responseMessage])

  const [isHovering, setIsHovering] = useState<boolean>(false);

  return (
    <button className={`border-1 text-black lg:w-[267px] p-2 text-xl rounded-md cursor-pointer 
                        top-0 hover:bg-white hover:text-[#5496ff] transition
                        duration-200 ease-in-out px-5 shadow-md`}
            onMouseEnter={() => setIsHovering(true)}
            onMouseLeave={() => setIsHovering(false)}
            onClick={() => {
                      if (!isConnected) {
                        toast.error("Not connected to robot for exploration mode toggle");
                        console.log("Not connected for exploration mode toggle");
                        return;
                      }

                      if (manualAutonomous) {
                        sendCommand(`{"type": "mode", "command": "autonomous"}`);
                        setRobotLog(prevLog => ({
                          ...prevLog,
                          textLog: [
                            ...prevLog.textLog,
                            `${new Date().toLocaleTimeString()} - Changing to autonomous exploration`,
                          ],
                        }));
                      } else {
                        sendCommand(`{"type": "mode", "command": "manual"}`);
                        setRobotLog(prevLog => ({
                          ...prevLog,
                          textLog: [
                            ...prevLog.textLog,
                            `${new Date().toLocaleTimeString()} - Changing to manual exploration`,
                          ],
                        }));
                      }
                    }}
            >
      {isHovering ? "Change Mode?" : manualAutonomous ? "Manual Exploration" : "Autonomous Exploration"}
    </button>
  )
}

interface DisplayConnectDisconnectProps {
  refreshConnection: number;
  setRefreshConnection: React.Dispatch<React.SetStateAction<number>>;
  setRobotLog: React.Dispatch<React.SetStateAction<LiveFeedData>>;
  isConnected: boolean;
  sendCommand: (command: string) => void;
  responseMessage: string;
  manualAutonomous: boolean;
  setManualAutonomous: React.Dispatch<React.SetStateAction<boolean>>;
}

function DisplayConnectDisconnect({ refreshConnection, setRefreshConnection, setRobotLog,
                                    isConnected, sendCommand, responseMessage,
                                    manualAutonomous, setManualAutonomous }
                                    :
                                    DisplayConnectDisconnectProps) {

  const ConnectionStatus = {
  Disconnected: "Disconnected",
  Connecting: "Connecting",
  Connected: "Connected"
  } as const;

  type ConnectionStatus = typeof ConnectionStatus[keyof typeof ConnectionStatus];


  const connectionColor = { Disconnected:"#fc030b",Connecting: "#fcb103", Connected:"#03fc52"};
  const [currentConnection, setCurrentConnection] = useState<ConnectionStatus>(ConnectionStatus.Disconnected);

  useEffect(() => {

    if (refreshConnection == 3){
      setCurrentConnection(ConnectionStatus.Disconnected);
    }
    else if (refreshConnection == 2){
      setCurrentConnection(ConnectionStatus.Disconnected);
      setRobotLog((prevLog) => ({
        ...prevLog,
        textLog: [...prevLog.textLog, 
                  `${new Date().toLocaleTimeString()} - Disconnected from robot`],
      }));
    }
    else if (refreshConnection == 1){
      setCurrentConnection(ConnectionStatus.Connecting);
      setRobotLog((prevLog) => ({
        ...prevLog,
        textLog: [...prevLog.textLog, 
                  `${new Date().toLocaleTimeString()} - Connecting to robot`],
      }));
    }
    else if (refreshConnection == 0){
      setCurrentConnection(ConnectionStatus.Connected);
      setRobotLog((prevLog) => ({
        ...prevLog,
        textLog: [...prevLog.textLog, 
                  `${new Date().toLocaleTimeString()} - Robot connection established`],
      }));
    }
    else {
      setCurrentConnection(ConnectionStatus.Disconnected);
    }

  }, [refreshConnection])

  return (
    <div className="connect-disconnect-main-container flex flex-col lg:flex-row">
      <div className="connection-strength-container flex flex-row flex-1 text-xl ">
        <p className="whitespace-pre">{`Robot Connection : `}</p>
        <p style={{ color: connectionColor[currentConnection] }}>
          {ConnectionStatus[currentConnection]}
        </p>
      </div>
      <div className="p-3"/>
      <div className="connect-disconnect-btn-container flex flex-col lg:flex-row">
        <DisplayManualAutonomous isConnected={isConnected} sendCommand={sendCommand} setRobotLog={setRobotLog}
                                 responseMessage={responseMessage} manualAutonomous={manualAutonomous} setManualAutonomous={setManualAutonomous}/>
        <span className="p-2"/>
        <button className=" border-1 bg-[#00ad2e] text-white
                            p-2 text-xl rounded-md cursor-pointer top-0
                            hover:bg-white hover:text-[#00ad2e] transition
                            duration-200 ease-in-out px-5 shadow-md"
                onClick={() => {
                  setRefreshConnection(1);
                  console.log("Connection refresh button pressed")
                }}>
          Connect
        </button>
        <span className="p-1"/>
        <button className=" border-1 bg-[#D50000] text-white
                            p-2 text-xl rounded-md cursor-pointer top-0
                            hover:bg-white hover:text-[#D50000] transition
                            duration-200 ease-in-out px-5 shadow-md"
                onClick={() => {
                  refreshConnection != 3 && setRefreshConnection(4);
                  console.log("Disconnect button pressed");
                  refreshConnection != 3 && setRobotLog((prevLog) => ({
                    ...prevLog,
                    textLog: [...prevLog.textLog, 
                              `${new Date().toLocaleTimeString()} - Disconnected from robot`],
                  }));
                }}>
          Disconnect
        </button>
      </div>
    </div>
  );
}