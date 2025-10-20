// src/components/RegisterForm.jsx
import { useState } from "react";

export default function RegisterForm({ onSuccess }) {
  const [form, setForm] = useState({ email: "", name: "", password: "", confirmPassword: "" });
  const [showPwd, setShowPwd] = useState(false);
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [serverMsg, setServerMsg] = useState("");

  const onChange = (e) => {
    const { name, value } = e.target;
    setForm((s) => ({ ...s, [name]: value }));
    setErrors((s) => ({ ...s, [name]: undefined }));
  };

  const validate = () => {
    const e = {};
    const email = form.email.trim();
    if (!email) e.email = "Please enter email";
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) e.email = "Invalid email";

    if (!form.password) e.password = "Please enter password";
    else if (form.password.length < 6) e.password = "Min length 6";

    if (!form.confirmPassword) e.confirmPassword = "Confirm password";
    else if (form.password !== form.confirmPassword) e.confirmPassword = "Passwords do not match";
    return e;
  };

  const registerRequest = async () => {
    const res = await fetch("/api/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({
        email: form.email.trim().toLowerCase(),
        password: form.password,
        name: form.name.trim() || undefined,
      }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data?.message || "Register failed");
    return data;
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    const ve = validate();
    if (Object.keys(ve).length) return setErrors(ve);

    setSubmitting(true);
    setServerMsg("");
    try {
      const data = await registerRequest();
      setServerMsg("Register success");
      onSuccess?.(data);
    } catch (err) {
      setServerMsg(err.message || "Register failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={onSubmit} className="space-y-4">
      {serverMsg && (
        <div className={`rounded-lg px-3 py-2 text-sm ${
          serverMsg.includes("success") ? "bg-green-50 text-green-700 border border-green-200"
                                        : "bg-rose-50 text-rose-700 border border-rose-200"
        }`}>
          {serverMsg}
        </div>
      )}

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
        <input
          type="email" name="email" value={form.email} onChange={onChange} autoComplete="email"
          className={`w-full rounded-xl border px-3 py-2 outline-none focus:ring-2 focus:ring-indigo-500 ${
            errors.email ? "border-rose-300" : "border-gray-300"
          }`} placeholder="you@example.com"
        />
        {errors.email && <p className="mt-1 text-xs text-rose-600">{errors.email}</p>}
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
        <input
          type="text" name="name" value={form.name} onChange={onChange} autoComplete="name"
          className="w-full rounded-xl border px-3 py-2 outline-none focus:ring-2 focus:ring-indigo-500 border-gray-300"
          placeholder="Your display name"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
        <div className={`flex items-center rounded-xl border ${errors.password ? "border-rose-300" : "border-gray-300"}`}>
          <input
            type={showPwd ? "text" : "password"} name="password" value={form.password} onChange={onChange}
            autoComplete="new-password" className="w-full px-3 py-2 rounded-l-xl outline-none focus:ring-2 focus:ring-indigo-500"
            placeholder="••••••••"
          />
          <button type="button" onClick={() => setShowPwd((s) => !s)} className="px-3 text-sm text-gray-500 hover:text-gray-800">
            {showPwd ? "Hide" : "Show"}
          </button>
        </div>
        {errors.password && <p className="mt-1 text-xs text-rose-600">{errors.password}</p>}
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Confirm</label>
        <input
          type={showPwd ? "text" : "password"} name="confirmPassword" value={form.confirmPassword} onChange={onChange}
          autoComplete="new-password" className={`w-full rounded-xl border px-3 py-2 outline-none focus:ring-2 focus:ring-indigo-500 ${
            errors.confirmPassword ? "border-rose-300" : "border-gray-300"
          }`} placeholder="••••••••"
        />
        {errors.confirmPassword && <p className="mt-1 text-xs text-rose-600">{errors.confirmPassword}</p>}
      </div>

      <button type="submit" disabled={submitting}
        className="w-full rounded-xl bg-indigo-600 text-white py-2.5 font-medium hover:bg-indigo-700 disabled:opacity-60">
        {submitting ? "Registering…" : "Sign up"}
      </button>
    </form>
  );
}
