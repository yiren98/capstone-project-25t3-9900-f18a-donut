// src/App.jsx
import { Routes, Route, Navigate, useLocation } from "react-router-dom";
import { AnimatePresence } from "framer-motion";

import Dashboard from "../routes/Dashboard.jsx";
import CultureAnalysis from "../routes/CultureAnalysis.jsx";
import { withTransition, SoftSlide /*, CardFlip*/ } from "../src/components/PageTransition.jsx";

// 选择一个过渡方案：SoftSlide 或 CardFlip
const TDashboard = withTransition(Dashboard, SoftSlide);
// const TDashboard = withTransition(Dashboard, CardFlip);
const TCulture = withTransition(CultureAnalysis, SoftSlide);
// const TCulture = withTransition(CultureAnalysis, CardFlip);

function AnimatedRoutes() {
  const location = useLocation();
  return (
    <AnimatePresence mode="wait">
      {/* 关键：把 location & key 传入，确保离场动画生效 */}
      <Routes location={location} key={location.pathname}>
        {/* Dashboard */}
        <Route path="/" element={<Navigate to="/Dashboard" replace />} />

        <Route path="/Dashboard" element={<TDashboard />} />
        <Route path="/Culture-Analysis" element={<TCulture />} />

        {/* 404 fallback */}
        <Route path="*" element={<Navigate to="/Dashboard" replace />} />
      </Routes>
    </AnimatePresence>
  );
}

export default function App() {
  return <AnimatedRoutes />;
}
