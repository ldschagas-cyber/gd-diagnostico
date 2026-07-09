import { Box, Paper, Typography, Stack } from "@mui/material";
import InboxIcon from "@mui/icons-material/Inbox";
import { DataGrid } from "@mui/x-data-grid";

const TEXTOS_PT = {
  noRowsLabel: "Nenhum registro",
  footerRowSelected: (n) =>
    n > 1 ? `${n} linhas selecionadas` : `${n} linha selecionada`,
  footerTotalRows: "Total de linhas:",
  columnMenuSortAsc: "Ordenar crescente",
  columnMenuSortDesc: "Ordenar decrescente",
  columnMenuFilter: "Filtrar",
  columnMenuHideColumn: "Ocultar coluna",
  columnMenuShowColumns: "Exibir colunas",
  columnMenuManageColumns: "Gerenciar colunas",
  columnMenuUnsort: "Remover ordenação",
  MuiTablePagination: {
    labelRowsPerPage: "Linhas por página:",
    labelDisplayedRows: ({ from, to, count }) => `${from}–${to} de ${count}`,
  },
};

export function VazioEstado({ mensagem, descricao }) {
  return (
    <Paper variant="outlined" sx={{ p: 6, textAlign: "center" }}>
      <Stack spacing={1.5} alignItems="center">
        <InboxIcon sx={{ fontSize: 48, color: "text.disabled" }} />
        <Typography variant="h6" color="text.secondary">
          {mensagem}
        </Typography>
        {descricao && (
          <Typography variant="body2" color="text.secondary">
            {descricao}
          </Typography>
        )}
      </Stack>
    </Paper>
  );
}

export default function Tabela({ rows, columns, carregando, altura = 540, ...props }) {
  return (
    <Box sx={{ width: "100%" }}>
      <DataGrid
        rows={rows}
        columns={columns}
        loading={carregando}
        autoHeight={rows.length > 0 && rows.length <= 8}
        localeText={TEXTOS_PT}
        disableRowSelectionOnClick
        pageSizeOptions={[10, 25, 50, 100]}
        initialState={{
          pagination: { paginationModel: { pageSize: 25 } },
        }}
        sx={{
          minHeight: rows.length > 8 ? altura : undefined,
          border: "1px solid rgba(45,53,97,0.12)",
          borderRadius: 2,
          backgroundColor: "#fff",
          "& .MuiDataGrid-columnHeaders": {
            backgroundColor: "#F5F1EB",
          },
          "& .MuiDataGrid-columnHeaderTitle": {
            fontWeight: 700,
            color: "#2D3561",
          },
        }}
        {...props}
      />
    </Box>
  );
}
