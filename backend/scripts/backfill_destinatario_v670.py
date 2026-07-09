"""CLI — Backfill de destinatário/composição de frete (v6.7.0, DT-27).

Corrige retroativamente CT-e importados ANTES do deploy da v6.7.0: preenche
`destinatario_cnpj`/`destinatario_nome` (dimensão Cliente do DLG, RN-68) e
recategoriza `composicao_frete` (TDE/TDA/Estadia, RN-73), relendo os XML
ORIGINAIS já importados e atualizando o registro existente por chave — sem
criar CT-e novo e sem alterar peso/valor_frete/valor_mercadoria.

Uso:
    python scripts/backfill_destinatario_v670.py --empresa-id 1 --dir ./xmls_originais
    python scripts/backfill_destinatario_v670.py --empresa-id 1 arquivo1.xml arquivo2.xml

Requisitos:
- Rodar com a MESMA variável DATABASE_URL do ambiente que se quer corrigir
  (ex.: no Windows, `set DATABASE_URL=...` antes de chamar o script; em
  produção, defina-a no shell da mesma forma que o backend usa).
- Os arquivos devem ser os XML originais dos CT-e já importados (mesma chave
  de acesso) — reimportar pela tela normal de importação não funciona aqui
  (RN-02 bloqueia como duplicado, sem atualizar o registro).
- Idempotente: pode rodar mais de uma vez sobre os mesmos arquivos sem
  duplicar nada.

Depois de rodar, dispare `POST /dlg/{empresa_id}/processar` (tela Diagnóstico
Logístico → botão "Processar diagnóstico") para o DLG recalcular a dimensão
Cliente com os dados corrigidos.
"""
import argparse
import glob
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # permite rodar sem -m

from app.application.use_cases.backfill_destinatario import BackfillDestinatarioUseCase  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.infrastructure.database.repositories import CTeRepository  # noqa: E402


def _coletar_arquivos(caminhos: list, diretorio: str) -> list:
    alvos = list(caminhos)
    if diretorio:
        alvos += sorted(glob.glob(str(Path(diretorio) / "*.xml")))

    arquivos = []
    for caminho in alvos:
        p = Path(caminho)
        if not p.is_file():
            print(f"[aviso] arquivo não encontrado, ignorado: {caminho}")
            continue
        arquivos.append((p.name, p.read_bytes()))
    return arquivos


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill de destinatário/composição de frete (v6.7.0, DT-27).",
    )
    parser.add_argument("--empresa-id", type=int, required=True, help="ID da empresa (isolamento multi-tenant).")
    parser.add_argument("--dir", type=str, default=None, help="Diretório com os XML originais (*.xml).")
    parser.add_argument("arquivos", nargs="*", help="Arquivos XML individuais (opcional, além de --dir).")
    args = parser.parse_args()

    arquivos = _coletar_arquivos(args.arquivos, args.dir)
    if not arquivos:
        print("Nenhum arquivo XML informado — use --dir <pasta> e/ou passe caminhos individuais.")
        sys.exit(1)

    print(f"Empresa {args.empresa_id}: processando {len(arquivos)} arquivo(s)...")

    db = SessionLocal()
    try:
        uc = BackfillDestinatarioUseCase(CTeRepository(db))
        resultado = uc.executar(args.empresa_id, arquivos)
    finally:
        db.close()

    print()
    print(f"Total de arquivos:  {resultado.total_arquivos}")
    print(f"Atualizados:        {resultado.atualizados}")
    print(f"Sem mudança:        {resultado.sem_mudanca}")
    print(f"Não encontrados:    {resultado.nao_encontrados}  (CT-e não existe nessa empresa — verifique --empresa-id)")
    if resultado.erros:
        print(f"Erros ({len(resultado.erros)}):")
        for e in resultado.erros:
            print(f"  - {e}")
    print()
    print(f"Próximo passo: dispare POST /dlg/{args.empresa_id}/processar "
          "(botão \"Processar diagnóstico\") para recalcular a dimensão Cliente.")


if __name__ == "__main__":
    main()
