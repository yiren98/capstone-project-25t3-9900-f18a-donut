// routes/Register.jsx
import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import RegisterForm from "../src/components/RegisterForm.jsx";

export default function RegisterPage() {
  const nav = useNavigate();

  useEffect(() => {
    fetch("/api/me", { credentials: "include" })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => { if (data?.user) nav("/Dashboard", { replace: true }); })
      .catch(() => {});
  }, [nav]);

  const handleSuccess = () => nav("/Dashboard", { replace: true });

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
      <div className="w-full max-w-md">
        <div className="bg-white shadow-xl rounded-2xl p-8">
          <h1 className="text-2xl font-semibold text-gray-900 mb-2">Register</h1>
          <p className="text-sm text-gray-500 mb-6">Auto sign-in after registering</p>
          <RegisterForm onSuccess={handleSuccess} />
          <p className="mt-6 text-center text-sm text-gray-600">
            Have an account?{" "}
            <a href="/login" className="text-indigo-600 hover:underline">Sign in</a>
          </p>
        </div>
        <p className="mt-6 text-center text-xs text-gray-400">
          © {new Date().getFullYear()} Culture Dashboard
        </p>
      </div>
    </div>
  );
}
