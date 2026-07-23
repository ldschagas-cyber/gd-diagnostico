import React from "react";
import ReactDOM from "react-dom/client";
import { ThemeProvider, CssBaseline } from "@mui/material";
import { ptBR } from "@mui/material/locale";
import { createTheme } from "@mui/material/styles";
import { ptBR as dgPtBR } from "@mui/x-data-grid/locales";
import { QueryClientProvider } from "@tanstack/react-query";
import baseTheme from "./theme";
import { queryClient } from "./api/queryClient";
import App from "./App";
import "./index.css";

// Aplica as localizações pt-BR do MUI e do DataGrid sobre o tema base.
const theme = createTheme(baseTheme, ptBR, dgPtBR);

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <App />
      </ThemeProvider>
    </QueryClientProvider>
  </React.StrictMode>
);
