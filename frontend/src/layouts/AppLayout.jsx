import { useState } from "react";
import { Outlet, useNavigate, useLocation } from "react-router-dom";
import {
  Box, Drawer, AppBar, Toolbar, List, ListItemButton, ListItemIcon,
  ListItemText, Typography, IconButton, Avatar, Menu, MenuItem,
  Divider, useMediaQuery, Collapse, Tooltip,
} from "@mui/material";
import MenuIcon            from "@mui/icons-material/Menu";
import LogoutIcon          from "@mui/icons-material/Logout";
import SpaceDashboardIcon  from "@mui/icons-material/SpaceDashboard";
import BusinessIcon        from "@mui/icons-material/Business";
import LocalShippingIcon   from "@mui/icons-material/LocalShipping";
import PublicIcon          from "@mui/icons-material/Public";
import GavelIcon           from "@mui/icons-material/Gavel";
import InsightsIcon        from "@mui/icons-material/Insights";
import SavingsIcon         from "@mui/icons-material/Savings";
import ManageSearchIcon      from "@mui/icons-material/ManageSearch";
import StackedLineChartIcon from "@mui/icons-material/StackedLineChart";
import LocationCityIcon    from "@mui/icons-material/LocationCity";
import FlagIcon            from "@mui/icons-material/Flag";
import ReceiptLongIcon     from "@mui/icons-material/ReceiptLong";
import UploadFileIcon      from "@mui/icons-material/UploadFile";
import AssessmentIcon      from "@mui/icons-material/Assessment";
import PeopleIcon          from "@mui/icons-material/People";
import LockIcon            from "@mui/icons-material/Lock";
import CompareArrowsIcon   from "@mui/icons-material/CompareArrows";
import ExpandLessIcon      from "@mui/icons-material/ExpandLess";
import ExpandMoreIcon      from "@mui/icons-material/ExpandMore";
import SettingsIcon        from "@mui/icons-material/Settings";
import PsychologyIcon       from "@mui/icons-material/Psychology";
import RecommendIcon        from "@mui/icons-material/Recommend";
import LibraryBooksIcon     from "@mui/icons-material/LibraryBooks";
import GridOnIcon           from "@mui/icons-material/GridOn";
import HubIcon              from "@mui/icons-material/Hub";
import AltRouteIcon         from "@mui/icons-material/AltRoute";
import { useAuth }         from "../contexts/AuthContext";
import { usePrefetch }     from "../hooks/usePrefetch";
import EmpresaAtivaChip    from "../components/EmpresaAtivaChip";
import { GD }              from "../theme";

const LARGURA = 256;

const GRUPOS = [
  {
    titulo: "Acesso e Segurança",
    icone: <LockIcon sx={{ fontSize: 14 }} />,
    soAdmin: true,
    itens: [
      { rotulo: "Usuários",  icone: <PeopleIcon />,   rota: "/usuarios" },
      { rotulo: "Empresas",  icone: <BusinessIcon />, rota: "/empresas" },
    ],
  },
  {
    titulo: "Cadastros",
    itens: [
      { rotulo: "Transportadoras", icone: <LocalShippingIcon />, rota: "/transportadoras" },
      { rotulo: "Regiões Logísticas", icone: <PublicIcon />,     rota: "/regioes" },
      { rotulo: "Cidades",         icone: <LocationCityIcon />,   rota: "/cidades" },
    ],
  },
  {
    titulo: "Parâmetros",
    itens: [
      { rotulo: "Metas", icone: <FlagIcon />,  rota: "/metas" },
      { rotulo: "Hubs Logísticos", icone: <HubIcon />, rota: "/configuracoes/hubs-logisticos" },
      { rotulo: "Matriz Mercado", icone: <GridOnIcon />, rota: "/inteligencia-mercado/matriz-od", soAdmin: true },
    ],
  },
  {
    titulo: "Importação",
    itens: [
      { rotulo: "Importar CTe", icone: <UploadFileIcon />, rota: "/importar/cte" },
    ],
  },
  {
    titulo: "Diagnóstico Logístico",
    itens: [
      { rotulo: "Diagnóstico",  icone: <SpaceDashboardIcon />, rota: "/",          exato: true },
      { rotulo: "Análise de Eficiência", icone: <ManageSearchIcon />, rota: "/diagnostico/dlg" },
      { rotulo: "Radar de Custo", icone: <StackedLineChartIcon />, rota: "/benchmark/mbl" },
      { rotulo: "Simulador de Hub", icone: <AltRouteIcon />, rota: "/simulador/hub" },
      { rotulo: "Fechamento de Frete", icone: <ReceiptLongIcon />, rota: "/fechamento-frete" },
    ],
  },
  {
    titulo: "Benchmark Mercado",
    itens: [
      { rotulo: "Dashboard Executivo",     icone: <InsightsIcon />,          rota: "/benchmark/executivo" },
      { rotulo: "Comparação com o Mercado", icone: <CompareArrowsIcon />,    rota: "/benchmark/comparativo-mercado" },
      { rotulo: "Potencial de Economia",  icone: <SavingsIcon />,           rota: "/benchmark/economia" },
    ],
  },
  {
    titulo: "Concorrência Logística - BID",
    itens: [
      { rotulo: "Dashboard BIDs",   icone: <SpaceDashboardIcon />, rota: "/bid/dashboard" },
      { rotulo: "Motor de Decisão", icone: <GavelIcon />,          rota: "/bid/decisao" },
    ],
  },
  {
    // Grupo próprio — "Recomendações" cruza Diagnóstico Logístico e Benchmark
    // Mercado (ver comentário em Recomendacoes.jsx), então não pertence a
    // nenhum dos dois módulos. Mesmo padrão de "Relatórios" (grupo com um
    // único item).
    titulo: "Recomendações",
    itens: [
      { rotulo: "Recomendações", icone: <RecommendIcon />, rota: "/diagnostico/recomendacoes" },
    ],
  },
  {
    titulo: "Relatórios",
    itens: [
      { rotulo: "Relatórios", icone: <AssessmentIcon />, rota: "/relatorios", exato: true },
    ],
  },
];

const ABERTOS_INIT = Object.fromEntries(GRUPOS.map((g) => [g.titulo, true]));

function Logo() {
  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 1.25, px: 2.5, py: 2 }}>
      <Box sx={{
        width: 38, height: 38, borderRadius: 2, bgcolor: GD.amber, color: GD.indigo,
        display: "grid", placeItems: "center",
        fontFamily: "'Sora', sans-serif", fontWeight: 700, fontSize: 18,
      }}>GD</Box>
      <Box sx={{ lineHeight: 1 }}>
        <Typography sx={{ color: "#fff", fontFamily: "'Sora', sans-serif", fontWeight: 700, fontSize: 15 }}>
          Diagnóstico Logístico
        </Typography>
        <Typography sx={{ color: "rgba(255,255,255,0.6)", fontSize: 11 }}>GD Conecta</Typography>
      </Box>
    </Box>
  );
}

export default function AppLayout() {
  const navigate  = useNavigate();
  const location  = useLocation();
  const { usuario, logout } = useAuth();
  const prefetch  = usePrefetch();
  const desktop   = useMediaQuery((t) => t.breakpoints.up("md"));
  const [aberto, setAberto]         = useState(false);
  const [menuPerfil, setMenuPerfil] = useState(null);
  const [expandido, setExpandido]   = useState(ABERTOS_INIT);

  const irPara = (rota) => { navigate(rota); if (!desktop) setAberto(false); };
  const toggleGrupo = (titulo) => setExpandido((p) => ({ ...p, [titulo]: !p[titulo] }));

  const isAtivo = (item) =>
    item.exato
      ? location.pathname === item.rota
      : item.rota === "/"
        ? location.pathname === "/"
        : location.pathname.startsWith(item.rota);

  const conteudoDrawer = (
    <Box sx={{ height: "100%", bgcolor: GD.indigo, display: "flex", flexDirection: "column" }}>
      <Logo />
      <Divider sx={{ borderColor: "rgba(255,255,255,0.08)" }} />
      <Box sx={{ overflowY: "auto", flex: 1, py: 1 }}>
        {GRUPOS.map((grupo) => {
          if (grupo.soAdmin && !usuario?.is_superuser) return null;

          const renderItem = (item) => {
            const ativo = isAtivo(item);
            return (
              <ListItemButton
                key={item.rotulo}
                onClick={() => irPara(item.rota)}
                onMouseEnter={() => prefetch(item.rota)}
                sx={{
                  mx: 1, borderRadius: 2,
                  color: ativo ? GD.indigo : "rgba(255,255,255,0.82)",
                  bgcolor: ativo ? GD.amber : "transparent",
                  "&:hover": { bgcolor: ativo ? GD.amber : "rgba(255,255,255,0.08)" },
                }}
              >
                <ListItemIcon sx={{ minWidth: 38, color: ativo ? GD.indigo : "rgba(255,255,255,0.7)" }}>
                  {item.icone}
                </ListItemIcon>
                <ListItemText
                  primary={item.rotulo}
                  primaryTypographyProps={{ fontWeight: ativo ? 700 : 500, fontSize: 14 }}
                />
              </ListItemButton>
            );
          };

          // Grupos com subgrupos (ex.: Benchmark Logístico) ganham cabeçalhos de
          // subseção não-clicáveis entre os blocos de itens; o Collapse continua
          // único, no nível do grupo, como nos demais grupos do menu.
          let corpo;
          if (grupo.subgrupos) {
            const subgrupos = grupo.subgrupos
              .map((sg) => ({ ...sg, itens: sg.itens.filter((i) => !i.soAdmin || usuario?.is_superuser) }))
              .filter((sg) => sg.itens.length);
            if (!subgrupos.length) return null;
            corpo = subgrupos.map((sg) => (
              <Box key={sg.titulo}>
                <Typography
                  sx={{
                    px: 2.5, pt: 1, pb: 0.25,
                    fontSize: 10, fontWeight: 700, letterSpacing: "0.08em",
                    color: "rgba(255,255,255,0.30)",
                  }}
                >
                  {sg.titulo.toUpperCase()}
                </Typography>
                <List dense disablePadding>{sg.itens.map(renderItem)}</List>
              </Box>
            ));
          } else {
            const itens = grupo.itens.filter((i) => !i.soAdmin || usuario?.is_superuser);
            if (!itens.length) return null;
            corpo = <List dense disablePadding>{itens.map(renderItem)}</List>;
          }

          const estaAberto = expandido[grupo.titulo] !== false;

          return (
            <Box key={grupo.titulo}>
              <ListItemButton
                onClick={() => toggleGrupo(grupo.titulo)}
                sx={{ px: 2, py: 0.75, "&:hover": { bgcolor: "rgba(255,255,255,0.06)" } }}
              >
                <ListItemText
                  primary={grupo.titulo.toUpperCase()}
                  primaryTypographyProps={{
                    fontSize: 11, fontWeight: 700, letterSpacing: "0.10em",
                    color: "rgba(255,255,255,0.45)",
                  }}
                />
                {estaAberto
                  ? <ExpandLessIcon sx={{ fontSize: 16, color: "rgba(255,255,255,0.35)" }} />
                  : <ExpandMoreIcon sx={{ fontSize: 16, color: "rgba(255,255,255,0.35)" }} />}
              </ListItemButton>

              <Collapse in={estaAberto} timeout="auto" unmountOnExit>
                {corpo}
              </Collapse>

              <Divider sx={{ borderColor: "rgba(255,255,255,0.05)", mx: 2, my: 0.25 }} />
            </Box>
          );
        })}
      </Box>
      <Divider sx={{ borderColor: "rgba(255,255,255,0.08)" }} />
      <Box sx={{ p: 2 }}>
        <Typography sx={{ color: "rgba(255,255,255,0.5)", fontSize: 11 }}>
          v6.18.0 · GD Diagnóstico Logístico
        </Typography>
      </Box>
    </Box>
  );

  return (
    <Box sx={{ display: "flex", minHeight: "100vh" }}>
      {desktop && (
        <Drawer variant="permanent" sx={{ width: LARGURA, flexShrink: 0, "& .MuiDrawer-paper": { width: LARGURA, boxSizing: "border-box", border: "none" } }}>
          {conteudoDrawer}
        </Drawer>
      )}
      {!desktop && (
        <Drawer open={aberto} onClose={() => setAberto(false)} sx={{ "& .MuiDrawer-paper": { width: LARGURA } }}>
          {conteudoDrawer}
        </Drawer>
      )}

      <Box sx={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        <AppBar position="sticky" elevation={0} sx={{ bgcolor: "#fff", borderBottom: "1px solid", borderColor: "divider", zIndex: 1100 }}>
          <Toolbar sx={{ gap: 1 }}>
            {!desktop && (
              <IconButton onClick={() => setAberto(true)} edge="start"><MenuIcon /></IconButton>
            )}
            <Box sx={{ flex: 1 }}><EmpresaAtivaChip /></Box>
            <Tooltip title="Assistente">
              <IconButton onClick={() => navigate("/inteligencia/assistente")} size="small">
                <PsychologyIcon sx={{ color: GD.indigo }} />
              </IconButton>
            </Tooltip>
            <Tooltip title="Base de Conhecimento">
              <IconButton onClick={() => navigate("/inteligencia/conhecimento")} size="small">
                <LibraryBooksIcon sx={{ color: GD.indigo }} />
              </IconButton>
            </Tooltip>
            <IconButton onClick={(e) => setMenuPerfil(e.currentTarget)} size="small">
              <Avatar sx={{ width: 34, height: 34, bgcolor: GD.indigo, fontSize: 14 }}>
                {usuario?.nome?.[0]?.toUpperCase() || "U"}
              </Avatar>
            </IconButton>
            <Menu anchorEl={menuPerfil} open={Boolean(menuPerfil)} onClose={() => setMenuPerfil(null)}
              anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
              transformOrigin={{ vertical: "top", horizontal: "right" }}>
              <MenuItem disabled sx={{ opacity: "1 !important" }}>
                <Box>
                  <Typography variant="body2" fontWeight={600}>{usuario?.nome}</Typography>
                  <Typography variant="caption" color="text.secondary">{usuario?.email}</Typography>
                </Box>
              </MenuItem>
              <Divider />
              <MenuItem onClick={() => { setMenuPerfil(null); logout(); }}>
                <ListItemIcon><LogoutIcon fontSize="small" /></ListItemIcon>
                Sair
              </MenuItem>
            </Menu>
          </Toolbar>
        </AppBar>

        <Box component="main" sx={{ flex: 1, p: { xs: 2, md: 3 }, bgcolor: "#F8F9FA" }}>
          <Outlet />
        </Box>
      </Box>
    </Box>
  );
}
