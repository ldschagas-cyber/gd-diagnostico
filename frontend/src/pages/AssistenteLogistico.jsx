import { useEffect, useState, useRef } from "react";
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
import {
  useIaStatus,
  useIaSessoes,
  useIaMensagens,
  useCriarSessaoAssistente,
  useEnviarMensagemAssistente,
} from "../api/queries";
import { useTelaEstado } from "../hooks/useTelaEstado";
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

  // Sessão ativa persistida entre navegações — evita criar uma sessão nova
  // (e perder o histórico da conversa) toda vez que o usuário volta a esta tela.
  const [tela, , patch] = useTelaEstado("assistente", { sessaoId: null });
  const sessaoId = tela.sessaoId;
  const setSessaoId = (id) => patch({ sessaoId: id });

  const [texto, setTexto] = useState("");
  // Mensagens otimistas (pergunta do usuário + eventual erro) exibidas antes
  // da confirmação do servidor, para manter a UX de chat fluida.
  const [pendentes, setPendentes] = useState([]);
  const fimRef = useRef(null);

  const statusQ = useIaStatus();
  const sessoesQ = useIaSessoes(empresaAtivaId);
  const mensagensQ = useIaMensagens(sessaoId, empresaAtivaId);
  const criarSessaoMut = useCriarSessaoAssistente(empresaAtivaId);
  const enviarMut = useEnviarMensagemAssistente(sessaoId, empresaAtivaId);

  const status = statusQ.data ?? null;
  const mensagensServidor = mensagensQ.data ?? [];
  const mensagens = [...mensagensServidor, ...pendentes];
  const enviando = enviarMut.isPending;
  const iniciando = criarSessaoMut.isPending;

  useEffect(() => {
    if (statusQ.error) fb.erro(extrairErro(statusQ.error));
  }, [statusQ.error]); // eslint-disable-line react-hooks/exhaustive-deps

  // Ao trocar de sessão (nova conversa ou restauração ao voltar à tela),
  // descarta as mensagens otimistas ainda não confirmadas.
  useEffect(() => {
    setPendentes([]);
  }, [sessaoId]);

  // Bootstrap: reaproveita a sessão persistida se ela ainda existir para esta
  // empresa; caso não haja sessão persistida (ou ela não exista mais), cria
  // uma nova — mesmo comportamento de antes, só que sem descartar a conversa
  // a cada remontagem da tela.
  useEffect(() => {
    if (!empresaAtivaId || sessoesQ.isLoading) return;
    if (sessaoId) {
      const existe = sessoesQ.data?.some((s) => s.id === sessaoId);
      if (existe === false) setSessaoId(null);
      return;
    }
    if (criarSessaoMut.isPending) return;
    criarSessaoMut.mutate("Conversa", {
      onSuccess: (sessao) => setSessaoId(sessao.id),
      onError: (e) => fb.erro(extrairErro(e)),
    });
  }, [empresaAtivaId, sessaoId, sessoesQ.isLoading, sessoesQ.data]); // eslint-disable-line react-hooks/exhaustive-deps

  // Segunda rede de segurança: se a sessão persistida falhar ao carregar
  // mensagens (removida, ou de outra empresa), descarta e recria.
  useEffect(() => {
    if (sessaoId && mensagensQ.error) setSessaoId(null);
  }, [sessaoId, mensagensQ.error]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    fimRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [mensagens.length, enviando]);

  const novaConversa = () => {
    criarSessaoMut.mutate("Conversa", {
      onSuccess: (sessao) => setSessaoId(sessao.id),
      onError: (e) => fb.erro(extrairErro(e)),
    });
  };

  const enviar = async (textoMsg) => {
    const conteudo = (textoMsg ?? texto).trim();
    if (!conteudo || !sessaoId || enviando) return;
    setTexto("");
    setPendentes((prev) => [...prev, { papel: "user", conteudo, ferramentas_usadas: {} }]);
    try {
      await enviarMut.mutateAsync(conteudo);
      // Aguarda o refetch (disparado pela invalidação da mutação) antes de
      // limpar a mensagem otimista, evitando o "flash" de ela sumir enquanto
      // os dados reais ainda não chegaram.
      await mensagensQ.refetch();
      setPendentes([]);
    } catch (e) {
      fb.erro(extrairErro(e));
      setPendentes((prev) => [
        ...prev,
        { papel: "assistant", conteudo: "Desculpe, ocorreu um erro ao processar.", ferramentas_usadas: {} },
      ]);
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
          <Button variant="outlined" startIcon={<AddIcon />} onClick={novaConversa} disabled={iniciando}>
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
