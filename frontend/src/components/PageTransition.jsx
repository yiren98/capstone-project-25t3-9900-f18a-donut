// src/transition/PageTransition.jsx
import { motion } from "framer-motion";

export const SoftSlide = ({ children }) => (
  <motion.div
    initial={{ opacity: 0, y: 8, filter: "blur(2px)" }}
    animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
    exit={{ opacity: 0, y: -8, filter: "blur(2px)" }}
    transition={{ duration: 0.28, ease: [0.22, 0.61, 0.36, 1] }}
    style={{ willChange: "transform, opacity, filter" }}
  >
    {children}
  </motion.div>
);

export const CardFlip = ({ children }) => (
  <motion.div
    initial={{ opacity: 0, rotateX: -6, y: 6, transformPerspective: 800 }}
    animate={{ opacity: 1, rotateX: 0, y: 0 }}
    exit={{ opacity: 0, rotateX: 6, y: -6 }}
    transition={{ duration: 0.32, ease: [0.22, 0.61, 0.36, 1] }}
    style={{ transformStyle: "preserve-3d", willChange: "transform, opacity" }}
  >
    {children}
  </motion.div>
);

export const withTransition = (Comp, Variant = SoftSlide) =>
  function Wrapped(props) {
    return (
      <div className="min-h-screen" style={{ perspective: 1000 }}>
        <Variant>
          <Comp {...props} />
        </Variant>
      </div>
    );
  };
