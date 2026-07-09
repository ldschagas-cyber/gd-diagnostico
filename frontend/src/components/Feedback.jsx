import { createContext, useContext, useState, useCallback } from "react";
import { Snackbar, Alert } from "@mui/material";

const FeedbackContext = createContext(null);

export function FeedbackProvider({ children }) {
  const [estado, setEstado] = useState({
    aberto: false,
    mensagem: "",
    severidade: "success",
  });

  const mostrar = useCallback((mensagem, severidade = "success") => {
    setEstado({ aberto: true, mensagem, severidade });
  }, []);

  const sucesso = useCallback((m) => mostrar(m, "success"), [mostrar]);
  const erro = useCallback((m) => mostrar(m, "error"), [mostrar]);
  const info = useCallback((m) => mostrar(m, "info"), [mostrar]);

  const fechar = (_, motivo) => {
    if (motivo === "clickaway") return;
    setEstado((e) => ({ ...e, aberto: false }));
  };

  return (
    <FeedbackContext.Provider value={{ mostrar, sucesso, erro, info }}>
      {children}
      <Snackbar
        open={estado.aberto}
        autoHideDuration={5000}
        onClose={fechar}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
      >
        <Alert
          onClose={fechar}
          severity={estado.severidade}
          variant="filled"
          sx={{ width: "100%" }}
        >
          {estado.mensagem}
        </Alert>
      </Snackbar>
    </FeedbackContext.Provider>
  );
}

export const useFeedback = () => useContext(FeedbackContext);
