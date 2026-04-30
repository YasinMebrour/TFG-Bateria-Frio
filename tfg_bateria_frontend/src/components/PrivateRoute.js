import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function PrivateRoute({ children }) {
  const { token, loadingUser } = useAuth();
  if (loadingUser) return null;  // o un spinner
  return token ? children : <Navigate to="/login" replace />;
}