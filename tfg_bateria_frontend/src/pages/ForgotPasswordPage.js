import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import "../assets/styles/Login.css";
import { useApi } from "../hooks/useApi";


export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState(null);
  const nav = useNavigate();
  const api = useApi();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setMessage(null);
    try {
      // Llamada a tu API de olvidé contraseña
      await api.post("/auth/forgot-password", { email });
      setMessage("Código enviado a tu correo.");
      nav("/reset-password", { state: { email } });
    } catch (err) {
      setMessage("Error al enviar el código. Intenta de nuevo.");
    }
  };

  return (
    <div className="login-page">
      <div className="login-page-wrapper">
        <h2 className="centered-title">
            Recuperar contraseña
        </h2>
        <form onSubmit={handleSubmit}>
          {message && <p className="error-text">{message}</p>}
          <input
            type="email"
            placeholder="Correo electrónico"
            value={email}
            onChange={e => setEmail(e.target.value)}
            required
          />
          <button type="submit">Enviar código</button>
        </form>
      </div>
    </div>
  );
}

