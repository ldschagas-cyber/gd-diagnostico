import { createTheme } from "@mui/material/styles";

// ---------------------------------------------------------------------------
// Identidade visual GD Conecta
//   Indigo  #2D3561  — cor institucional (navegação, títulos)
//   Amber   #C9A84C  — destaque / chamadas de ação
//   Blue    #0077A8  — dados e elementos interativos secundários
//   Ivory   #F5F1EB  — fundo de superfícies
// ---------------------------------------------------------------------------
export const GD = {
  indigo: "#2D3561",
  indigoDark: "#1F2647",
  amber: "#C9A84C",
  amberDark: "#A98A33",
  blue: "#0077A8",
  blueDark: "#005C82",
  ivory: "#F5F1EB",
  ivoryDeep: "#ECE6DA",
  ink: "#1C2030",
  slate: "#5A6072",
  ok: "#2E7D5B",
  warn: "#C9772F",
  danger: "#B4453B",
};

const theme = createTheme({
  palette: {
    mode: "light",
    primary: { main: GD.indigo, dark: GD.indigoDark, contrastText: "#FFFFFF" },
    secondary: { main: GD.amber, dark: GD.amberDark, contrastText: "#1C2030" },
    info: { main: GD.blue, dark: GD.blueDark, contrastText: "#FFFFFF" },
    success: { main: GD.ok },
    warning: { main: GD.warn },
    error: { main: GD.danger },
    background: { default: GD.ivory, paper: "#FFFFFF" },
    text: { primary: GD.ink, secondary: GD.slate },
    divider: "rgba(45,53,97,0.12)",
  },
  shape: { borderRadius: 10 },
  typography: {
    fontFamily: "'Inter', system-ui, sans-serif",
    h1: { fontFamily: "'Sora', sans-serif", fontWeight: 700 },
    h2: { fontFamily: "'Sora', sans-serif", fontWeight: 700 },
    h3: { fontFamily: "'Sora', sans-serif", fontWeight: 600 },
    h4: { fontFamily: "'Sora', sans-serif", fontWeight: 600, letterSpacing: "-0.01em" },
    h5: { fontFamily: "'Sora', sans-serif", fontWeight: 600 },
    h6: { fontFamily: "'Sora', sans-serif", fontWeight: 600 },
    button: { textTransform: "none", fontWeight: 600 },
    overline: { fontWeight: 600, letterSpacing: "0.12em" },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: { backgroundColor: GD.ivory },
        "::selection": { background: "rgba(201,168,76,0.35)" },
      },
    },
    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: { root: { borderRadius: 8 } },
    },
    MuiPaper: {
      styleOverrides: {
        outlined: { borderColor: "rgba(45,53,97,0.12)" },
      },
    },
    MuiCard: {
      defaultProps: { variant: "outlined" },
      styleOverrides: {
        root: { borderColor: "rgba(45,53,97,0.12)" },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: "#FFFFFF",
          color: GD.ink,
          borderBottom: "1px solid rgba(45,53,97,0.12)",
        },
      },
    },
    MuiChip: {
      styleOverrides: { root: { fontWeight: 600 } },
    },
    MuiTableHead: {
      styleOverrides: {
        root: { "& th": { fontWeight: 700, color: GD.indigo } },
      },
    },
    MuiTextField: {
      defaultProps: { size: "small", fullWidth: true },
    },
  },
});

export default theme;
