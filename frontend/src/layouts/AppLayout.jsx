import { useState } from "react";
import { Outlet, useNavigate, useLocation } from "react-router-dom";
import {
  Box, Drawer, AppBar, Toolbar, List, ListItemButton, ListItemIcon,
  ListItemText, Typography, IconButton, Avatar, Menu, MenuItem,
  Divider, useMediaQuery, Collapse,
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
import UploadFileIcon      from "@mui/icons-material/UploadFile";
import TableChartIcon      from "@mui/icons-material/TableChart";
import AssessmentIcon      from "@mui/icons-material/Assessment";
import PeopleIcon          from "@mui/icons-material/People";
import TuneIcon            from "@mui/icons-material/Tune";
import LockIcon            from "@mui/icons-material/Lock";
import CompareArrowsIcon   from "@mui/icons-material/CompareArrows";
import ExpandLessIcon      from "@mui/icons-material/ExpandLess";
import ExpandMoreIcon      from "@mui/icons-material/ExpandMore";
import SettingsIcon        from "@mui/icons-material/Settings";
import PsychologyIcon       from "@mui/icons-material/Psychology";
import AutoAwesomeIcon      from "@mui/icons-material/AutoAwesome";
import LightbulbIcon        from "@mui/icons-material/Lightbulb";
import RecommendIcon        from "@mui/icons-material/Recommend";
import SpeedIcon            from "@mui/icons-material/Speed";
import LibraryBooksIcon     from "@mui/icons-material/LibraryBooks";
import GridOnIcon           from "@mui/icons-material/GridOn";
import HubIcon              from "@mui/icons-material/Hub";
import { useAuth }         from "../contexts/AuthContext";
import { usePrefetch }     from "../hooks/usePrefetch";
import EmpresaSelector     from "../components/EmpresaSelector";
import { GD }              from "../theme";

const LARGURA = 256;

const GRUPOS = [
  {
    titulo: "Acesso e Segurança",
    icone: <LockIcon sx={{ fontSize: 14 }} />,
    soAdmin: true,
    itens: [
      { rotulo: "Usuários",          icone: <PeopleIcon />,   rota: "/usuarios" },
      { rotulo: "Empresas e Filiais", icone: <BusinessIcon />, rota: "/empresas" },
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
    titulo: "Configuração",
    itens: [
      { rotulo: "Metas & Mercado (%)", icone: <FlagIcon />,  rota: "/metas" },
      { rotulo: "Hubs Logísticos", icone: <HubIcon />, rota: "/configuracoes/hubs-logisticos" },
    ],
  },
  {
    titulo: "Importação",
    itens: [
      { rotulo: "Importar CT-e",  icone: <UploadFileIcon />, rota: "/importar/cte" },
      { rotulo: "Importar Excel", icone: <TableChartIcon />, rota: "/importar/excel" },
    ],
  },
  {
    titulo: "Diagnóstico Logístico",
    itens: [
      { rotulo: "Dashboard",  icone: <SpaceDashboardIcon />, rota: "/",          exato: true },
      { rotulo: "Diagnóstico", icone: <ManageSearchIcon />, rota: "/diagnostico/dlg" },
      { rotulo: "Recomendações", icone: <RecommendIcon />, rota: "/diagnostico/recomendacoes" },
      { rotulo: "Relatórios", icone: <AssessmentIcon />,     rota: "/relatorios" },
    ],
  },
  {
    titulo: "Inteligência de Mercado",
    itens: [
      { rotulo: "Matriz Benchmark (OD)", icone: <GridOnIcon />, rota: "/inteligencia-mercado/matriz-od" },
    ],
  },
  {
    titulo: "Benchmark Logístico",
    itens: [
      { rotulo: "Dashboard Executivo",    icone: <InsightsIcon />,          rota: "/benchmark/executivo" },
      { rotulo: "Diagnóstico",            icone: <ManageSearchIcon />,      rota: "/benchmark/diagnostico" },
      { rotulo: "Comparativo de Mercado", icone: <CompareArrowsIcon />,     rota: "/benchmark/comparativo-mercado" },
      { rotulo: "Potencial de Economia",  icone: <SavingsIcon />,           rota: "/benchmark/economia" },
    ],
  },
  {
    titulo: "Concorrência Logística - BID",
    itens: [
      { rotulo: "Dashboard BIDs", icone: <SpaceDashboardIcon />, rota: "/bid/dashboard" },
      { rotulo: "BIDs de Frete",  icone: <GavelIcon />,          rota: "/bid", exato: true },
      { rotulo: "Comparativo",    icone: <CompareArrowsIcon />,  rota: "/bid/comparativo" },
      { rotulo: "Motor de Decisão", icone: <GavelIcon />,         rota: "/bid/decisao" },
      { rotulo: "Benchmark (MBL)", icone: <StackedLineChartIcon />, rota: "/bid/mbl" },
    ],
  },
  {
    titulo: "Inteligência Logística - IA",
    itens: [
      { rotulo: "Visão Geral",         icone: <PsychologyIcon />,   rota: "/inteligencia", exato: true },
      { rotulo: "Diagnóstico IA",      icone: <AutoAwesomeIcon />,  rota: "/inteligencia/diagnostico" },
      { rotulo: "Insights",            icone: <LightbulbIcon />,    rota: "/inteligencia/insights" },
      { rotulo: "Score Logístico",     icone: <SpeedIcon />,        rota: "/inteligencia/score" },
      { rotulo: "Oportunidades",       icone: <SavingsIcon />,      rota: "/inteligencia/oportunidades" },
      { rotulo: "Assistente",          icone: <PsychologyIcon />,   rota: "/inteligencia/assistente" },
      { rotulo: "Base de Conhecimento", icone: <LibraryBooksIcon />, rota: "/inteligencia/conhecimento" },
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
          Frete Diagnóstico
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
          v6.9.2 · GD Frete Diagnóstico
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
            <Box sx={{ flex: 1 }}><EmpresaSelector /></Box>
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
