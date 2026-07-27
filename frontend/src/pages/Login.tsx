import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { NovaMark, Wordmark } from "../components/brand/NovaMark";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await login(email, password);
      navigate("/");
    } catch {
      setError("Incorrect email or password.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell title="Sign in" subtitle="Welcome back to your observatory.">
      <form onSubmit={onSubmit} className="space-y-4">
        <Field label="Email" type="email" value={email} onChange={setEmail} />
        <Field
          label="Password"
          type="password"
          value={password}
          onChange={setPassword}
        />
        {error && <p className="text-sm text-nova-700">{error}</p>}
        <button type="submit" disabled={busy} className="btn-nova w-full disabled:opacity-60">
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>
      <p className="mt-6 text-center text-sm text-slate-500">
        No account?{" "}
        <Link to="/register" className="font-medium text-nova-600 hover:underline">
          Create one
        </Link>
      </p>
    </AuthShell>
  );
}

export function AuthShell({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: React.ReactNode;
}) {
  return (
    <div className="grid min-h-screen lg:grid-cols-[1.05fr_1fr]">
      {/* Observatory panel */}
      <aside className="nebula relative hidden overflow-hidden p-10 text-white lg:flex lg:flex-col lg:justify-between">
        <div className="starfield absolute inset-0 opacity-70" />
        <div className="relative flex items-center gap-2">
          <NovaMark size={26} animate />
          <span className="font-display text-lg font-bold">
            Data<span className="text-spark">Nova</span>
          </span>
        </div>

        <div className="relative max-w-md">
          <p className="eyebrow text-nova-200">Analytics observatory</p>
          <h2 className="mt-3 font-display text-[2.6rem] font-bold leading-[1.05]">
            Turn raw data into a burst of insight.
          </h2>
          <p className="mt-4 text-sm leading-relaxed text-white/70">
            Upload a dataset or connect a database — then profile, model, explain,
            and chat with your data, all in one console.
          </p>
        </div>

        <div className="relative grid grid-cols-3 gap-4 font-mono text-[11px] uppercase tracking-wider text-white/50">
          {[
            ["7", "analysis tabs"],
            ["SHAP", "explainable AI"],
            ["NL→SQL", "ask anything"],
          ].map(([big, small]) => (
            <div key={small}>
              <div className="font-display text-2xl font-bold tracking-normal text-white">
                {big}
              </div>
              {small}
            </div>
          ))}
        </div>
      </aside>

      {/* Form */}
      <main className="flex items-center justify-center bg-paper px-6 py-12">
        <div className="w-full max-w-sm animate-fade-up">
          <div className="mb-10 lg:hidden">
            <Wordmark />
          </div>
          <p className="eyebrow">Access</p>
          <h1 className="mt-2 font-display text-3xl font-bold text-ink">{title}</h1>
          <p className="mt-1 text-sm text-slate-500">{subtitle}</p>
          <div className="mt-8">{children}</div>
        </div>
      </main>
    </div>
  );
}

export function Field({
  label,
  type,
  value,
  onChange,
}: {
  label: string;
  type: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <label className="block">
      <span className="text-sm font-medium text-slate-700">{label}</span>
      <input
        type={type}
        required
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="input mt-1.5"
      />
    </label>
  );
}
