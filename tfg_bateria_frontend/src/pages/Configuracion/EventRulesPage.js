import React, { useState, useEffect } from "react";
import { useApi } from "../../hooks/useApi";
import { formatDuration } from "../../utils/time";
import "../../assets/styles/Users.css";

export default function EventRulesPage() {
  const api = useApi();
  const [rules, setRules] = useState([]);
  const [buckets, setBuckets] = useState([]);
  const [measurements, setMeasurements] = useState([]);
  const [fields, setFields] = useState([]);
  const [form, setForm] = useState({
    bucket: "",
    measurement: "",
    field: "",
    descripcion: "",
    operador: ">",
    valor_derecho: "",
    ventana_segundos: "60",
    frecuencia_segundos: "60",
    habilitada: true,
  });
  const [editingId, setEditingId] = useState(null);
  const [errors, setErrors] = useState([]);

  const loadRules = async () => {
    try {
      const data = await api.get("/reglas");
      setRules(data);
    } catch (e) {
      console.error("Cargando reglas:", e);
    }
  };

  useEffect(() => {
    loadRules();
    (async () => {
      try {
        const data = await api.get("/influx/buckets");
        setBuckets(data.buckets || []);
      } catch (e) {
        console.error("Cargando buckets:", e);
      }
    })();
  }, []);

  useEffect(() => {
    if (!form.bucket && buckets.length > 0) {
      setForm((f) => ({ ...f, bucket: buckets[0] }));
    }
  }, [buckets]);

  useEffect(() => {
    if (!form.bucket) {
      setMeasurements([]);
      return;
    }
    (async () => {
      try {
        const data = await api.get(
          `/influx/measurements?bucket=${encodeURIComponent(form.bucket)}`
        );
        setMeasurements(data.measurements || []);
      } catch (e) {
        console.error("Cargando measurements:", e);
      }
    })();
  }, [form.bucket]);

  useEffect(() => {
    if (!form.bucket || !form.measurement) {
      setFields([]);
      return;
    }
    (async () => {
      try {
        const data = await api.get(
          `/influx/fields?bucket=${encodeURIComponent(form.bucket)}&measurement=${encodeURIComponent(form.measurement)}`
        );
        setFields(data.fields || []);
      } catch (e) {
        console.error("Cargando fields:", e);
      }
    })();
  }, [form.bucket, form.measurement]);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm((f) => {
      const updated = { ...f, [name]: type === "checkbox" ? checked : value };
      if (name === "bucket") {
        updated.measurement = "";
        updated.field = "";
      } else if (name === "measurement") {
        updated.field = "";
      }
      return updated;
    });
  };

  const resetForm = () => {
    setForm({
      bucket: "",
      measurement: "",
      field: "",
      descripcion: "",
      operador: ">",
      valor_derecho: "",
      ventana_segundos: "60",
      frecuencia_segundos: "60",
      habilitada: true,
    });
    setEditingId(null);
    setErrors([]);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrors([]);
    const payload = {
      measurement: form.measurement,
      field: form.field,
      descripcion: form.descripcion,
      operador: form.operador,
      valor_derecho: form.valor_derecho,
      ventana_segundos: parseInt(form.ventana_segundos) || 0,
      frecuencia_segundos: parseInt(form.frecuencia_segundos) || 0,
      habilitada: form.habilitada,
      nombre: `${form.measurement}_${form.field}`,
      tipo_condicion: "comparacion",
    };

    try {
      if (editingId) {
        const updated = await api.put(`/reglas/${editingId}`, payload);
        setRules((prev) => prev.map((r) => (r.id === editingId ? updated : r)));
      } else {
        const created = await api.post("/reglas", payload);
        setRules((prev) => [...prev, created]);
      }
      resetForm();
    } catch (err) {
      setErrors(Array.isArray(err) ? err : [err.toString()]);
    }
  };

  const handleEdit = (rule) => {
    setEditingId(rule.id);
    setForm({
      bucket: buckets[0] || "",
      measurement: rule.measurement,
      field: rule.field,
      descripcion: rule.descripcion || "",
      operador: rule.operador,
      valor_derecho: rule.valor_derecho,
      ventana_segundos: rule.ventana_segundos,
      frecuencia_segundos: rule.frecuencia_segundos,
      habilitada: rule.habilitada,
    });
  };

  const handleDelete = async (id) => {
    if (!window.confirm("¿Eliminar regla?")) return;
    try {
      await api.delete(`/reglas/${id}`);
      setRules((prev) => prev.filter((r) => r.id !== id));
      if (editingId === id) resetForm();
    } catch (err) {
      alert("Error al borrar");
    }
  };

  return (
    <div className="usuarios-page">
      <div className="usuarios-grid">
        <section className="usuarios-section">
          <h2>{editingId ? "Editar regla" : "Crear regla"}</h2>
          <form onSubmit={handleSubmit}>
            {errors.length > 0 && (
              <div className="error-messages">
                {errors.map((msg, i) => (
                  <p key={i} className="error-text">{msg}</p>
                ))}
              </div>
            )}
            <div className="usuarios-form-group">
              <label htmlFor="bucket">Bucket</label>
              <select
                id="bucket"
                name="bucket"
                value={form.bucket}
                onChange={handleChange}
                required
              >
                <option value="">Selecciona bucket</option>
                {buckets.map((b) => (
                  <option key={b} value={b}>
                    {b}
                  </option>
                ))}
              </select>
            </div>
            <div className="usuarios-form-group">
              <label htmlFor="measurement">Measurement</label>
              <select
                id="measurement"
                name="measurement"
                value={form.measurement}
                onChange={handleChange}
                required
              >
                <option value="">Selecciona measurement</option>
                {measurements.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            </div>
            <div className="usuarios-form-group">
              <label htmlFor="field">Field</label>
              <select
                id="field"
                name="field"
                value={form.field}
                onChange={handleChange}
                required
              >
                <option value="">Selecciona field</option>
                {fields.map((f) => (
                  <option key={f} value={f}>
                    {f}
                  </option>
                ))}
              </select>
            </div>
            <div className="usuarios-form-group">
              <label htmlFor="descripcion">Descripción</label>
              <input
                id="descripcion"
                name="descripcion"
                value={form.descripcion}
                onChange={handleChange}
              />
            </div>
            <div className="usuarios-form-group">
              <label htmlFor="operador">Operador</label>
              <select
                id="operador"
                name="operador"
                value={form.operador}
                onChange={handleChange}
              >
                <option value=">">Mayor que</option>
                <option value=">=">Mayor o igual</option>
                <option value="<">Menor que</option>
                <option value="<=">Menor o igual</option>
                <option value="==">Igual a</option>
                <option value="!=">Distinto de</option>
              </select>
            </div>
            <div className="usuarios-form-group">
              <label htmlFor="valor_derecho">Valor</label>
              <input
                id="valor_derecho"
                name="valor_derecho"
                value={form.valor_derecho}
                onChange={handleChange}
                required
              />
            </div>
            <div className="usuarios-form-group">
              <label htmlFor="ventana_segundos">Ventana</label>
              <select
                id="ventana_segundos"
                name="ventana_segundos"
                value={form.ventana_segundos}
                onChange={handleChange}
                required
              >
                <option value="60">1 min</option>
                <option value="300">5 min</option>
                <option value="600">10 min</option>
                <option value="1800">30 min</option>
                <option value="3600">1 h</option>
                <option value="86400">24 h</option>
              </select>
            </div>
            <div className="usuarios-form-group">
              <label htmlFor="frecuencia_segundos">Frecuencia</label>
              <select
                id="frecuencia_segundos"
                name="frecuencia_segundos"
                value={form.frecuencia_segundos}
                onChange={handleChange}
                required
              >
                <option value="60">1 min</option>
                <option value="300">5 min</option>
                <option value="600">10 min</option>
                <option value="1800">30 min</option>
                <option value="3600">1 h</option>
                <option value="86400">24 h</option>
              </select>
            </div>
            <div className="usuarios-form-group">
              <label htmlFor="habilitada">Activa</label>
              <input
                type="checkbox"
                id="habilitada"
                name="habilitada"
                checked={form.habilitada}
                onChange={handleChange}
              />
            </div>
            <div className="usuarios-form-actions">
              <button type="submit" className="btn-save-user usuarios-btn-inline">
                {editingId ? "Guardar" : "Crear"}
              </button>
              {editingId && (
                <button
                  type="button"
                  className="btn-save-user usuarios-btn-inline"
                  onClick={resetForm}
                >
                  Cancelar
                </button>
              )}
            </div>
          </form>
        </section>
        <section className="usuarios-section">
          <h2>Reglas</h2>
          <table className="usuarios-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Measurement</th>
                <th>Field</th>
                <th>Descripción</th>
                <th>Oper.</th>
                <th>Valor</th>
                <th>Ventana</th>
                <th>Frecuencia</th>
                <th>Estado</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {rules.map((r) => (
                <tr key={r.id}>
                  <td>{r.id}</td>
                  <td>{r.measurement}</td>
                  <td>{r.field}</td>
                  <td>{r.descripcion}</td>
                  <td>{r.operador}</td>
                  <td>{r.valor_derecho}</td>
                  <td>{formatDuration(r.ventana_segundos)}</td>
                  <td>{formatDuration(r.frecuencia_segundos)}</td>
                  <td>{r.habilitada ? "Sí" : "No"}</td>
                  <td>
                    <button
                      onClick={() => handleEdit(r)}
                      className="btn-save-role"
                    >
                      Editar
                    </button>
                    <button
                      onClick={() => handleDelete(r.id)}
                      className="btn-save-role"
                      style={{ marginLeft: "0.5rem", background: "#dc2626" }}
                    >
                      Eliminar
                    </button>
                  </td>
                </tr>
              ))}
              {rules.length === 0 && (
                <tr>
                  <td colSpan="10" style={{ textAlign: "center", padding: "1rem" }}>
                    Sin reglas
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

