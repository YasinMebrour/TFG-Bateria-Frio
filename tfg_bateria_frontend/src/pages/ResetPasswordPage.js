import React, { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import "../assets/styles/Login.css";
import { useApi } from "../hooks/useApi";

export default function ResetPasswordPage() {
  const { state } = useLocation();
  const initialEmail = state?.email || "";
  const [code, setCode]             = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [errors, setErrors]         = useState([]);    // array de strings
  const [success, setSuccess]       = useState("");    // mensaje de éxito
  const nav                         = useNavigate();
  const api = useApi();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrors([]);
    setSuccess("");

    try {
      const res = await api.post("/auth/reset-password", {
        email:        initialEmail,
        code,
        new_password: newPassword,
      });
      // Si la respuesta es exitosa, api.post no lanza error
      setSuccess("Contraseña actualizada con éxito.");
      setTimeout(() => nav("/login", { replace: true }), 1500);

    } catch (e) {
      console.error(e);
      setErrors(["Error de red. Inténtalo de nuevo."]);
    }
  };

  return (
    <div className="login-page">
      <div className="login-page-wrapper">
        <h2 className="centered-title">
            Restablecer contraseña
        </h2>

        <form onSubmit={handleSubmit}>
          {/* Mensajes de error */}
          {errors.map((msg, i) => (
            <p key={i} className="error-text">{msg}</p>
          ))}

          {/* Mensaje de éxito */}
          {success && <p className="success-text">{success}</p>}

          <p>Código enviado a: <b>{initialEmail}</b></p>

          <input
            type="text"
            placeholder="Código de verificación"
            value={code}
            onChange={e => setCode(e.target.value)}
            required
          />

          <input
            type="password"
            placeholder="Nueva contraseña"
            value={newPassword}
            onChange={e => setNewPassword(e.target.value)}
            required
            minLength={6}
          />

          <button type="submit">Actualizar contraseña</button>
        </form>
      </div>
    </div>
  );
}
