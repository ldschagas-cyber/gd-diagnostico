"""CLI — Backfill provisório de % Frete legado para a Matriz Mercado (v6.17).

A tela "Referência de Frete" legada (tabela `benchmarks`) tinha % Frete/Mercadoria
só por macro-região, sem origem. A Matriz Mercado (`benchmark_mercado`) exige
corredor (origem×destino) — não há mapeamento 1:1 possível, então este script
NÃO migra dado real de corredor: ele só evita que o indicador de %Frete do
Dashboard fique em branco durante a transição, copiando o valor legado de cada
região para uma linha "intra-regional" (origem=destino=região, setor=TODOS)
da Matriz Mercado, marcada como provisória em `metodologia`.

Comportamento:
- Se já existir uma linha real para origem=destino=região/TODOS/TODOS/0/0,
  só os campos frete_pct_min/medio/max são atualizados — R$/kg cadastrado
  manualmente NUNCA é sobrescrito.
- Se não existir, cria uma linha nova com R$/kg também vindo do legado
  (frete_kg_min/medio/max → P10/P50/P90), claramente marcada em `metodologia`
  como dado provisório — para não deixar a linha com R$/kg zerado/quebrado.
- Idempotente: pode rodar mais de uma vez sem duplicar (upsert pela mesma
  chave única da Matriz Mercado).
- A região "NACIONAL" do legado não tem par origem/destino na Matriz Mercado
  (vocabulário de região é só as 5 macro-regiões) — não é migrada; o
  indicador nacional já agrega min/max de todas as linhas de região mesmo
  assim.

Uso:
    python scripts/backfill_matriz_mercado_pct.py

Requisitos: rodar com a MESMA variável DATABASE_URL do ambiente que se quer
corrigir (mesmo padrão de scripts/backfill_destinatario_v670.py).

Depois de rodar, o dado real por corredor deve substituir estas linhas
provisórias assim que a pesquisa de mercado por corredor avançar (ver
MatrizOD.jsx / tela Matriz Mercado).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # permite rodar sem -m

from sqlalchemy import select  # noqa: E402

from app.core.database import SessionLocal  # noqa: E402
from app.infrastructure.database.models import BenchmarkMercadoModel, BenchmarkModel  # noqa: E402

METODOLOGIA_PROVISORIA = (
    "Migrado do legado (Referência de Frete) — dado agregado regional "
    "provisório, não específico de corredor. Substituir por pesquisa de "
    "corredor real quando disponível."
)


def main() -> None:
    db = SessionLocal()
    atualizados = 0
    criados = 0
    ignorados = 0
    try:
        legado = db.scalars(select(BenchmarkModel)).all()
        for b in legado:
            regiao = (b.regiao or "").strip().upper()
            if regiao == "NACIONAL":
                ignorados += 1
                print(f"[ignorado] {regiao}: sem par origem/destino na Matriz Mercado.")
                continue
            if not (b.frete_pct_min or b.frete_pct_medio or b.frete_pct_max):
                ignorados += 1
                print(f"[ignorado] {regiao}: sem %Frete cadastrado no legado.")
                continue

            m = db.scalars(
                select(BenchmarkMercadoModel).where(
                    BenchmarkMercadoModel.origem_regiao == regiao,
                    BenchmarkMercadoModel.destino_regiao == regiao,
                    BenchmarkMercadoModel.modal == "",
                    BenchmarkMercadoModel.tipo_operacao == "TODOS",
                    BenchmarkMercadoModel.setor == "TODOS",
                    BenchmarkMercadoModel.faixa_peso_min == 0,
                    BenchmarkMercadoModel.faixa_peso_max == 0,
                )
            ).first()

            if m:
                m.frete_pct_min = b.frete_pct_min
                m.frete_pct_medio = b.frete_pct_medio
                m.frete_pct_max = b.frete_pct_max
                atualizados += 1
                print(f"[atualizado] {regiao}->{regiao}: %Frete {b.frete_pct_min}-{b.frete_pct_medio}-{b.frete_pct_max}"
                      f" (R$/kg existente preservado: p50={m.rs_kg_p50})")
            else:
                m = BenchmarkMercadoModel(
                    origem_regiao=regiao, destino_regiao=regiao, modal="", tipo_operacao="TODOS", setor="TODOS",
                    faixa_peso_min=0, faixa_peso_max=0,
                    rs_kg_p10=b.frete_kg_min, rs_kg_p25=b.frete_kg_min,
                    rs_kg_p50=b.frete_kg_medio, rs_kg_p75=b.frete_kg_max, rs_kg_p90=b.frete_kg_max,
                    frete_pct_min=b.frete_pct_min, frete_pct_medio=b.frete_pct_medio, frete_pct_max=b.frete_pct_max,
                    fonte="MERCADO", metodologia=METODOLOGIA_PROVISORIA,
                )
                db.add(m)
                criados += 1
                print(f"[criado] {regiao}->{regiao}: R$/kg e %Frete provisórios a partir do legado.")

        db.commit()
    finally:
        db.close()

    print()
    print(f"Atualizados: {atualizados}  |  Criados: {criados}  |  Ignorados: {ignorados}")


if __name__ == "__main__":
    main()
