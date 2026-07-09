import { useEffect, useState, useRef, useCallback } from "react";
import {
  Box, Card, CardContent, Typography, Button, TextField, IconButton,
  Stack, Chip, LinearProgress, Avatar, Paper, Tooltip, Divider,
} from "@mui/material";
import PsychologyIcon from "@mui/icons-material/Psychology";
import SendIcon from "@mui/icons-material/Send";
import AddIcon from "@mui/icons-material/Add";
import BuildIcon from "@mui/icons-material/Build";
import PersonIcon from "@mui/icons-material/Person";
import PageHeader from "../components/PageHeader";
import ModoSimuladoBanner from "../components/ModoSimuladoBanner";
import { VazioEstado } from "../components/Tabela";
import { useEmpresa } from "../contexts/EmpresaContext";
import { useFeedback } from "../components/Feedback";
import { inteligenciaApi } from "../api/endpoints";
import { extrairErro } from "../api/client";
import { GD } from "../theme";

const SUGESTOES = [
  "Qual minha transportadora mais cara?",
  "Qual região tem maior custo?",
  "Quanto posso economizar?",
  "Qual filial tem pior desempenho?",
  "Quais transportadoras convidar para BID?",
];

function Mensagem({ msg }) {
  const ehUser = msg.papel === "user";
  const calls = msg.ferramentas_usadas?.calls || [];
  return (
    <Stack
      direction="row"
      spacing={1.5}
      sx={{ mb: 2, flexDirection: ehUser ? "row-reverse" : "row" }}
    >
      <Avatar sx={{ bgcolor: ehUser ? GD.blue : GD.indigo, width: 36, height: 36 }}>
        {ehUser ? <PersonIcon fontSize="small" /> : <PsychologyIcon fontSize="small" />}
      </Avatar>
      <Box sx={{ maxWidth: "75%" }}>
        <Paper
          variant="outlined"
          sx={{
            p: 1.5,
            bgcolor: ehUser ? GD.blue : "#fff",
            color: ehUser ? "#fff" : "text.primary",
            borderColor: ehUser ? GD.blue : "divider",
          }}
        >
          <Typography variant="body2" sx={{ whiteSpace: "pre-line" }}>
            {msg.conteudo}
          </Typography>
        </Paper>
        {calls.length > 0 && (
          <Stack direction="row" spacing={0.5} sx={{ mt: 0.5, flexWrap: "wrap", gap: 0.5 }}>
            {calls.map((c, i) => (
              <Tooltip key={i} title="Ferramenta consultada (dado real via SQL)">
                <Chip
                  icon={<BuildIcon sx={{ fontSize: 14 }} />}
                  label={c.ferramenta}
                  size="small"
                  sx={{ bgcolor: GD.ivoryDeep, fontSize: "0.7rem" }}
                />
              </Tooltip>
            ))}
          </Stack>
        )}
      </Box>
    </Stack>
  );
}

export default function AssistenteLogistico() {
  const { empresaAtivaId } = useEmpresa();
  const fb = useFeedback();
  const [status, setStatus] = useState(null);
  const [sessaoId, setSessaoId] = useState(null);
  const [mensagens, setMensagens] = useState([]);
  const [texto, setTexto] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [iniciando, setIniciando] = useState(false);
  const fimRef = useRef(null);

  const iniciarSessao = useCallback(async () => {
    if (!empresaAtivaId) return;
    setIniciando(true);
    try {
      const st = await inteligenciaApi.status();
      setStatus(st);
      const sessao = await inteligenciaApi.criarSessao(empresaAtivaId, "Conversa");
      setSessaoId(sessao.id);
      setMensagens([]);
    } catch (e) {
      fb.erro(extrairErro(e));
    } finally {
      setIniciando(false);
    }
  }, [empresaAtivaId, fb]);

  useEffect(() => { iniciarSessao(); }, [iniciarSessao]);

  useEffect(() => {
    fimRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [mensagens, enviando]);

  const enviar = async (textoMsg) => {
    const conteudo = (textoMsg ?? texto).trim();
    if (!conteudo || !sessaoId || enviando) return;
    setTexto("");
    setMensagens((prev) => [...prev, { papel: "user", conteudo, ferramentas_usadas: {} }]);
    setEnviando(true);
    try {
      const resp = await inteligenciaApi.enviarMensagem(sessaoId, empresaAtivaId, conteudo);
      setMensagens((prev) => [...prev, resp]);
    } catch (e) {
      fb.erro(extrairErro(e));
      setMensagens((prev) => [
        ...prev,
        { papel: "assistant", conteudo: "Desculpe, ocorreu um erro ao processar.", ferramentas_usadas: {} },
      ]);
    } finally {
      setEnviando(false);
    }
  };

  if (!empresaAtivaId) {
    return (
      <Box>
        <PageHeader titulo="Assistente Logístico" icone={<PsychologyIcon />} />
        <VazioEstado mensagem="Selecione uma empresa." />
      </Box>
    );
  }

  return (
    <Box sx={{ display: "flex", flexDirection: "column", height: "calc(100vh - 140px)" }}>
      <PageHeader
        titulo="Assistente Logístico"
        subtitulo="Pergunte sobre seus dados — respostas com números reais via consultas SQL"
        icone={<PsychologyIcon sx={{ color: GD.indigo }} />}
        acoes={
          <Button variant="outlined" startIcon={<AddIcon />} onClick={iniciarSessao} disabled={iniciando}>
            Nova conversa
          </Button>
        }
      />

      <ModoSimuladoBanner status={status} />

      <Card variant="outlined" sx={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        {/* Área de mensagens */}
        <Box sx={{ flex: 1, overflowY: "auto", p: 2, bgcolor: GD.ivory }}>
          {mensagens.length === 0 && !enviando && (
            <Box sx={{ textAlign: "center", py: 4 }}>
              <PsychologyIcon sx={{ fontSize: 48, color: GD.indigo, mb: 1, opacity: 0.6 }} />
              <Typography variant="h6" sx={{ mb: 0.5 }}>Como posso ajudar?</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                Faça uma pergunta sobre sua operação logística.
              </Typography>
              <Stack spacing={1} sx={{ maxWidth: 420, mx: "auto" }}>
                {SUGESTOES.map((s) => (
                  <Button
                    key={s} variant="outlined" size="small"
                    onClick={() => enviar(s)} disabled={enviando || !sessaoId}
                    sx={{ justifyContent: "flex-start", textTransform: "none" }}
                  >
                    {s}
                  </Button>
                ))}
              </Stack>
            </Box>
          )}

          {mensagens.map((m, i) => <Mensagem key={i} msg={m} />)}

          {enviando && (
            <Stack direction="row" spacing={1.5} sx={{ mb: 2 }}>
              <Avatar sx={{ bgcolor: GD.indigo, width: 36, height: 36 }}>
                <PsychologyIcon fontSize="small" />
              </Avatar>
              <Paper variant="outlined" sx={{ p: 1.5, bgcolor: "#fff" }}>
                <Typography variant="body2" color="text.secondary">Analisando...</Typography>
              </Paper>
            </Stack>
          )}
          <div ref={fimRef} />
        </Box>

        {enviando && <LinearProgress />}
        <Divider />

        {/* Campo de entrada */}
        <Box sx={{ p: 1.5, display: "flex", gap: 1, bgcolor: "#fff" }}>
          <TextField
            fullWidth size="small" placeholder="Digite sua pergunta..."
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); enviar(); } }}
            disabled={enviando || !sessaoId}
          />
          <IconButton
            color="primary" onClick={() => enviar()}
            disabled={enviando || !sessaoId || !texto.trim()}
            sx={{ bgcolor: GD.indigo, color: "#fff", "&:hover": { bgcolor: GD.indigoDark } }}
          >
            <SendIcon />
          </IconButton>
        </Box>
      </Card>
    </Box>
  );
}
