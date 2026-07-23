// Mesma regra do backend (`get_current_superuser` em
// app/presentation/api/dependencies.py): superusuário global OU role=ADMIN
// de uma empresa-cliente têm privilégio de administrador. Usar sempre esta
// função em vez de checar `usuario?.is_superuser` sozinho, para não abrir
// controles no backend que a UI não mostra (ou o inverso).
export function ehAdmin(usuario) {
  return Boolean(usuario?.is_superuser) || usuario?.role === "ADMIN";
}
