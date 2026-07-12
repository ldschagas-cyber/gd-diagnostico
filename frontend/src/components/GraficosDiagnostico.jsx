import { Card, CardContent, Typography, Grid, Box } from "@mui/material";
import {
  BarChart,
  Bar,
  ComposedChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as ReTooltip,
  ResponsiveContainer,
  Cell,
  PieChart,
  Pie,
  Legend,
  ReferenceLine,
  LabelList,
} from "recharts";
import { fmtMoeda, fmtNumero, fmtPct, fmtRsKg, rotuloMacro } from "../utils/format";
import { GD } from "../theme";

const CORES_PIZZA = [
  GD.indigo,
  GD.blue,
  "#4F8FC0",
  GD.ok,
  GD.amber,
  GD.warn,
  GD.danger,
  "#7E57C2",
];

// Abrevia o rótulo da transportadora (CNPJ + nome) para caber no eixo.
const abreviar = (nome, max = 22) =>
  nome && nome.length > max ? nome.slice(0, max) + "…" : nome || "—";

function Painel({ titulo, children, vazio, alturaMin = 320 }) {
  return (
    <Card sx={{ height: "100%" }}>
      <CardContent>
        <Typography variant="h6" sx={{ mb: 2 }}>
          {titulo}
        </Typography>
        {vazio ? (
          <Box sx={{ py: 6, textAlign: "center", color: "text.secondary" }}>
            <Typography variant="body2">Sem dados para o período.</Typography>
          </Box>
        ) : (
          <Box sx={{ width: "100%", minHeight: alturaMin }}>{children}</Box>
        )}
      </CardContent>
    </Card>
  );
}

export default function GraficosDiagnostico({ diag }) {
  const nac = diag?.nacional || {};
  const metaRsKg = nac.meta_rs_kg || 0;
  const metaPct = nac.meta_pct || 0;

  // ---- 1) Custo/kg × meta por macro-região (colunas + linha) ----
  const dadosRegiaoCusto = (diag?.regionais || []).map((r) => ({
    nome: rotuloMacro(r.macro_regiao),
    resultado: Number((r.frete_rs_kg || 0).toFixed(4)),
    meta: Number((r.meta_rs_kg || 0).toFixed(4)),
  }));

  // ---- 2) Frete por transportadora (barras horizontais ordenadas) ----
  const dadosFreteTransp = (diag?.transportadoras || [])
    .slice(0, 12)
    .map((t) => ({
      nome: abreviar(t.nome),
      nomeCompleto: t.nome,
      valor: Number((t.frete_total || 0).toFixed(2)),
      pct: Number((t.participacao_pct || 0).toFixed(1)),
    }));

  // ---- 3) Custo/kg por transportadora (barras + linha meta nacional) ----
  const dadosCustoTransp = [...(diag?.transportadoras || [])]
    .filter((t) => t.frete_rs_kg > 0)
    .sort((a, b) => b.frete_rs_kg - a.frete_rs_kg)
    .slice(0, 12)
    .map((t) => ({
      nome: abreviar(t.nome),
      nomeCompleto: t.nome,
      valor: Number((t.frete_rs_kg || 0).toFixed(2)),
      acima: metaRsKg > 0 && t.frete_rs_kg > metaRsKg,
    }));

  // ---- 4) % Frete/faturamento por transportadora (barras + linha meta) ----
  const dadosPctTransp = [...(diag?.transportadoras || [])]
    .filter((t) => t.frete_pct > 0)
    .sort((a, b) => b.frete_pct - a.frete_pct)
    .slice(0, 12)
    .map((t) => ({
      nome: abreviar(t.nome),
      nomeCompleto: t.nome,
      valor: Number((t.frete_pct || 0).toFixed(2)),
      acima: metaPct > 0 && t.frete_pct > metaPct,
    }));

  // ---- 5) % Frete/faturamento por região (colunas + linha meta) ----
  const dadosPctRegiao = (diag?.regionais || []).map((r) => ({
    nome: rotuloMacro(r.macro_regiao),
    resultado: Number((r.frete_pct || 0).toFixed(2)),
    meta: Number((r.meta_pct || 0).toFixed(2)),
  }));

  // ---- 5b/5c) Evolução mensal (Frete Total e % Frete) — MELHORIA v6.10 ----
  const fmtMesAno = (aaaaMm) => {
    const [ano, mes] = String(aaaaMm || "").split("-");
    return ano && mes ? `${mes}/${ano.slice(2)}` : aaaaMm;
  };
  const dadosEvolucao = (diag?.evolucao_frete || []).map((e) => ({
    mes: fmtMesAno(e.mes),
    frete_total: Number((e.frete_total || 0).toFixed(2)),
    frete_pct: Number((e.frete_pct || 0).toFixed(2)),
  }));

  // ---- 6) Composição do frete (pizza) ----
  const dadosComposicao = Object.entries(diag?.composicao_frete || {})
    .map(([nome, valor]) => ({ nome, valor: Number(valor) }))
    .sort((a, b) => b.valor - a.valor);
  const totalComp = dadosComposicao.reduce((s, d) => s + d.valor, 0) || 1;

  // Altura dinâmica para barras horizontais (≈34px por barra).
  const alturaBarras = (n) => Math.max(260, n * 34 + 40);

  // ---- Composição do frete: rótulo, tooltip e legenda customizados ----
  // Rótulo interno apenas nas fatias >= 3% — evita a sobreposição dos textos
  // das fatias minúsculas (GRIS, Pedágio, Despacho, Ademe...). Os valores de
  // TODAS as categorias continuam visíveis na legenda e no tooltip.
  const LIMITE_ROTULO = 0.03;
  const renderRotuloFatia = ({
    cx, cy, midAngle, innerRadius, outerRadius, percent,
  }) => {
    if (percent < LIMITE_ROTULO) return null;
    const RAD = Math.PI / 180;
    const r = innerRadius + (outerRadius - innerRadius) * 0.6;
    const x = cx + r * Math.cos(-midAngle * RAD);
    const y = cy + r * Math.sin(-midAngle * RAD);
    return (
      <text
        x={x}
        y={y}
        fill="#fff"
        fontSize={12}
        fontWeight={600}
        textAnchor="middle"
        dominantBaseline="central"
      >
        {fmtPct(percent * 100, 1)}
      </text>
    );
  };

  // Tooltip: categoria + valor total (R$) + percentual.
  const TooltipComposicao = ({ active, payload }) => {
    if (!active || !payload || !payload.length) return null;
    const d = payload[0];
    const pct = (d.value / totalComp) * 100;
    return (
      <Box
        sx={{
          bgcolor: "#fff",
          border: "1px solid",
          borderColor: "divider",
          borderRadius: 1,
          px: 1.5,
          py: 1,
          boxShadow: 3,
        }}
      >
        <Typography variant="body2" sx={{ fontWeight: 700 }}>
          {d.name}
        </Typography>
        <Typography variant="body2" sx={{ fontVariantNumeric: "tabular-nums" }}>
          {fmtMoeda(d.value)}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {fmtPct(pct, 1)}
        </Typography>
      </Box>
    );
  };

  // Legenda: cor + nome + percentual (alinhado à direita, uma casa decimal).
  const LegendaComposicao = () => (
    <Box sx={{ mt: 1.5, px: 0.5 }}>
      {dadosComposicao.map((d, i) => (
        <Box
          key={d.nome}
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            py: 0.35,
          }}
        >
          <Box sx={{ display: "flex", alignItems: "center", gap: 1, minWidth: 0 }}>
            <Box
              sx={{
                width: 11,
                height: 11,
                borderRadius: "2px",
                flexShrink: 0,
                bgcolor: CORES_PIZZA[i % CORES_PIZZA.length],
              }}
            />
            <Typography variant="body2" noWrap title={d.nome}>
              {d.nome}
            </Typography>
          </Box>
          <Typography
            variant="body2"
            sx={{ fontWeight: 600, ml: 1, fontVariantNumeric: "tabular-nums" }}
          >
            {fmtPct((d.valor / totalComp) * 100, 1)}
          </Typography>
        </Box>
      ))}
    </Box>
  );

  return (
    <>
      {/* Evolução mensal — Valor de Frete e % Frete (MELHORIA v6.10) */}
      <Grid container spacing={2.5} sx={{ mt: 0.5 }}>
        <Grid item xs={12} md={6}>
          <Painel titulo="Evolução do Valor de Frete" vazio={!dadosEvolucao.length} alturaMin={280}>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={dadosEvolucao} margin={{ top: 24 }}>
                <XAxis dataKey="mes" tick={{ fontSize: 12 }} axisLine={false} tickLine={false} />
                <ReTooltip formatter={(v) => fmtMoeda(v)} contentStyle={{ borderRadius: 8 }} />
                <Bar dataKey="frete_total" fill={GD.blue} radius={[6, 6, 0, 0]} barSize={38}>
                  <LabelList
                    dataKey="frete_total"
                    position="top"
                    formatter={(v) => fmtMoeda(v)}
                    style={{ fontSize: 12, fontWeight: 700, fill: GD.ink }}
                  />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Painel>
        </Grid>
        <Grid item xs={12} md={6}>
          <Painel titulo="Evolução do % Frete" vazio={!dadosEvolucao.length} alturaMin={280}>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={dadosEvolucao} margin={{ top: 24 }}>
                <XAxis dataKey="mes" tick={{ fontSize: 12 }} axisLine={false} tickLine={false} />
                <ReTooltip formatter={(v) => fmtPct(v)} contentStyle={{ borderRadius: 8 }} />
                <Bar dataKey="frete_pct" fill={GD.amberDark} radius={[6, 6, 0, 0]} barSize={38}>
                  <LabelList
                    dataKey="frete_pct"
                    position="top"
                    formatter={(v) => fmtPct(v, 1)}
                    style={{ fontSize: 12, fontWeight: 700, fill: GD.ink }}
                  />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Painel>
        </Grid>
      </Grid>

      {/* Frete por Kg Regional e % Frete / Valor Mercadoria Regional — lado a
          lado, tamanho reduzido (MELHORIA v6.10 — antes eram 2 painéis de
          largura total, empilhados) */}
      <Grid container spacing={2.5} sx={{ mt: 0.5 }}>
        <Grid item xs={12} md={6}>
          <Painel
            titulo="Frete por Kg Regional"
            vazio={!dadosRegiaoCusto.length}
            alturaMin={260}
          >
            <ResponsiveContainer width="100%" height={260}>
              <ComposedChart data={dadosRegiaoCusto}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eee" />
                <XAxis dataKey="nome" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `R$ ${v}`} />
                <ReTooltip
                  formatter={(v, n) => [fmtRsKg(v), n === "resultado" ? "Frete" : "Meta"]}
                  contentStyle={{ borderRadius: 8 }}
                />
                <Legend
                  formatter={(v) => (v === "resultado" ? "Frete (R$/kg)" : "Meta (R$/kg)")}
                />
                <Bar dataKey="resultado" fill={GD.blue} radius={[4, 4, 0, 0]} barSize={32} />
                <Line
                  type="monotone"
                  dataKey="meta"
                  stroke={GD.amber}
                  strokeWidth={3}
                  dot={{ r: 4, fill: GD.amber }}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </Painel>
        </Grid>
        <Grid item xs={12} md={6}>
          <Painel
            titulo="% Frete / Valor Mercadoria Regional"
            vazio={!dadosPctRegiao.length}
            alturaMin={260}
          >
            <ResponsiveContainer width="100%" height={260}>
              <ComposedChart data={dadosPctRegiao}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eee" />
                <XAxis dataKey="nome" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `${v}%`} />
                <ReTooltip
                  formatter={(v, n) => [fmtPct(v), n === "resultado" ? "Frete" : "Meta"]}
                  contentStyle={{ borderRadius: 8 }}
                />
                <Legend
                  formatter={(v) => (v === "resultado" ? "Frete (%)" : "Meta (%)")}
                />
                <Bar dataKey="resultado" fill={GD.blue} radius={[4, 4, 0, 0]} barSize={32} />
                <Line
                  type="monotone"
                  dataKey="meta"
                  stroke={GD.amber}
                  strokeWidth={3}
                  dot={{ r: 4, fill: GD.amber }}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </Painel>
        </Grid>
      </Grid>

      {/* Composição do frete (pizza): removida do mock — desabilitada. */}
      {false && (
      <Grid container spacing={2.5} sx={{ mt: 0.5 }}>
        <Grid item xs={12} md={5}>
          <Painel titulo="Composição do frete" vazio={!dadosComposicao.length}>
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={dadosComposicao}
                  dataKey="valor"
                  nameKey="nome"
                  cx="50%"
                  cy="50%"
                  outerRadius={90}
                  minAngle={2}
                  paddingAngle={1}
                  label={renderRotuloFatia}
                  labelLine={false}
                  isAnimationActive={false}
                >
                  {dadosComposicao.map((_, i) => (
                    <Cell
                      key={i}
                      fill={CORES_PIZZA[i % CORES_PIZZA.length]}
                      stroke="#fff"
                      strokeWidth={1.5}
                    />
                  ))}
                </Pie>
                <ReTooltip content={<TooltipComposicao />} />
              </PieChart>
            </ResponsiveContainer>
            <LegendaComposicao />
          </Painel>
        </Grid>
      </Grid>
      )}

      {/* Linha 2 (removida do mock — desabilitada): frete por transportadora */}
      {false && (
      <Box sx={{ mt: 2.5 }}>
        <Painel
          titulo="Frete por transportadora"
          vazio={!dadosFreteTransp.length}
          alturaMin={alturaBarras(dadosFreteTransp.length)}
        >
          <ResponsiveContainer width="100%" height={alturaBarras(dadosFreteTransp.length)}>
            <BarChart
              data={dadosFreteTransp}
              layout="vertical"
              margin={{ left: 20, right: 70 }}
            >
              <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#eee" />
              <XAxis type="number" tick={{ fontSize: 11 }} tickFormatter={(v) => fmtMoeda(v)} />
              <YAxis
                type="category"
                dataKey="nome"
                width={160}
                tick={{ fontSize: 11 }}
                interval={0}
              />
              <ReTooltip
                formatter={(v) => fmtMoeda(v)}
                labelFormatter={(l, p) => p?.[0]?.payload?.nomeCompleto || l}
                contentStyle={{ borderRadius: 8 }}
              />
              <Bar dataKey="valor" fill={GD.indigo} radius={[0, 4, 4, 0]}>
                <LabelList
                  dataKey="pct"
                  position="right"
                  formatter={(v) => `${v}%`}
                  style={{ fontSize: 11, fill: GD.slate }}
                />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Painel>
      </Box>
      )}

      {/* Linha 3 (removida do mock — desabilitada): custo/kg e % frete por transportadora */}
      {false && (
      <Grid container spacing={2.5} sx={{ mt: 0.5 }}>
        <Grid item xs={12} md={6}>
          <Painel
            titulo="Custo/kg por transportadora"
            vazio={!dadosCustoTransp.length}
            alturaMin={alturaBarras(dadosCustoTransp.length)}
          >
            <ResponsiveContainer width="100%" height={alturaBarras(dadosCustoTransp.length)}>
              <BarChart
                data={dadosCustoTransp}
                layout="vertical"
                margin={{ left: 20, right: 60 }}
              >
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#eee" />
                <XAxis type="number" tick={{ fontSize: 11 }} />
                <YAxis
                  type="category"
                  dataKey="nome"
                  width={150}
                  tick={{ fontSize: 10 }}
                  interval={0}
                />
                <ReTooltip
                  formatter={(v) => fmtRsKg(v)}
                  labelFormatter={(l, p) => p?.[0]?.payload?.nomeCompleto || l}
                  contentStyle={{ borderRadius: 8 }}
                />
                {metaRsKg > 0 && (
                  <ReferenceLine
                    x={metaRsKg}
                    stroke={GD.amberDark}
                    strokeDasharray="5 4"
                    strokeWidth={2}
                    label={{
                      value: `meta ${fmtNumero(metaRsKg, 2)}`,
                      position: "top",
                      fontSize: 10,
                      fill: GD.amberDark,
                    }}
                  />
                )}
                <Bar dataKey="valor" radius={[0, 4, 4, 0]}>
                  {dadosCustoTransp.map((d, i) => (
                    <Cell key={i} fill={d.acima ? GD.danger : GD.blue} />
                  ))}
                  <LabelList
                    dataKey="valor"
                    position="right"
                    formatter={(v) => fmtNumero(v, 2)}
                    style={{ fontSize: 10 }}
                  />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Painel>
        </Grid>

        <Grid item xs={12} md={6}>
          <Painel
            titulo="% Frete/faturamento por transportadora"
            vazio={!dadosPctTransp.length}
            alturaMin={alturaBarras(dadosPctTransp.length)}
          >
            <ResponsiveContainer width="100%" height={alturaBarras(dadosPctTransp.length)}>
              <BarChart
                data={dadosPctTransp}
                layout="vertical"
                margin={{ left: 20, right: 60 }}
              >
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#eee" />
                <XAxis
                  type="number"
                  tick={{ fontSize: 11 }}
                  tickFormatter={(v) => `${v}%`}
                />
                <YAxis
                  type="category"
                  dataKey="nome"
                  width={150}
                  tick={{ fontSize: 10 }}
                  interval={0}
                />
                <ReTooltip
                  formatter={(v) => fmtPct(v)}
                  labelFormatter={(l, p) => p?.[0]?.payload?.nomeCompleto || l}
                  contentStyle={{ borderRadius: 8 }}
                />
                {metaPct > 0 && (
                  <ReferenceLine
                    x={metaPct}
                    stroke={GD.amberDark}
                    strokeDasharray="5 4"
                    strokeWidth={2}
                    label={{
                      value: `meta ${fmtNumero(metaPct, 1)}%`,
                      position: "top",
                      fontSize: 10,
                      fill: GD.amberDark,
                    }}
                  />
                )}
                <Bar dataKey="valor" radius={[0, 4, 4, 0]}>
                  {dadosPctTransp.map((d, i) => (
                    <Cell key={i} fill={d.acima ? GD.danger : GD.ok} />
                  ))}
                  <LabelList
                    dataKey="valor"
                    position="right"
                    formatter={(v) => `${fmtNumero(v, 1)}%`}
                    style={{ fontSize: 10 }}
                  />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Painel>
        </Grid>
      </Grid>
      )}
    </>
  );
}
