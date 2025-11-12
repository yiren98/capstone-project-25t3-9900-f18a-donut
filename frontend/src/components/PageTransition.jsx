/* eslint-disable react-refresh/only-export-components */
import { motion as Motion } from "framer-motion";

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

export function withTransition(Comp, Variant = SoftSlide) {
  const VariantToUse = Variant; 
  return function Wrapped(props) {
    return (
      <div className="min-h-screen" style={{ perspective: 1000 }}>
        <VariantToUse>
          <Comp {...props} />
        </VariantToUse>
      </div>
    );
  };
}

export default withTransition;
