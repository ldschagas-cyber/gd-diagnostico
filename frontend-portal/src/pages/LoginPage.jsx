import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import NetworkCanvas from "../components/NetworkCanvas.jsx";
import Toast, { useToast } from "../components/Toast.jsx";
import "./LoginPage.css";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { msg, show, showToast } = useToast();

  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [mostrarSenha, setMostrarSenha] = useState(false);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    setErro("");
    if (!email || !senha) {
      setErro("Preencha e-mail e senha para continuar.");
      return;
    }
    setCarregando(true);
    try {
      await login(email, senha);
      navigate(location.state?.from?.pathname || "/", { replace: true });
    } catch {
      setErro("E-mail ou senha inválidos.");
    } finally {
      setCarregando(false);
    }
  }

  return (
    <div className="screen">
      <main className="access">
        <div className="wordmark">
          <div className="monogram">GD</div>
          <div className="wordmark-text">
            <strong>GD Conecta</strong>
            <span>Portal Executivo</span>
          </div>
        </div>

        <div className="access-mid">
          <p className="kicker">Inteligência Logística</p>
          <h1>Portal Executivo</h1>
          <p className="lede">Acesse os diagnósticos, indicadores, benchmarks de mercado e planos de ação da sua empresa.</p>

          {erro && (
            <div className="alert error show" role="alert">
              <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.7"><circle cx="10" cy="10" r="8" /><path d="M10 6.5v4.2M10 13.4h.01" /></svg>
              <span>{erro}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} noValidate>
            <div className="field">
              <label htmlFor="email">E-mail</label>
              <div className="field-control">
                <input
                  type="email" id="email" autoComplete="username" placeholder="voce@suaempresa.com.br"
                  value={email} onChange={(e) => setEmail(e.target.value)}
                  aria-invalid={erro && !email ? "true" : undefined}
                />
              </div>
            </div>
            <div className="field">
              <label htmlFor="password">Senha</label>
              <div className="field-control has-toggle">
                <input
                  type={mostrarSenha ? "text" : "password"} id="password" autoComplete="current-password"
                  placeholder="••••••••" value={senha} onChange={(e) => setSenha(e.target.value)}
                  aria-invalid={erro && !senha ? "true" : undefined}
                />
                <button
                  type="button" className="toggle-visibility" aria-pressed={mostrarSenha}
                  aria-label={mostrarSenha ? "Ocultar senha" : "Mostrar senha"}
                  onClick={() => setMostrarSenha((v) => !v)}
                >
                  {mostrarSenha ? (
                    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6"><path d="M2.5 2.5l15 15M8.3 8.4a2.6 2.6 0 003.4 3.4M6 5.2C3.3 6.6 1.5 10 1.5 10s3 5.5 8.5 5.5c1.4 0 2.7-.35 3.8-.9M12.2 5.1c-.7-.2-1.4-.3-2.2-.3-1 0-1.9.16-2.7.45" /><path d="M15.6 6.9c1.5 1.2 2.9 3.1 2.9 3.1s-.7 1.28-2 2.6" /></svg>
                  ) : (
                    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6"><path d="M1.5 10S4.5 4.5 10 4.5 18.5 10 18.5 10 15.5 15.5 10 15.5 1.5 10 1.5 10Z" /><circle cx="10" cy="10" r="2.6" /></svg>
                  )}
                </button>
              </div>
            </div>
            <div className="row-between">
              <label className="remember"><input type="checkbox" /> Manter conectado</label>
              <button type="button" className="forgot" onClick={() => showToast("Recuperação por e-mail ainda não está disponível nesta versão.")}>
                Esqueci minha senha
              </button>
            </div>
            <button type="submit" className={`submit${carregando ? " is-loading" : ""}`} disabled={carregando}>
              <span className="spinner" aria-hidden="true"></span>
              <span className="submit-label">Entrar</span>
            </button>
          </form>
        </div>

        <div className="access-foot">
          <span>© GD Conecta</span>
          <span>Portal do Cliente · v6.18.0</span>
        </div>
      </main>

      <aside className="stage">
        <NetworkCanvas />

        <div className="stage-top">
          <div className="env-pill">Rede de operação monitorada</div>
        </div>

        <div className="stage-mid">
          <h2>Transformamos dados de frete em decisões estratégicas.</h2>
          <div className="pill-row">
            <span className="pill"><span className="pill-dot"></span>Diagnóstico</span>
            <span className="pill"><span className="pill-dot"></span>Benchmark</span>
            <span className="pill"><span className="pill-dot"></span>Inteligência</span>
            <span className="pill"><span className="pill-dot"></span>Governança</span>
          </div>
        </div>

        {/* Cards ilustrativos — chrome de marca, não são dado real de nenhuma
            empresa (o dado real só aparece após login, no Dashboard). */}
        <div className="float-card fc1"><div className="t">Economia potencial</div><div className="v">R$ 842 mil</div></div>
        <div className="float-card fc2"><div className="t">Aderência ao mercado</div><div className="v">81%</div></div>
        <div className="float-card fc3"><div className="t">Rotas acima do benchmark</div><div className="v">18</div></div>

        <div className="stage-bottom">
          <span>GD Conecta © 2026</span>
          <span>Malha de centros de distribuição · ilustrativo</span>
        </div>
      </aside>

      <Toast msg={msg} show={show} />
    </div>
  );
}
