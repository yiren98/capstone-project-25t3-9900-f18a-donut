import LoginForm from "../src/components/LoginForm.jsx";
import { useNavigate } from "react-router-dom";
import { useEffect } from "react";

export default function LoginPage() {
  const nav = useNavigate();

  useEffect(() => {
  // pre check current login status
  fetch("/api/me", { credentials: "include" })
    .then((r) => (r.ok ? r.json() : null))
    .then((data) => {
        if (data?.user) nav("/Dashboard", { replace: true });
    })
    .catch(() => {});
  }, [nav]);

  const handleSuccess = () => nav("/Dashboard", { replace: true });

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
      <div className="w-full max-w-md">
        <div className="bg-white shadow-xl rounded-2xl p-8">
          <h1 className="text-2xl font-semibold text-gray-900 mb-2">Login</h1>
          <p className="text-sm text-gray-500 mb-6">
            Please sign in with your email and password
          </p>
          <LoginForm onSuccess={handleSuccess} />
          <p className="mt-6 text-center text-sm text-gray-600">
            No account?{" "}
            <a href="/register" className="text-indigo-600 hover:underline">
                Sign up
            </a>
          </p>
        </div>
        <p className="mt-6 text-center text-xs text-gray-400">
          © {new Date().getFullYear()} Culture Dashboard
        </p>
      </div>
    </div>
  );
}
