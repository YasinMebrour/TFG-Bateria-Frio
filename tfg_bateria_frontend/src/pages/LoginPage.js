// src/pages/LoginPage.js
import { useState } from "react";
import { useAuth } from "../context/AuthContext";
import { useNavigate } from "react-router-dom";

import "../assets/styles/Login.css";

export default function LoginPage() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [form, setForm] = useState({ username: "", password: "" });
  const [error, setError] = useState(null);

  const handleChange = (e) =>
    setForm({ ...form, [e.target.name]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await login(form.username, form.password);
      nav("/", { replace: true });
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="login-page">
      <div className="login-page-wrapper">
        <form onSubmit={handleSubmit}>
          {error && <p className="error-text">{error}</p>}
          <input
            name="username"
            placeholder="Usuario"
            value={form.username}
            onChange={handleChange}
            required
          />
          <input
            name="password"
            type="password"
            placeholder="Contraseña"
            value={form.password}
            onChange={handleChange}
            required
          />
          <button type="submit">Entrar</button>
          <p
          className="forgot-password"
          onClick={() => nav("/forgot-password")}
          style={{ cursor: "pointer", color: "#007bff", marginTop: "1rem" }}
        >
          ¿Olvidaste tu contraseña?
        </p> 
        </form>

        
        <div className="login-page-drops">
          <div></div>
          <div></div>
          <div></div>
          <div></div>
          <div></div>
        </div>
      </div>
    </div>
  );
}
