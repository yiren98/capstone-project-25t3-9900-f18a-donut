/* eslint-disable react-refresh/only-export-components */
import { motion as Motion } from "framer-motion";

// Gentle slide / fade-in wrapper used for page-level transitions
export const SoftSlide = ({ children }) => (
  <Motion.div
    initial={{ opacity: 0, y: 8, filter: "blur(2px)" }}
    animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
    exit={{ opacity: 0, y: -8, filter: "blur(2px)" }}
    transition={{ duration: 0.28, ease: [0.22, 0.61, 0.36, 1] }}
    style={{ willChange: "transform, opacity, filter" }}
  >
    {children}
  </Motion.div>
);

// Slight 3D flip for cards / views when they appear or disappear
export const CardFlip = ({ children }) => (
  <Motion.div
    initial={{ opacity: 0, rotateX: -6, y: 6, transformPerspective: 800 }}
    animate={{ opacity: 1, rotateX: 0, y: 0 }}
    exit={{ opacity: 0, rotateX: 6, y: -6 }}
    transition={{ duration: 0.32, ease: [0.22, 0.61, 0.36, 1] }}
    style={{ transformStyle: "preserve-3d", willChange: "transform, opacity" }}
  >
    {children}
  </Motion.div>
);

// HOC to wrap a component with a chosen animation variant
export function withTransition(Comp, Variant = SoftSlide) {
  // Allow passing a different animation wrapper if needed
  const VariantToUse = Variant;
  return function Wrapped(props) {
    return (
      // Add perspective so 3D transforms (e.g. CardFlip) look more natural
      <div className="min-h-screen" style={{ perspective: 1000 }}>
        <VariantToUse>
          <Comp {...props} />
        </VariantToUse>
      </div>
    );
  };
}

// Default export: convenient shortcut when you just want SoftSlide
export default withTransition;
