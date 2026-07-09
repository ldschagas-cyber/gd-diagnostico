import { Chip } from "@mui/material";

const STATUS_CONFIG = {
  RASCUNHO:    { label: "Rascunho",        color: "default" },
  ABERTO:      { label: "Aberto",           color: "info" },
  EM_COTACAO:  { label: "Em Cotação",       color: "warning" },
  ENCERRADO:   { label: "Encerrado",        color: "success" },
  CANCELADO:   { label: "Cancelado",        color: "error" },
};

export const TRANSP_STATUS_CONFIG = {
  CONVIDADA:         { label: "Convidada",          color: "default" },
  PARTICIPANDO:      { label: "Participando",        color: "info" },
  PROPOSTA_RECEBIDA: { label: "Proposta Recebida",   color: "success" },
  DESISTIU:          { label: "Desistiu",            color: "error" },
  DESCLASSIFICADA:   { label: "Desclassificada",     color: "error" },
  VENCEDORA:         { label: "Vencedora",           color: "success" },
};

export const SCORE_COLOR = (s) => {
  if (s >= 80) return "success";
  if (s >= 65) return "info";
  if (s >= 50) return "warning";
  return "error";
};

export default function BidStatusChip({ status, size = "small" }) {
  const cfg = STATUS_CONFIG[status] || { label: status, color: "default" };
  return <Chip size={size} label={cfg.label} color={cfg.color} />;
}
