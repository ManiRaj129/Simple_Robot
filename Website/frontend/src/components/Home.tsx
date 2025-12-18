// Polyfill 
if (!('randomUUID' in crypto)) {
    (crypto as any).randomUUID = () => {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
            const r = crypto.getRandomValues(new Uint8Array(1))[0] % 16;
            const v = c === 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    };
}

import React from "react";
import { useNavigate } from "react-router-dom";
import robotImg from "../assets/logo/SimpleRobotLogo.svg";
import flowchartImg from "../assets/flowchat1.png";

const Home: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gray-100 text-gray-900 font-sans">
      <header className="flex justify-between items-center px-8 py-4 bg-white shadow-md sticky top-0 z-50">
        <div className="header-container flex items-center justify-center border-b-1 shadow-md p-1">
				<span className="logo-container cursor-pointer">
					<img
						className="w-[100px] center"
						src={robotImg}>
					</img> 
				</span>
        <span className="px-2">Simple Robot</span>
				</div>
        {/* <button
            onClick={() => navigate("/login")}
            className="px-6 py-2 mb-4 bg-black text-white rounded-lg hover:bg-gray-800 transition"
          >
            Login 
          </button> */}
      </header>

      <main className="flex flex-col items-center">
        <div className="max-w-4xl w-full my-8 p-6 text-center">
          <h2 className="text-2xl font-semibold mb-4">Simple Robot 🤖</h2>
          <img src={robotImg} alt="Robot" className="w-72 h-auto mx-auto rounded-lg shadow-md mb-4" />
          <button
            onClick={() => navigate("/interaction")}
            className="px-6 py-2 mb-4 bg-black text-white rounded-lg hover:bg-gray-800 transition"
          >
            Try Robot 
          </button>
          <p className="text-justify text-gray-700 leading-relaxed">
            We’ve built a robot powered by Raspberry Pi that can move, listen, and speak. It integrates Text-to-Speech (TTS),
            Speech-to-Text (STT), and a decision model, allowing it to interact naturally with people. The robot responds to
            voice commands, drives in multiple directions, and can be controlled remotely through a simple interface. <br />
            <br />
            Equipped with a camera, microphone, speaker, ultrasonic sensor, and screen, the robot not only supports manual
            driving but also lays the foundation for collision prevention, object detection, and autonomous exploration.
          </p>
        </div>

<div className="max-w-4xl w-full my-8 p-6 text-center">          
	{/* <h2 className="text-2xl font-semibold mb-4">Simple Robot 🤖</h2> */}
          <p className="text-gray-700 text-justify mb-4">
            We are excited to introduce SimpleBot as a hands-on platform for students, researchers, educators, and hobbyists.
            Whether you want to learn robotics from scratch, test new algorithms, or teach robotics in the classroom,
            SimpleBot provides an affordable and extensible starting point.
          </p>
          <img src={flowchartImg} alt="Flowchart" className="rounded-md border border-gray-200 shadow-sm max-w-full mx-auto" />
        </div>

<div className="max-w-4xl w-full my-8 p-6 text-center">
	          {/* <h2 className="text-2xl font-semibold mb-4">Simple Robot 🤖</h2> */}
          <p className="text-gray-700 text-justify leading-relaxed">
            This flowchart describes how a robot responds to a user request to move to a certain object in a room, integrating
            speech recognition, AI decision-making, and movement control.
            <br />
            <br />
            <strong>Activation:</strong> The robot waits for a wake word (like “Hey [Robot Name]”) to detect a command.
            <br />
            <strong>Input processing:</strong> Once activated, the robot listens and captures the user's spoken input. It
            transcribes the audio to text using a speech-to-text system.
            <br />
            <strong>AI decision-making:</strong> The transcribed input is sent to an AI model (e.g., ChatGPT or LLaMA), which
            interprets the command and decides the appropriate action.
            <br />
            <strong>Movement planning:</strong> The robot determines the location or object to move to and produces an audio
            response indicating the planned action.
            <br />
            <strong>Object detection:</strong> Using wheels and a camera, the robot scans its surroundings and detects objects.
            <br />
            <strong>Success/failure handling:</strong> The robot moves toward the object, updating its progress vocally, and
            stops if sensors indicate it is close enough.
          </p>
        </div>

<div className="max-w-4xl w-full my-8 p-6 text-center">
	          {/* <h2 className="text-2xl font-semibold mb-4">Simple Robot 🤖</h2> */}
          <p className="text-gray-700 text-justify leading-relaxed mb-4">
            Logging & feedback: All decisions, movements, and I/O actions are logged. The robot changes its display or
            expression to reflect its current state and waits for further instructions.
            <br />
            <br />
            Essentially, this flowchart shows an end-to-end interaction loop combining voice recognition, AI reasoning, robotic
            navigation, and user feedback, similar in spirit to how ChatGPT processes conversational input, interprets it, and
            provides a response—but in a physical robotic system.
          </p>

          <ul className="list-disc list-inside text-gray-700 mb-4 text-left mx-auto max-w-md">
            <li>🚗 Drive the robot forward, backward, left, or right</li>
            <li>🗣️ Speak a command, and hear it respond</li>
            <li>📸 Capture what the robot sees through its camera</li>
            <li>🤖 Enable autonomous navigation with future extensions</li>
          </ul>

          <p className="text-center mt-6 text-sm text-gray-600">
            This Simple Robot project was built by <b>Mani Raj Rejinthala</b>, <b>Ethan</b>, <b>Koushik Shaganti</b>, and{" "}
            <b>Kenny Jia Hui Leong</b>.
            <br />© 2025 Team Simple Robot
          </p>
        </div>
      </main>
    </div>
  );
};

export default Home;
