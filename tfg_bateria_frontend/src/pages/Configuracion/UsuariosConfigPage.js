import React, { useState, useEffect } from "react";
import "../../assets/styles/Users.css";
import { useAuth } from "../../context/AuthContext";
import { useApi } from "../../hooks/useApi";

export default function UsuariosConfigPage() {
  
  const api = useApi();          // ← aquí tienes get/post/put/delete
  const [form,   setForm]   = useState({
    username:"",
    email:"",
    password:"",
    is_editor:false,
    telegram_chat_id:"",
    telegram_bot_token:"",
    telegram_notify:false,
  });
  const [users,  setUsers]  = useState([]);
  const [errors, setErrors] = useState([]);

  useEffect(() => {
    (async () => {
      try {
        const data = await api.get("/users?skip=0&limit=100");
        setUsers(data.map(u => ({
          id: u.id,
          username: u.nombre,
          email: u.email,
          is_editor: u.is_editor,
        })));
      } catch (e) {
        console.error("Carga usuarios:", e);
      }
    })();
  }, []);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((f) => ({ ...f, [name]: value }));
  };

  const handleSubmit = async e => {
    e.preventDefault();
    setErrors([]);
    try {
      const u = await api.post("/users/", {
        nombre:    form.username,
        email:     form.email,
        password:  form.password,
        is_editor: form.is_editor,
        telegram_chat_id: form.telegram_chat_id || null,
        telegram_bot_token: form.telegram_bot_token || null,
        telegram_notify: form.telegram_notify,
      });
      setUsers(prev => [...prev, {
        id: u.id,
        username: u.nombre,
        email: u.email,
        is_editor: u.is_editor,
      }]);
      setForm({
        username:"",
        email:"",
        password:"",
        is_editor:false,
        telegram_chat_id:"",
        telegram_bot_token:"",
        telegram_notify:false,
      });
    } catch (err) {
      setErrors(Array.isArray(err) ? err : [err.toString()]);
    }
  };

  const handleDelete = async id => {
    if (!window.confirm("¿Eliminar?")) return;
    try {
      await api.delete(`/users/${id}`);
      setUsers(prev => prev.filter(u => u.id !== id));
    } catch (err) {
      alert("Error al borrar: " + err);
    }
  };

  const handleRoleSelection = (id, valueYesNo) => {
    setUsers((prev) =>
      prev.map((u) =>
        u.id === id ? { ...u, is_editor: valueYesNo === "yes" } : u
      )
    );
  };

  const handleSaveRole = async (id, is_editor) => {
    try {
      const u = await api.put(`/users/${id}/role`, { is_editor });
      setUsers(prev => prev.map(o => o.id===u.id ? { ...o, is_editor: u.is_editor } : o));
    } catch (err) {
      setErrors(Array.isArray(err) ? err : [err.toString()]);
    }
  };

  /* ──────────────────── RENDER ──────────────────── */
  return (
    <div className="usuarios-page">
      <div className="usuarios-grid">
        {/* ─────── Registro ─────── */}
        <section className="usuarios-section">
          <h2>Registrar usuario</h2>
          <form onSubmit={handleSubmit}>
            {errors.length > 0 && (
              <div className="error-messages">
                {errors.map((msg, i) => (
                  <p key={i} className="error-text">
                    {msg}
                  </p>
                ))}
              </div>
            )}
            <div className="usuarios-form-group">
              <label htmlFor="username">Usuario</label>
              <input
                id="username"
                name="username"
                type="text"
                value={form.username}
                onChange={handleChange}
                required
              />
            </div>
            <div className="usuarios-form-group">
              <label htmlFor="email">Correo electrónico</label>
              <input
                id="email"
                name="email"
                type="email"
                value={form.email}
                onChange={handleChange}
                required
              />
            </div>
            <div className="usuarios-form-group">
              <label htmlFor="password">Contraseña</label>
              <input
                id="password"
                name="password"
                type="password"
                value={form.password}
                onChange={handleChange}
                required
                minLength={5}
              />
            </div>
            <div className="usuarios-form-group">
              <label htmlFor="role">Rol</label>
              <select
                id="role"
                value={form.is_editor ? "yes" : "no"}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    is_editor: e.target.value === "yes",
                  }))
                }
              >
                <option value="no">Visualizador</option>
                <option value="yes">Editor</option>
              </select>
            </div>
            <div className="usuarios-form-group">
              <label htmlFor="telegram_chat_id">Chat ID de Telegram</label>
              <input
                id="telegram_chat_id"
                name="telegram_chat_id"
                type="text"
                value={form.telegram_chat_id}
                onChange={handleChange}
              />
            </div>
            <div className="usuarios-form-group">
              <label htmlFor="telegram_bot_token">Token del bot</label>
              <input
                id="telegram_bot_token"
                name="telegram_bot_token"
                type="text"
                value={form.telegram_bot_token}
                onChange={handleChange}
              />
            </div>
            <div className="usuarios-form-group">
              <label>
                <input
                  type="checkbox"
                  name="telegram_notify"
                  checked={form.telegram_notify}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, telegram_notify: e.target.checked }))
                  }
                />
                {" "}Recibir notificaciones por Telegram
              </label>
            </div>
            <button type="submit" className="btn-save-user">
              Crear usuario
            </button>
          </form>
        </section>

        {/* ─────── Lista ─────── */}
        <section className="usuarios-section">
          <h2>Lista de usuarios</h2>
          <table className="usuarios-table">
            <thead>
              <tr>
                <th>Usuario</th>
                <th>Correo electrónico</th>
                <th>Rol</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td>{u.username}</td>
                  <td>{u.email}</td>
                  <td>
                    <select
                      value={u.is_editor ? "yes" : "no"}
                      onChange={(e) =>
                        handleRoleSelection(u.id, e.target.value)
                      }
                      className="role-select"
                    >
                      <option value="no">Visualizador</option>
                      <option value="yes">Editor</option>
                    </select>
                  </td>
                  <td>
                    <button
                      onClick={() => handleDelete(u.id)}
                      className="btn-delete-user"
                    >
                      Eliminar
                    </button>
                    <button
                      onClick={() => handleSaveRole(u.id, u.is_editor)}
                      className="btn-save-role"
                      style={{ marginLeft: "0.5rem" }}
                    >
                      Guardar
                    </button>
                  </td>
                </tr>
              ))}
              {users.length === 0 && (
                <tr>
                  <td colSpan="4" style={{ textAlign: "center", padding: "1rem" }}>
                    No hay usuarios registrados.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </section>
      </div>
    </div>
  );
}
