import React from "react";
import { NavLink, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Navbar() {
  const { token, logout, user } = useAuth();
  const isEditor = user?.is_editor;
  const navigate = useNavigate();

  const location = useLocation();

  // No mostrar el nav en /login
  if (
    location.pathname === "/login" ||
    location.pathname === "/forgot-password" ||
    location.pathname === "/reset-password"
  ) {
    return null;
  }

  const handleLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  return (
    <nav style={styles.navbar}>
      <ul style={styles.navList}>
        
        <li>
          <NavLink to="/gemelo" style={({ isActive }) => isActive ? styles.activeLink : styles.link}>
            Gemelo
          </NavLink>
        </li>
        <li>
          {isEditor ? (
            <NavLink to="/planificador" style={({ isActive }) => isActive ? styles.activeLink : styles.link}>
              Planificador
            </NavLink> ) : (<span style={styles.disabledLink}>Planificador</span>
          )}
        </li>
        <li>
          <NavLink to="/dashboard" style={({ isActive }) => isActive ? styles.activeLink : styles.link}>
            Dashboard
          </NavLink>
        </li>
        <li>
          {isEditor ? (
            <NavLink to="/config" style={({ isActive }) => isActive ? styles.activeLink : styles.link}>
              Configuracion
            </NavLink> ) : (<span style={styles.disabledLink}>Configuración</span>
          )}
        </li>
         {token && (
          <li style={styles.logoutItem}>
            <button onClick={handleLogout} style={styles.logoutButton}>
              Cerrar sesión
            </button>
        </li>
        
        )}
      </ul>
    </nav>
  );
}

// Estilos en línea
const styles = {
  navbar: {
    background: "#333",
    padding: "10px",
  },
  navList: {
    display: "flex",
    listStyle: "none",
    justifyContent: "center",
    padding: 0,
    position: "relative",
  },
  link: {
    color: "white",
    textDecoration: "none",
    margin: "0 15px",
    fontSize: "18px",
  },
  activeLink: {
    color: "yellow", // Color del enlace cuando está activo
    textDecoration: "underline",
    fontWeight: "bold",
    margin: "0 15px",
    fontSize: "18px",
  },
  disabledLink:{ 
    color: "#777",
    margin: "0 15px", 
    fontSize: "18px", 
    cursor: "not-allowed" 
  },
  logoutItem: {
    position: "absolute",
    right: "10px",             // separación del borde derecho
    top: "50%",
    transform: "translateY(-50%)",  // lo centra verticalmente
  },
  logoutButton: {
    background: "transparent",
    border: "1px solid white",
    color: "white",
    padding: "5px 10px",
    cursor: "pointer",
    fontSize: "16px",
  },
};

