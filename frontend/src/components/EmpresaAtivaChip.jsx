import { Box, Typography, Tooltip, Chip } from "@mui/material";
import BusinessIcon from "@mui/icons-material/Business";
import LockOutlinedIcon from "@mui/icons-material/LockOutlined";
import { useEmpresa } from "../contexts/EmpresaContext";
import { GD } from "../theme";

export default function EmpresaAtivaChip() {
  const { empresaAtiva } = useEmpresa();

  if (!empresaAtiva) {
    return (
      <Chip
        icon={<BusinessIcon />}
        label="Nenhuma empresa cadastrada"
        variant="outlined"
        size="small"
      />
    );
  }

  return (
    <Tooltip title="Empresa definida no login. Para trocar, saia e entre novamente.">
      <Box
        sx={{
          display: "inline-flex",
          alignItems: "center",
          gap: 0.75,
          bgcolor: "rgba(45,53,97,0.06)",
          border: "1px solid rgba(45,53,97,0.14)",
          borderRadius: 999,
          px: 1.25,
          py: 0.5,
          cursor: "default",
        }}
      >
        <BusinessIcon sx={{ fontSize: 16, color: GD.indigo }} />
        <Typography variant="body2" sx={{ fontWeight: 600 }}>
          {empresaAtiva.nome_fantasia || empresaAtiva.razao_social}
        </Typography>
        <LockOutlinedIcon sx={{ fontSize: 14, color: "text.secondary" }} />
      </Box>
    </Tooltip>
  );
}
