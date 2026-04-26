import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useLogin, useRegister } from "../hooks/useAuth";

export function AuthPage() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const login = useLogin();
  const register = useRegister();
  const navigate = useNavigate();

  function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    const onSuccess = () => navigate("/");
    const onError = (e: Error) => setErr(e.message);
    if (mode === "login") {
      login.mutate({ email, password }, { onSuccess, onError });
    } else {
      register.mutate({ email, password, display_name: name }, { onSuccess, onError });
    }
  }

  return (
    <form className="auth-card" onSubmit={submit}>
      <h2>{mode === "login" ? "Sign in" : "Create account"}</h2>
      {err && <div className="err">{err}</div>}
      {mode === "register" && (
        <input
          placeholder="Display name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
      )}
      <input
        type="email"
        placeholder="Email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        required
      />
      <input
        type="password"
        placeholder="Password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        required
        minLength={6}
      />
      <button type="submit">{mode === "login" ? "Sign in" : "Register"}</button>
      <p style={{ textAlign: "center", marginTop: 12 }}>
        <a
          href="#"
          onClick={(e) => {
            e.preventDefault();
            setMode(mode === "login" ? "register" : "login");
          }}
        >
          {mode === "login" ? "Need an account?" : "Already have an account?"}
        </a>
      </p>
    </form>
  );
}
