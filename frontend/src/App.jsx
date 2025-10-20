// src/App.jsx
import { Routes, Route, Navigate } from "react-router-dom";
import Dashboard from "../routes/Dashboard.jsx";
import LoginPage from "../routes/Login.jsx";
import RegisterPage from "../routes/Register.jsx";
export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/Login" replace />} />
      <Route path="/Login" element={<LoginPage />} />
      <Route path="/Register" element={<RegisterPage />} />
      <Route path="/Dashboard" element={<Dashboard />} />
      {/* 兜底：任何未知路径都重定向到登录页 */}
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}
