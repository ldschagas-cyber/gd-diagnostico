import { Select, MenuItem, Box, Typography, Chip } from "@mui/material";
import BusinessIcon from "@mui/icons-material/Business";
import { useEmpresa } from "../contexts/EmpresaContext";

export default function EmpresaSelector() {
  const { empresas, empresaAtivaId, selecionar } = useEmpresa();

  if (!empresas.length) {
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
    <Box sx={{ display: "flex", alignItems: "center", gap: 1, minWidth: 0 }}>
      <Typography
        variant="caption"
        color="text.secondary"
        sx={{ display: { xs: "none", md: "block" }, whiteSpace: "nowrap" }}
      >
        Empresa ativa
      </Typography>
      <Select
        size="small"
        value={empresaAtivaId || ""}
        onChange={(e) => selecionar(Number(e.target.value))}
        sx={{ minWidth: { xs: 160, sm: 240 }, fontWeight: 600 }}
        renderValue={(val) => {
          const emp = empresas.find((e) => e.id === val);
          return emp ? emp.nome_fantasia || emp.razao_social : "Selecionar";
        }}
      >
        {empresas.map((e) => (
          <MenuItem key={e.id} value={e.id}>
            <Box>
              <Typography variant="body2" sx={{ fontWeight: 600 }}>
                {e.nome_fantasia || e.razao_social}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {e.razao_social}
                {e.status === "INATIVO" ? " · inativa" : ""}
              </Typography>
            </Box>
          </MenuItem>
        ))}
      </Select>
    </Box>
  );
}
