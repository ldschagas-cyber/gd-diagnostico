import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { getOportunidades, priorizarOportunidade } from "../api/oportunidades";
import Toast, { useToast } from "../components/Toast.jsx";
import "./OportunidadesPage.css";

const PRIORIDADE_LABEL = { alta: "Prioridade alta", media: "Prioridade média", baixa: "Prioridade baixa" };
const STATUS_LABEL = { pendente: "Pendente", andamento: "Em andamento", concluido: "Concluído" };

function formatMoeda(v) {
  return `R$ ${Math.round(v || 0).toLocaleString("pt-BR")}`;
}

export default function OportunidadesPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { msg, show, showToast } = useToast();

  const query = useQuery({ queryKey: ["portal-oportunidades"], queryFn: getOportunidades });

  const priorizar = useMutation({
    mutationFn: priorizarOportunidade,
    onSuccess: (data, id) => {
      queryClient.setQueryData(["portal-oportunidades"], (atual) =>
        (atual || []).map((o) => (o.id === id ? { ...o, priorizada_pelo_cliente: data.priorizada_pelo_cliente } : o)),
      );
      const item = query.data?.find((o) => o.id === id);
      showToast(
        data.priorizada_pelo_cliente
          ? `"${item?.titulo}" priorizada — a equipe GD Conecta será avisada.`
          : `"${item?.titulo}" removida das priorizadas.`,
      );
    },
  });

  const itens = query.data || [];
  const totalPotencial = itens.reduce((s, o) => s + (o.impacto_estimado || 0), 0);
  const priorizadas = itens.filter((o) => o.priorizada_pelo_cliente).length;

  return (
    <div className="page">
      <button className="back-link" onClick={() => navigate("/")}>
        <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 4L6 10l6 6" /></svg>
        Voltar ao Dashboard Executivo
      </button>

      <div className="page-head">
        <h1>Oportunidades Prioritárias</h1>
        <p>
          As iniciativas com maior impacto financeiro identificadas no seu diagnóstico, ordenadas por
          potencial de economia. Priorize as que quer acompanhar de perto — isso não altera o
          trabalho da equipe GD Conecta, só destaca o que importa para você.
        </p>
      </div>

      {query.isLoading && <p className="state-msg">Carregando oportunidades…</p>}
      {query.isError && <p className="state-msg error">Não foi possível carregar as oportunidades agora.</p>}

      {query.data && (
        <>
          <div className="totals-bar">
            <div className="totals-bar-stats">
              <div className="stat"><div className="t">Potencial identificado (período analisado)</div><div className="v">{formatMoeda(totalPotencial)}</div></div>
              <div className="stat"><div className="t">Oportunidades listadas</div><div className="v">{itens.length}</div></div>
            </div>
            <div className="stat"><div className="t">Priorizadas por você</div><div className="v">{priorizadas} de {itens.length}</div></div>
          </div>

          <div className="opp-list">
            {itens.map((o, i) => (
              <div className="opp-card" key={o.id}>
                <div className="opp-rank">{i + 1}</div>
                <div className="opp-main">
                  <div className="opp-title">{o.titulo}</div>
                  <div className="opp-desc">{o.descricao || "Sem descrição detalhada."}</div>
                  <div className="opp-tags">
                    <span className={`prio-pill ${o.prioridade}`}><span className="dot"></span>{PRIORIDADE_LABEL[o.prioridade]}</span>
                    <span className={`status-pill ${o.status}`}>{STATUS_LABEL[o.status]}</span>
                  </div>
                </div>
                <div className="opp-side">
                  <div className="opp-value">{formatMoeda(o.impacto_estimado)}<span>impacto estimado no período analisado</span></div>
                  <div className="opp-actions">
                    <button className="btn-ghost" onClick={() => showToast(`Detalhe de "${o.titulo}" ainda não foi prototipado.`)}>Ver detalhes</button>
                    <button
                      className={`btn-prioritize${o.priorizada_pelo_cliente ? " is-active" : ""}`}
                      disabled={priorizar.isPending && priorizar.variables === o.id}
                      onClick={() => priorizar.mutate(o.id)}
                    >
                      <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2"><path d="M10 3l2.1 4.3 4.7.7-3.4 3.3.8 4.7L10 14l-4.2 2 .8-4.7L3.2 8l4.7-.7L10 3z" /></svg>
                      {o.priorizada_pelo_cliente ? "Priorizada" : "Priorizar"}
                    </button>
                  </div>
                </div>
              </div>
            ))}
            {!itens.length && <p className="state-msg">Nenhuma oportunidade identificada ainda.</p>}
          </div>
        </>
      )}

      <Toast msg={msg} show={show} />
    </div>
  );
}
