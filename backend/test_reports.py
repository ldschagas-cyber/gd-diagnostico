"""Script de verificação manual (não faz parte do app) — gera os relatórios HTML
novos/atualizados com dados reais da empresa 1 e salva em /tmp para inspeção."""
from datetime import datetime

from app.core.database import SessionLocal
from app.infrastructure.database.repositories import (
    CTeRepository, EmpresaRepository, TransportadoraRepository,
    MetaNacionalRepository, MetaRegionalRepository, BenchmarkRepository,
    RecomendacaoRepository,
)
from app.application.use_cases.diagnostico import DiagnosticoUseCase
from app.application.use_cases.dlg import DlgUseCase
from app.application.use_cases.benchmark import BenchmarkUseCase
from app.infrastructure.reports.html_report import gerar_relatorio_html
from app.infrastructure.reports.benchmark_report import gerar_benchmark_html

db = SessionLocal()
empresa_id = 1

cte_repo = CTeRepository(db)
empresa_repo = EmpresaRepository(db)
transp_repo = TransportadoraRepository(db)
meta_nac = MetaNacionalRepository(db)
meta_reg = MetaRegionalRepository(db)
bench_repo = BenchmarkRepository(db)

diag_uc = DiagnosticoUseCase(cte_repo, empresa_repo, transp_repo, meta_nac, meta_reg)
diag = diag_uc.gerar(empresa_id, None, None)

dlg_uc = DlgUseCase(db)
dlg_por_dim = {
    dim: dlg_uc.listar(empresa_id, dimensao=dim, modo="consolidado", data_inicio=None, data_fim=None)
    for dim in ("CLIENTE_FINAL", "ROTA", "TRANSPORTADORA", "FILIAL")
}
outliers = dlg_uc.listar_outliers(empresa_id, data_inicio=None, data_fim=None)
recomendacoes = RecomendacaoRepository(db).listar(empresa_id)

html_diag = gerar_relatorio_html(diag, dlg_por_dim, outliers, recomendacoes, gerado_em=datetime.now().strftime("%d/%m/%Y %H:%M"))
with open("/tmp/diagnostico.html", "wb") as f:
    f.write(html_diag)
print("Diagnostico OK ->", len(html_diag), "bytes")

bench_uc = BenchmarkUseCase(diag_uc, cte_repo, bench_repo, db=db)
nome = empresa_repo.get(empresa_id).nome_fantasia or empresa_repo.get(empresa_id).razao_social
nacional = bench_uc.nacional(empresa_id, None, None, None)
nacional.empresa_nome = nome
regional = bench_uc.regional(empresa_id, None, None, None)
transportadoras = bench_uc.transportadoras(empresa_id, None, None)
economia = bench_uc.potencial_economia(empresa_id, None, None)

html_bench = gerar_benchmark_html(nome, nacional, regional, transportadoras, economia, gerado_em=datetime.now().strftime("%d/%m/%Y %H:%M"))
with open("/tmp/benchmark.html", "wb") as f:
    f.write(html_bench)
print("Benchmark OK ->", len(html_bench), "bytes")

db.close()
