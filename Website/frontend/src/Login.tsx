import { useState } from "react";
import { useNavigate } from "react-router-dom";

const Login: React.FC = () => {
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();

    if (!name || !password) {
      setError("Please enter both name and password");
      return;
    }

    if (password === "password") {
      setError("");
      alert(`Welcome, ${name}!`);
      navigate("/interaction"); // go to interaction page
    } else {
      setError("Incorrect password for robot");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <form
        onSubmit={handleLogin}
        className="bg-white p-6 rounded-lg shadow-md w-80 flex flex-col gap-4"
      >
        <h2 className="text-center text-xl font-semibold text-gray-800">
          Robot Login
        </h2>

        <input
          type="text"
          placeholder="Your Name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="border p-2 rounded focus:outline-none focus:ring-2 focus:ring-blue-400"
        />

        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="border p-2 rounded focus:outline-none focus:ring-2 focus:ring-blue-400"
        />

        {error && <p className="text-red-500 text-sm text-center">{error}</p>}

        <button
          type="submit"
          className="bg-blue-600 hover:bg-blue-700 text-white rounded py-2 transition"
        >
          Login
          {/* It should SSH and connect to the robot. */}
        </button>
      </form>
    </div>
  );
};

export default Login;
