import { useState } from "react";
import { useNavigate } from "react-router-dom";

const Login: React.FC = () => {
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!name || !password) {
      setError("Please enter both name and password");
      return;
    }

    try {
      const response = await fetch("http://localhost:5000/api/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ name, password }),
      });

      const data = await response.json();

      if (response.ok) {
        setError("");
        alert(`Welcome, ${name}!`);

        // Pass stream URL to the next page via state
        navigate("/interaction", {
          state: { streamUrl: data.streamUrl, name },
        });
      } else {
        setError(data.message || "Login failed");
      }
    } catch (error) {
      console.error("Error during login:", error);
      setError("Unable to connect to server");
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
        </button>
      </form>
    </div>
  );
};

export default Login;
