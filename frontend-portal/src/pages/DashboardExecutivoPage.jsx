import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import { getDashboard } from "../api/dashboard";
import Toast, { useToast } from "../components/Toast.jsx";
import "./DashboardExecutivoPage.css";

const NAV_ITENS = ["Diagnóstico", "Benchmark", "Inteligência", "Governança", "Relatórios"];
const DONUT_CORES = ["var(--seq-4)", "var(--seq-2)", "var(--amber)", "var(--ink-faint)", "var(--seq-1)", "var(--seq-3)"];
const REGIAO_CORES = ["var(--critical)", "var(--warning)", "var(--warning)", "var(--seq-3)", "var(--good)", "var(--good)"];

function formatMoeda(v) {
  return `R$ ${Math.round(v || 0).toLocaleString("pt-BR")}`;
}

function nomeRegiao(macroRegiao) {
  const nomes = { NORTE: "Norte", NORDESTE: "Nordeste", CENTRO_OESTE: "Centro-Oeste", SUDESTE: "Sudeste", SUL: "Sul" };
  return nomes[macroRegiao] || macroRegiao;
}

function mesLabel(mes) {
  const nomes = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"];
  const [, m] = (mes || "").split("-");
  const idx = parseInt(m, 10) - 1;
  return nomes[idx] ?? mes;
}

/** Gera os pontos do polyline (viewBox 420x160, área útil x:10-410 y:20-140). */
function pontosEvolucao(pontos, referencia) {
  if (!pontos.length) return { linha: "", ref: "", eixoX: [] };
  const valores = pontos.map((p) => p.custo_real_kg);
  const min = Math.min(...valores, referencia || Infinity);
  const max = Math.max(...valores, referencia || 0);
  const amplitude = max - min || 1;
  const passoX = pontos.length > 1 ? 400 / (pontos.length - 1) : 0;
  const y = (v) => 140 - ((v - min) / amplitude) * 120;
  const coords = pontos.map((p, i) => [10 + i * passoX, y(p.custo_real_kg)]);
  const linha = coords.map(([x, yy]) => `${x.toFixed(0)},${yy.toFixed(0)}`).join(" ");
  const yRef = y(referencia || 0).toFixed(0);
  const ref = `10,${yRef} 410,${yRef}`;
  return { linha, ref, coords, eixoX: pontos.map((p) => mesLabel(p.mes)) };
}

/** Segmentos do donut (viewBox 120x120, raio 46, circunferência ≈ 289). */
function segmentosDonut(itens) {
  const total = itens.reduce((s, i) => s + (i.valor || 0), 0) || 1;
  const CIRC = 2 * Math.PI * 46;
  let acumulado = 0;
  return itens.map((item, i) => {
    const fatia = (item.valor / total) * CIRC;
    const seg = { ...item, cor: DONUT_CORES[i % DONUT_CORES.length], dasharray: `${fatia.toFixed(1)} ${(CIRC - fatia).toFixed(1)}`, offset: -acumulado.toFixed(1) };
    acumulado += fatia;
    return seg;
  });
}

export default function DashboardExecutivoPage() {
  const { usuario, logout } = useAuth();
  const navigate = useNavigate();
  const { msg, show, showToast } = useToast();

  const query = useQuery({ queryKey: ["portal-dashboard"], queryFn: getDashboard });

  function irNaoDisponivel(nome) {
    showToast(`Seção "${nome}" ainda não foi prototipada nesta versão.`);
  }

  async function handleLogout() {
    await logout();
    navigate("/login");
  }

  const d = query.data;
  const evolucao = d ? pontosEvolucao(d.evolucao_frete, d.referencia_mercado_kg) : null;
  const donut = d ? segmentosDonut(d.potencial_economia.por_regiao) : [];
  const maxCusto = d ? Math.max(...d.custo_por_regiao.map((r) => r.custo_kg), 1) : 1;
  const maxBench = d ? Math.max(...d.benchmark_mercado.flatMap((r) => [r.valor_empresa_kg, r.valor_mercado_kg]), 1) : 1;

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="sb-brand">
          <div className="monogram">GD</div>
          <div><strong>GD Conecta</strong><span>Portal Executivo</span></div>
        </div>

        <nav className="sb-nav">
          <div className="sb-item active">
            <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6"><rect x="2.5" y="2.5" width="6.2" height="6.2" rx="1.3" /><rect x="11.3" y="2.5" width="6.2" height="4.4" rx="1.3" /><rect x="11.3" y="9.4" width="6.2" height="8.1" rx="1.3" /><rect x="2.5" y="11.2" width="6.2" height="6.3" rx="1.3" /></svg>
            Dashboard Executivo
          </div>
          {NAV_ITENS.map((nome) => (
            <button key={nome} className="sb-item" onClick={() => irNaoDisponivel(nome)}>
              <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6"><circle cx="10" cy="10" r="7" /></svg>
              {nome}
            </button>
          ))}
          <div className="sb-label" style={{ marginTop: 14 }}>Conta</div>
          <button className="sb-item" onClick={() => irNaoDisponivel("Minha Conta")}>
            <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6"><circle cx="10" cy="6.6" r="3.1" /><path d="M3.4 17c.6-3.4 3.2-5.4 6.6-5.4s6 2 6.6 5.4" /></svg>
            Minha Conta
          </button>
        </nav>

        <div className="sb-user">
          <div className="avatar">{(usuario?.nome || "?").slice(0, 2).toUpperCase()}</div>
          <div className="sb-user-meta">
            <strong>{usuario?.nome}</strong>
            <span>{usuario?.empresa_nome || "Cliente GD Conecta"}</span>
          </div>
          <button className="logout-btn" aria-label="Sair" title="Sair" onClick={handleLogout}>
            <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.7"><path d="M8 17.5H4.3a1 1 0 01-1-1v-13a1 1 0 011-1H8" /><path d="M12.8 14l4-4-4-4M16.6 10H7.5" /></svg>
          </button>
        </div>
      </aside>

      <div className="main-col">
        <header className="topbar">
          <div className="topbar-title">
            <h1>Olá, {usuario?.nome?.split(" ")[0] || ""}.</h1>
            <p>{d ? `Empresa: ${d.empresa_nome}` : "Carregando…"}</p>
          </div>
          <div className="topbar-actions">
            <button className="icon-btn" aria-label="Notificações" onClick={() => showToast("Central de notificações ainda não prototipada.")}>
              <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6"><path d="M5 8a5 5 0 0110 0c0 3.6 1.1 4.7 1.5 5.2H3.5C3.9 12.7 5 11.6 5 8z" /><path d="M8.3 16a1.8 1.8 0 003.4 0" /></svg>
            </button>
          </div>
        </header>

        <div className="content">
          {query.isLoading && <p className="state-msg">Carregando indicadores…</p>}
          {query.isError && <p className="state-msg error">Não foi possível carregar o dashboard agora.</p>}

          {d && (
            <>
              <section className="summary-card" aria-label="Resumo executivo">
                <div className="summary-head">
                  <h2>Situação Atual</h2>
                  <span>Resumo executivo</span>
                </div>
                <div className="summary-list">
                  {d.resumo.map((item) => (
                    <div className="summary-row" key={item.chave}>
                      <span className={`status-dot ${item.status}`}></span>
                      <span className="label">{item.titulo}</span>
                      <span className="value">{item.valor}</span>
                    </div>
                  ))}
                </div>
                <button className="btn-cta" onClick={() => navigate("/oportunidades")}>
                  Ver oportunidades prioritárias
                  <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2.2"><path d="M4 10h12M11 5l5 5-5 5" /></svg>
                </button>
              </section>

              <section className="kpi-row" aria-label="Indicadores principais">
                <div className="kpi-card"><div className="label">Economia Potencial</div><div className="value">{formatMoeda(d.kpis.economia_potencial_anual)}</div><div className="sub">estimativa anual</div></div>
                <div className="kpi-card"><div className="label">Aderência ao Mercado</div><div className="value">{d.kpis.aderencia_mercado_pct.toFixed(0)}%</div><div className="sub">vs. benchmark do setor</div></div>
                <div className="kpi-card"><div className="label">Performance Logística</div><div className="value">{d.kpis.performance_logistica.toFixed(0)} pontos</div><div className="sub">escala de 0 a 100</div></div>
                <div className="kpi-card"><div className="label">Rotas acima do benchmark</div><div className="value">{d.kpis.rotas_acima_benchmark}</div><div className="sub">regiões monitoradas</div></div>
                <div className="kpi-card"><div className="label">Transportadoras Monitoradas</div><div className="value">{d.kpis.transportadoras_monitoradas}</div><div className="sub">na malha atual</div></div>
              </section>

              <section className="charts-grid" aria-label="Indicadores e gráficos">
                <div className="card">
                  <div className="card-head"><div><h3>Evolução do Frete</h3><p>Custo real vs. referência de mercado</p></div></div>
                  <div className="card-body">
                    <div className="legend">
                      <span><i style={{ background: "var(--seq-4)" }}></i>Sua empresa</span>
                      <span><i style={{ background: "var(--ink-faint)" }}></i>Referência de mercado</span>
                    </div>
                    {evolucao?.coords?.length ? (
                      <svg viewBox="0 0 420 160" width="100%" height="160" role="img" aria-label="Gráfico de evolução do frete">
                        <line x1="0" y1="30" x2="420" y2="30" stroke="var(--border)" strokeWidth="1" />
                        <line x1="0" y1="80" x2="420" y2="80" stroke="var(--border)" strokeWidth="1" />
                        <line x1="0" y1="130" x2="420" y2="130" stroke="var(--border)" strokeWidth="1" />
                        <polyline points={evolucao.ref} fill="none" stroke="var(--ink-faint)" strokeWidth="2" strokeDasharray="4 4" />
                        <polyline points={evolucao.linha} fill="none" stroke="var(--seq-4)" strokeWidth="2.5" />
                        <g fill="var(--seq-4)">
                          {evolucao.coords.map(([x, y], i) => <circle key={i} cx={x} cy={y} r="3" />)}
                        </g>
                        <g fontFamily="var(--font-mono)" fontSize="9.5" fill="var(--ink-faint)">
                          {evolucao.coords.map(([x], i) => <text key={i} x={x - 8} y="152">{evolucao.eixoX[i]}</text>)}
                        </g>
                      </svg>
                    ) : <p className="state-msg">Sem dado de evolução mensal ainda.</p>}
                  </div>
                </div>

                <div className="card">
                  <div className="card-head"><div><h3>Benchmark Mercado</h3><p>Sua empresa vs. mercado, por macrorregião</p></div></div>
                  <div className="card-body">
                    <div className="legend">
                      <span><i style={{ background: "var(--seq-4)" }}></i>Sua empresa</span>
                      <span><i style={{ background: "var(--ink-faint)", opacity: 0.5 }}></i>Mercado</span>
                    </div>
                    {d.benchmark_mercado.map((r) => (
                      <div className="bench-row" key={r.regiao}>
                        <div className="bench-name">{nomeRegiao(r.regiao)}</div>
                        <div>
                          <div className="bench-track">
                            <div className="bench-fill market" style={{ width: `${(r.valor_mercado_kg / maxBench) * 100}%` }}></div>
                            <div className="bench-fill company" style={{ width: `${(r.valor_empresa_kg / maxBench) * 100}%` }}></div>
                          </div>
                          <div className="bench-label">Você {r.valor_empresa_kg.toFixed(2)} · mercado {r.valor_mercado_kg.toFixed(2)} (R$/kg, menor é melhor)</div>
                        </div>
                      </div>
                    ))}
                    {!d.benchmark_mercado.length && <p className="state-msg">Sem benchmark calculado ainda.</p>}
                  </div>
                </div>

                <div className="card">
                  <div className="card-head"><div><h3>Custo por Região</h3><p>Custo médio de frete por macrorregião</p></div></div>
                  <div className="card-body">
                    <div className="region-bars">
                      {d.custo_por_regiao.map((r, i) => (
                        <div className="region-row" key={r.regiao}>
                          <span className="region-uf">{nomeRegiao(r.regiao)}</span>
                          <div className="region-track"><div className="region-fill" style={{ width: `${(r.custo_kg / maxCusto) * 100}%`, background: REGIAO_CORES[i % REGIAO_CORES.length] }}></div></div>
                          <span className="region-val">R$ {r.custo_kg.toFixed(2)}/kg</span>
                        </div>
                      ))}
                      {!d.custo_por_regiao.length && <p className="state-msg">Sem dado regional ainda.</p>}
                    </div>
                  </div>
                </div>

                <div className="card">
                  <div className="card-head"><div><h3>Potencial de Economia</h3><p>{formatMoeda(d.potencial_economia.total_anual)}/ano · por macrorregião</p></div></div>
                  <div className="card-body">
                    {donut.length ? (
                      <div className="donut-wrap">
                        <svg viewBox="0 0 120 120" width="120" height="120" role="img" aria-label="Distribuição do potencial de economia">
                          <circle cx="60" cy="60" r="46" fill="none" stroke="var(--paper)" strokeWidth="16" />
                          {donut.map((seg) => (
                            <circle key={seg.regiao} cx="60" cy="60" r="46" fill="none" stroke={seg.cor} strokeWidth="16"
                              strokeDasharray={seg.dasharray} strokeDashoffset={seg.offset} transform="rotate(-90 60 60)" />
                          ))}
                          <text x="60" y="57" textAnchor="middle" fontSize="12" fontWeight="700" fill="var(--ink)">
                            {formatMoeda(d.potencial_economia.total_anual)}
                          </text>
                          <text x="60" y="71" textAnchor="middle" fontSize="8" fill="var(--ink-faint)">potencial/ano</text>
                        </svg>
                        <div className="donut-legend">
                          {donut.map((seg) => (
                            <div className="row" key={seg.regiao}>
                              <span className="lname"><i style={{ background: seg.cor }}></i>{nomeRegiao(seg.regiao)}</span>
                              <span className="lval">{formatMoeda(seg.valor)}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : <p className="state-msg">Sem oportunidade regional identificada ainda.</p>}
                  </div>
                </div>
              </section>

              <section className="card" aria-label="Plano de ação">
                <div className="card-head">
                  <div><h3>Plano de Ação</h3><p>{d.plano_acao_concluidas} de {d.plano_acao_total} ações concluídas</p></div>
                  <button style={{ all: "unset", cursor: "pointer", fontSize: "12.5px", fontWeight: 600, color: "var(--link)" }} onClick={() => irNaoDisponivel("Governança")}>
                    Ver todas as ações →
                  </button>
                </div>
                <div style={{ overflowX: "auto" }}>
                  <table className="plano">
                    <thead><tr><th>Ação</th><th>Categoria</th><th>Status</th></tr></thead>
                    <tbody>
                      {d.plano_acao.map((item) => (
                        <tr key={item.id}>
                          <td><div className="acao-title">{item.titulo}</div></td>
                          <td>{item.categoria}</td>
                          <td><span className={`status-pill ${item.status}`}>{{ pendente: "Pendente", andamento: "Em andamento", concluido: "Concluído" }[item.status]}</span></td>
                        </tr>
                      ))}
                      {!d.plano_acao.length && (
                        <tr><td colSpan={3} className="state-msg">Nenhuma ação registrada ainda.</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </section>
            </>
          )}
        </div>
      </div>

      <Toast msg={msg} show={show} />
    </div>
  );
}
