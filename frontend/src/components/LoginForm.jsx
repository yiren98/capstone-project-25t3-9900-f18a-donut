import { useState } from "react";

export default function LoginForm({ onSuccess }) {
  const [form, setForm] = useState({ email: "", password: "", remember: true });
  const [showPwd, setShowPwd] = useState(false);
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [serverMsg, setServerMsg] = useState("");

  const onChange = (e) => {
    const { name, type, checked, value } = e.target;
    setForm((s) => ({ ...s, [name]: type === "checkbox" ? checked : value }));
    setErrors((s) => ({ ...s, [name]: undefined }));
  };

  const validate = () => {
    const e = {};
    if (!form.email.trim()) e.email = "Please enter email";
    else if (!/^\S+@\S+\.\S+$/.test(form.email)) e.email = "Invalid email";
    if (!form.password) e.password = "Please enter password";
    return e;
  };

  const loginRequest = async () => {
    const res = await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: form.email, password: form.password, remember: form.remember }),
      credentials: "include", 
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data?.message || "Login failed");
    return data; 
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    const ve = validate();
    if (Object.keys(ve).length) return setErrors(ve);

    setSubmitting(true);
    setServerMsg("");
    try {
      const data = await loginRequest();

      if (data?.token) {
        localStorage.setItem("token", data.token);
      }
      setServerMsg("Login success");
      onSuccess?.(data);
    } catch (err) {
      setServerMsg(err.message || "Login failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={onSubmit} className="space-y-4">
      {serverMsg && (
        <div
          className={`rounded-lg px-3 py-2 text-sm ${
            serverMsg.includes("success")
              ? "bg-green-50 text-green-700 border border-green-200"
              : "bg-rose-50 text-rose-700 border border-rose-200"
          }`}
        >
          {serverMsg}
        </div>
      )}

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
        <input
          type="email"
          name="email"
          value={form.email}
          onChange={onChange}
          autoComplete="email"
          className={`w-full rounded-xl border px-3 py-2 outline-none focus:ring-2 focus:ring-indigo-500 ${
            errors.email ? "border-rose-300" : "border-gray-300"
          }`}
          placeholder="you@example.com"
        />
        {errors.email && <p className="mt-1 text-xs text-rose-600">{errors.email}</p>}
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
        <div
          className={`flex items-center rounded-xl border ${
            errors.password ? "border-rose-300" : "border-gray-300"
          }`}
        >
          <input
            type={showPwd ? "text" : "password"}
            name="password"
            value={form.password}
            onChange={onChange}
            autoComplete="current-password"
            className="w-full px-3 py-2 rounded-l-xl outline-none focus:ring-2 focus:ring-indigo-500"
            placeholder="••••••••"
          />
          <button
            type="button"
            onClick={() => setShowPwd((s) => !s)}
            className="px-3 text-sm text-gray-500 hover:text-gray-800"
          >
            {showPwd ? "Hide" : "Show"}
          </button>
        </div>
        {errors.password && <p className="mt-1 text-xs text-rose-600">{errors.password}</p>}
      </div>

      <div className="flex items-center justify-between">
        <label className="inline-flex items-center space-x-2 text-sm text-gray-600">
          <input
            type="checkbox"
            name="remember"
            checked={form.remember}
            onChange={onChange}
            className="rounded border-gray-300"
          />
          <span>Remember me</span>
        </label>
        <a href="#" className="text-sm text-indigo-600 hover:underline">
          Forgot password?
        </a>
      </div>

      <button
        type="submit"
        disabled={submitting}
        className="w-full rounded-xl bg-indigo-600 text-white py-2.5 font-medium hover:bg-indigo-700 disabled:opacity-60"
      >
        {submitting ? "Signing in…" : "Sign in"}
      </button>
    </form>
  );
}
