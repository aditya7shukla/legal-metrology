import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      navigate("/");
    } catch (err) {
      setError(err.response?.data?.detail || "Login failed. Please check your credentials.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-brand-900 px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-6 text-white">
          <h1 className="text-2xl font-bold">Legal Metrology</h1>
          <p className="text-brand-100/80 text-sm">Compliance Checking System</p>
        </div>
        <form onSubmit={handleSubmit} className="card space-y-4">
          <div>
            <label className="label">Email</label>
            <input
              type="email" required className="input" value={email}
              onChange={(e) => setEmail(e.target.value)} placeholder="officer@legalmetrology.gov.in"
            />
          </div>
          <div>
            <label className="label">Password</label>
            <input
              type="password" required className="input" value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button type="submit" disabled={loading} className="btn-primary w-full">
            {loading ? "Signing in..." : "Sign in"}
          </button>
          <p className="text-xs text-gray-400 text-center pt-2">
            Demo: admin@legalmetrology.gov.in / ChangeMe@123
          </p>
        </form>
      </div>
    </div>
  );
}
