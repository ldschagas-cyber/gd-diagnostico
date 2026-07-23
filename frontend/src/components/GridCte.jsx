import { useEffect, useState, useCallback } from "react";
import { Box, Card, CardContent, Typography, Stack, Chip, Button } from "@mui/material";
import ViewListIcon from "@mui/icons-material/ViewList";
import DeleteForeverIcon from "@mui/icons-material/DeleteForever";
import Tabela from "./Tabela";
import ConfirmDialog from "./ConfirmDialog";
import { importacaoApi } from "../api/endpoints";
import { extrairErro } from "../api/client";
import { useFeedback } from "./Feedback";
import { useAuth } from "../contexts/AuthContext";
import { useEmpresa } from "../contexts/EmpresaContext";
import { ehAdmin } from "../utils/permissoes";
import { GD } from "../theme";

function maskChave(chave) {
  return chave && chave.length > 12 ? `…${chave.slice(-12)}` : chave || "—";
}

const COLUNAS = [
  {
    field: "chave", headerName: "Chave", width: 150,
    renderCell: (p) => (
      <span style={{ fontFamily: "monospace", fontSize: 12 }}>{maskChave(p.value)}</span>
    ),
  },
  { field: "numero", headerName: "Nº CT-e", width: 90 },
  { field: "data_emissao", headerName: "Emissão", width: 100 },
  { field: "transportadora_nome", headerName: "Transportadora", flex: 1, minWidth: 160 },
  {
    field: "trajeto", headerName: "Origem → Destino", flex: 1, minWidth: 180,
    valueGetter: (_v, row) =>
      `${row.municipio_origem || "?"}/${row.uf_origem || "?"} → ${row.municipio_destino || "?"}/${row.uf_destino || "?"}`,
  },
  {
    field: "peso", headerName: "Peso (kg)", width: 100, align: "right", headerAlign: "right",
    valueFormatter: (v) => Number(v || 0).toLocaleString("pt-BR", { maximumFractionDigits: 1 }),
  },
  {
    field: "valor_frete", headerName: "Vlr. Frete", width: 120, align: "right", headerAlign: "right",
    valueFormatter: (v) =>
      Number(v || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" }),
  },
  {
    field: "status", headerName: "Status", width: 110,
    renderCell: (p) => (
      <Chip
        size="small"
        label={p.value === "ATIVO" ? "Ativo" : "Cancelado"}
        sx={{
          bgcolor: p.value === "ATIVO" ? `${GD.ok}1F` : `${GD.danger}1F`,
          color: p.value === "ATIVO" ? GD.ok : GD.danger,
          fontWeight: 700,
        }}
      />
    ),
  },
  {
    field: "origem_importacao", headerName: "Origem", width: 90,
    renderCell: (p) => (
      <Chip
        size="small"
        label={p.value}
        sx={{
          bgcolor: p.value === "XML" ? `${GD.blue}1F` : `${GD.warn}1F`,
          color: p.value === "XML" ? GD.blue : GD.warn,
          fontWeight: 700,
        }}
      />
    ),
  },
];

/**
 * Grid de CT-e individuais da tela de Importação (v6.11).
 *
 * Lista paginada (server-side) de todos os CT-es já importados da empresa
 * (XML ou Excel), com seleção por checkbox e exclusão em lote dos
 * selecionados. Recarrega automaticamente via `recarregarSinal` (mesmo
 * padrão de `IndicadorBaseCte`), e avisa o pai via `onExcluido` para que os
 * demais indicadores da tela também sejam atualizados.
 */
export default function GridCte({ recarregarSinal = 0, onExcluido }) {
  const { usuario } = useAuth();
  const { empresaAtivaId } = useEmpresa();
  const { sucesso, erro: erroToast } = useFeedback();

  const podeExcluir = ehAdmin(usuario);

  const [linhas, setLinhas] = useState([]);
  const [total, setTotal] = useState(0);
  const [carregando, setCarregando] = useState(false);
  const [paginacao, setPaginacao] = useState({ page: 0, pageSize: 25 });
  const [selecao, setSelecao] = useState([]);
  const [confirmando, setConfirmando] = useState(false);
  const [excluindo, setExcluindo] = useState(false);

  const carregar = useCallback(async () => {
    if (!empresaAtivaId) return;
    setCarregando(true);
    try {
      const dados = await importacaoApi.listarCtes(empresaAtivaId, {
        page: paginacao.page + 1,
        pageSize: paginacao.pageSize,
      });
      setLinhas(dados.items || []);
      setTotal(dados.total || 0);
    } catch (e) {
      erroToast(extrairErro(e, "Falha ao carregar os CT-es."));
    } finally {
      setCarregando(false);
    }
  }, [empresaAtivaId, paginacao, erroToast]);

  useEffect(() => { carregar(); }, [carregar, recarregarSinal]);

  if (!empresaAtivaId) return null;

  const confirmarExclusao = async () => {
    setExcluindo(true);
    try {
      const r = await importacaoApi.excluirCtesPorIds(empresaAtivaId, selecao);
      sucesso(`${r.excluidos} CT-e(s) excluído(s).`);
      setSelecao([]);
      setConfirmando(false);
      await carregar();
      onExcluido?.();
    } catch (e) {
      erroToast(extrairErro(e, "Falha ao excluir os CT-es selecionados."));
    } finally {
      setExcluindo(false);
    }
  };

  return (
    <Card sx={{ mt: 2.5 }}>
      <CardContent>
        <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 0.5 }}>
          <ViewListIcon sx={{ color: GD.indigo }} />
          <Typography variant="subtitle1" fontWeight={700}>
            CT-e importados
          </Typography>
        </Stack>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
          Selecione um ou mais registros para excluir. A exclusão é permanente.
        </Typography>

        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1.5 }}>
          <Typography variant="caption" color="text.secondary">
            <b>{selecao.length}</b> selecionado(s)
          </Typography>
          {podeExcluir && (
            <Button
              size="small"
              color="error"
              variant="outlined"
              startIcon={<DeleteForeverIcon />}
              disabled={selecao.length === 0}
              onClick={() => setConfirmando(true)}
            >
              Excluir selecionados
            </Button>
          )}
        </Stack>

        <Box sx={{ width: "100%" }}>
          <Tabela
            rows={linhas}
            columns={COLUNAS}
            carregando={carregando}
            checkboxSelection={podeExcluir}
            rowSelectionModel={selecao}
            onRowSelectionModelChange={(modelo) => setSelecao(modelo)}
            paginationMode="server"
            rowCount={total}
            paginationModel={paginacao}
            onPaginationModelChange={setPaginacao}
            pageSizeOptions={[10, 25, 50, 100]}
          />
        </Box>
      </CardContent>

      <ConfirmDialog
        aberto={confirmando}
        titulo="Confirmar exclusão"
        mensagem={`Você está prestes a excluir ${selecao.length} CT-e(s) selecionado(s). Esta ação é permanente e não pode ser desfeita.`}
        textoConfirmar={excluindo ? "Excluindo..." : "Excluir definitivamente"}
        corConfirmar="error"
        carregando={excluindo}
        onConfirmar={confirmarExclusao}
        onCancelar={() => !excluindo && setConfirmando(false)}
      />
    </Card>
  );
}
