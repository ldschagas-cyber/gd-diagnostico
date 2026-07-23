import { useEffect, useState, useCallback } from "react";
import {
  Box, Card, CardContent, Typography, Stack, Button, Chip, Divider,
  Dialog, DialogTitle, DialogContent, DialogContentText, DialogActions,
  TextField, Alert, LinearProgress,
} from "@mui/material";
import DeleteForeverIcon from "@mui/icons-material/DeleteForever";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import { importacaoApi } from "../api/endpoints";
import { extrairErro } from "../api/client";
import { useFeedback } from "./Feedback";
import { useAuth } from "../contexts/AuthContext";
import { useEmpresa } from "../contexts/EmpresaContext";
import { ehAdmin } from "../utils/permissoes";
import { GD } from "../theme";

/**
 * Painel administrativo de gestão de dados importados (CT-e XML / Excel).
 *
 * Visível apenas para administradores. Permite excluir os registros
 * importados da empresa ativa por origem (XML, Excel ou todos). A exclusão é
 * destrutiva e exige que o administrador digite a quantidade exata de
 * registros — validada também no backend antes de remover qualquer dado.
 */
export default function GerenciarDadosImportados() {
  const { usuario } = useAuth();
  const { empresaAtivaId, empresaAtiva } = useEmpresa();
  const { sucesso, erro: erroToast } = useFeedback();

  const [contagem, setContagem] = useState(null);
  const [carregando, setCarregando] = useState(false);
  const [dialogo, setDialogo] = useState(null); // { origem, esperado, rotulo }
  const [confirmacao, setConfirmacao] = useState("");
  const [excluindo, setExcluindo] = useState(false);

  const podeGerenciar = ehAdmin(usuario);

  const carregar = useCallback(async () => {
    if (!empresaAtivaId || !podeGerenciar) return;
    setCarregando(true);
    try {
      const c = await importacaoApi.contarDados(empresaAtivaId);
      setContagem(c);
    } catch (e) {
      erroToast(extrairErro(e, "Falha ao carregar a contagem de dados."));
    } finally {
      setCarregando(false);
    }
  }, [empresaAtivaId, podeGerenciar, erroToast]);

  useEffect(() => { carregar(); }, [carregar]);

  if (!podeGerenciar || !empresaAtivaId) return null;

  const abrirDialogo = (origem, esperado, rotulo) => {
    setConfirmacao("");
    setDialogo({ origem, esperado, rotulo });
  };

  const confirmarExclusao = async () => {
    if (!dialogo) return;
    setExcluindo(true);
    try {
      const r = await importacaoApi.excluirDados(
        empresaAtivaId,
        Number(confirmacao),
        dialogo.origem,
      );
      sucesso(`${r.excluidos} registro(s) excluído(s).`);
      setDialogo(null);
      await carregar();
    } catch (e) {
      erroToast(extrairErro(e, "Falha ao excluir os dados."));
    } finally {
      setExcluindo(false);
    }
  };

  const total = contagem?.total ?? 0;
  const xml = contagem?.xml ?? 0;
  const excel = contagem?.excel ?? 0;

  // Habilita o botão de confirmar só quando o número digitado bate com o esperado.
  const numeroConfere =
    dialogo != null &&
    confirmacao.trim() !== "" &&
    Number(confirmacao) === dialogo.esperado;

  return (
    <Card sx={{ mt: 2.5, border: `1px solid ${GD.warn}33` }}>
      <CardContent>
        <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 0.5 }}>
          <WarningAmberIcon sx={{ color: GD.warn }} />
          <Typography variant="subtitle1" fontWeight={700}>
            Gerenciar dados importados
          </Typography>
          <Chip size="small" label="Administrador" color="warning" variant="outlined" />
        </Stack>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Exclui os registros importados de{" "}
          <b>{empresaAtiva?.nome_fantasia || empresaAtiva?.razao_social}</b>. Esta ação é
          irreversível e remove a base usada por Diagnóstico, Benchmark e Inteligência.
        </Typography>

        {carregando && <LinearProgress sx={{ mb: 2 }} />}

        <Stack
          direction={{ xs: "column", sm: "row" }}
          spacing={1.5}
          divider={<Divider orientation="vertical" flexItem />}
          sx={{ mb: 2 }}
        >
          <Box>
            <Typography variant="h5" fontWeight={700} sx={{ color: GD.indigo }}>{total}</Typography>
            <Typography variant="caption" color="text.secondary">Total importado</Typography>
          </Box>
          <Box>
            <Typography variant="h5" fontWeight={700} sx={{ color: GD.indigo }}>{xml}</Typography>
            <Typography variant="caption" color="text.secondary">Via XML (CT-e)</Typography>
          </Box>
          <Box>
            <Typography variant="h5" fontWeight={700} sx={{ color: GD.indigo }}>{excel}</Typography>
            <Typography variant="caption" color="text.secondary">Via planilha</Typography>
          </Box>
        </Stack>

        <Stack direction="row" spacing={1.5} flexWrap="wrap" useFlexGap>
          <Button
            variant="outlined" color="warning" size="small" startIcon={<DeleteForeverIcon />}
            disabled={xml === 0}
            onClick={() => abrirDialogo("XML", xml, "importados por XML (CT-e)")}
          >
            Excluir XML
          </Button>
          <Button
            variant="outlined" color="warning" size="small" startIcon={<DeleteForeverIcon />}
            disabled={excel === 0}
            onClick={() => abrirDialogo("EXCEL", excel, "importados por planilha")}
          >
            Excluir Excel
          </Button>
          <Button
            variant="contained" color="error" size="small" startIcon={<DeleteForeverIcon />}
            disabled={total === 0}
            onClick={() => abrirDialogo(null, total, "importados (XML + planilha)")}
          >
            Excluir tudo
          </Button>
        </Stack>
      </CardContent>

      <Dialog open={!!dialogo} onClose={() => !excluindo && setDialogo(null)} maxWidth="xs" fullWidth>
        <DialogTitle sx={{ fontWeight: 700, color: "error.main" }}>
          Confirmar exclusão
        </DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ mb: 2 }}>
            Você está prestes a excluir <b>{dialogo?.esperado}</b> registro(s){" "}
            {dialogo?.rotulo} desta empresa. Esta ação é permanente.
          </DialogContentText>
          <Alert severity="warning" sx={{ mb: 2 }}>
            Para confirmar, digite a quantidade exata de registros: <b>{dialogo?.esperado}</b>
          </Alert>
          <TextField
            autoFocus
            fullWidth
            size="small"
            label="Quantidade a excluir"
            value={confirmacao}
            onChange={(e) => setConfirmacao(e.target.value.replace(/\D/g, ""))}
            inputProps={{ inputMode: "numeric" }}
            error={confirmacao !== "" && !numeroConfere}
            helperText={
              confirmacao !== "" && !numeroConfere
                ? "O número não confere com a quantidade a excluir."
                : " "
            }
          />
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setDialogo(null)} color="inherit" disabled={excluindo}>
            Cancelar
          </Button>
          <Button
            onClick={confirmarExclusao}
            variant="contained"
            color="error"
            disabled={!numeroConfere || excluindo}
          >
            {excluindo ? "Excluindo..." : "Excluir definitivamente"}
          </Button>
        </DialogActions>
      </Dialog>
    </Card>
  );
}
