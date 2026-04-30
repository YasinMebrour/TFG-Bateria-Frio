import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function AdminRoute({ children }) {
  const { token, user, loadingUser } = useAuth();
  if (loadingUser) return null;
  return token && user?.is_editor ? children : <Navigate to="/" replace />;
}