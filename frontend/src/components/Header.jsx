import { useEffect, useState } from "react";

export default function Header({ title = "Corporate Culture Monitor", subtitle = "Sprint 1" }) {
  const [elevated, setElevated] = useState(false);

  useEffect(() => {
    const onScroll = () => setElevated(window.scrollY > 4);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={[
        "sticky top-0 z-50",
        "backdrop-blur supports-[backdrop-filter]:bg-white/70 bg-white/95",
        "border-b border-black/5",
        elevated ? "shadow-sm" : "shadow-none",
      ].join(" ")}
    >
      <div className="mx-auto max-w-6xl px-5 md:px-8 py-4">
        <h1 className="font-display text-5xl font-semibold tracking-tight">
             Corporate Culture Monitor
        </h1>
        <p className="font-body text-gray-500 mt-1">Sprint 1</p>
      </div>
    </header>
  );
}
