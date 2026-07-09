import { Alert, AlertTitle } from "@mui/material";
import ScienceIcon from "@mui/icons-material/Science";

/**
 * Banner exibido no topo das telas de Inteligência quando a IA está em modo
 * simulado (sem chaves de API). As respostas são mock; os números continuam
 * vindo de consultas SQL reais.
 */
export default function ModoSimuladoBanner({ status }) {
  if (!status || !status.modo_simulado) return null;
  return (
    <Alert severity="info" icon={<ScienceIcon />} sx={{ mb: 3 }}>
      <AlertTitle>Modo simulado ativo</AlertTitle>
      A IA está gerando respostas de demonstração, sem custo. Os números vêm de
      consultas reais ao seu banco — apenas a narrativa é simulada. Configure as
      chaves de API (OpenAI / Anthropic) para ativar as análises reais.
    </Alert>
  );
}
