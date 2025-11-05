// src/App.jsx
import { Routes, Route, Navigate } from "react-router-dom";
import Dashboard from "../routes/Dashboard.jsx";
import CultureAnalysis from "../routes/CultureAnalysis.jsx";

export default function App() {
  return (
    <Routes>
      {/* Dashboard */}
      <Route path="/" element={<Navigate to="/Dashboard" replace />} />

      <Route path="/Dashboard" element={<Dashboard />} />
      <Route path="/Culture-Analysis" element={<CultureAnalysis />} />

      {/* 404 fallback */}
      <Route path="*" element={<Navigate to="/Dashboard" replace />} />
    </Routes>
  );
}
