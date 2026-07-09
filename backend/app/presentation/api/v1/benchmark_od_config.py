"""Routers de configuração do Benchmark OD (V2.1).

- /hubs                         → catálogo global de hubs (admin)
- /empresas/{id}/clusters       → mapa UF/município → hub, por empresa
- /benchmarks-corredor          → referência de mercado por corredor (admin)
"""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.domain.entities import BenchmarkCorredor, ClusterCliente, HubLogistico
from app.presentation.api.dependencies import (
    get_benchmark_corredor_repo,
    get_cluster_repo,
    get_current_superuser,
    get_current_user,
    verificar_acesso_empresa,
    get_empresa_repo,
    get_hub_repo,
)
from app.presentation.schemas import (
    BenchmarkCorredorIn,
    BenchmarkCorredorOut,
    ClusterClienteIn,
    ClusterClienteOut,
    HubLogisticoIn,
    HubLogisticoOut,
)

# ───────────────────────── Hubs (catálogo global) ─────────────────────────
hubs_router = APIRouter(prefix="/hubs", tags=["Benchmark OD — Hubs"])


@hubs_router.get("", response_model=list[HubLogisticoOut])
def listar_hubs(
    apenas_ativos: bool = False,
    _=Depends(get_current_user),
    repo=Depends(get_hub_repo),
):
    return repo.list(apenas_ativos=apenas_ativos)


@hubs_router.post("", response_model=HubLogisticoOut, status_code=201)
def criar_hub(payload: HubLogisticoIn, _=Depends(get_current_superuser), repo=Depends(get_hub_repo)):
    codigo = payload.codigo.strip().upper().replace(" ", "_")
    if repo.get_by_codigo(codigo):
        raise HTTPException(409, f"Já existe um hub com o código {codigo}.")
    dados = payload.model_dump()
    dados["codigo"] = codigo
    return repo.create(HubLogistico(**dados))


@hubs_router.put("/{hub_id}", response_model=HubLogisticoOut)
def atualizar_hub(hub_id: int, payload: HubLogisticoIn, _=Depends(get_current_superuser), repo=Depends(get_hub_repo)):
    dados = payload.model_dump()
    dados["codigo"] = payload.codigo.strip().upper().replace(" ", "_")
    atualizado = repo.update(hub_id, HubLogistico(**dados))
    if not atualizado:
        raise HTTPException(404, "Hub não encontrado.")
    return atualizado


@hubs_router.delete("/{hub_id}", status_code=204)
def remover_hub(hub_id: int, _=Depends(get_current_superuser), repo=Depends(get_hub_repo)):
    if not repo.delete(hub_id):
        raise HTTPException(404, "Hub não encontrado.")


# ─────────────────── Clusters por empresa-cliente ───────────────────
clusters_router = APIRouter(prefix="/empresas", tags=["Benchmark OD — Clusters"])


@clusters_router.get("/{empresa_id}/clusters", response_model=list[ClusterClienteOut])
def listar_clusters(
    empresa_id: int,
    _=Depends(verificar_acesso_empresa),
    repo=Depends(get_cluster_repo),
    empresa_repo=Depends(get_empresa_repo),
):
    if not empresa_repo.get(empresa_id):
        raise HTTPException(404, "Empresa não encontrada.")
    return repo.list_by_empresa(empresa_id)


@clusters_router.post("/{empresa_id}/clusters", response_model=ClusterClienteOut, status_code=201)
def criar_cluster(
    empresa_id: int,
    payload: ClusterClienteIn,
    _=Depends(verificar_acesso_empresa),
    repo=Depends(get_cluster_repo),
    hub_repo=Depends(get_hub_repo),
    empresa_repo=Depends(get_empresa_repo),
):
    if not empresa_repo.get(empresa_id):
        raise HTTPException(404, "Empresa não encontrada.")
    if not hub_repo.get(payload.hub_id):
        raise HTTPException(422, "Hub inválido.")
    cluster = ClusterCliente(empresa_id=empresa_id, **payload.model_dump())
    return repo.create(cluster)


@clusters_router.get("/{empresa_id}/clusters/modelo")
def baixar_modelo_clusters(
    empresa_id: int,
    _=Depends(verificar_acesso_empresa),
):
    """Baixa a planilha-modelo (.xlsx) para importação de clusters logísticos.
    Colunas: uf, municipio (opcional), hub_codigo."""
    import openpyxl
    from io import BytesIO
    from fastapi.responses import StreamingResponse
    from openpyxl.styles import Font, PatternFill

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Clusters"
    ws.append(["uf", "municipio", "hub_codigo"])
    azul = PatternFill("solid", fgColor="2D3561")
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = azul
    ws.append(["SP", "São Paulo", "SUDESTE_HUB"])
    ws.append(["SP", "", "SUDESTE_HUB"])
    ws.append(["PE", "Recife", "NORDESTE_HUB"])
    ws.column_dimensions["A"].width = 8
    ws.column_dimensions["B"].width = 28
    ws.column_dimensions["C"].width = 22

    inst = wb.create_sheet("Instruções")
    for linha in [
        ["Como preencher"],
        [""],
        ["uf", "Sigla da UF com 2 letras, ex.: SP, PE (obrigatório)."],
        ["municipio", "Nome do município (opcional). Vazio = regra para a UF inteira."],
        ["hub_codigo", "Código de um Hub já cadastrado, ex.: SUDESTE_HUB (obrigatório)."],
        [""],
        ["Clusters já cadastrados (mesma UF + município) são ignorados."],
    ]:
        inst.append(linha)
    inst["A1"].font = Font(bold=True, size=14)
    inst.column_dimensions["A"].width = 18
    inst.column_dimensions["B"].width = 70

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=modelo_clusters.xlsx"},
    )


@clusters_router.post("/{empresa_id}/clusters/importar", response_model=dict)
async def importar_clusters_excel(
    empresa_id: int,
    arquivo: UploadFile = File(...),
    _=Depends(verificar_acesso_empresa),
    repo=Depends(get_cluster_repo),
    hub_repo=Depends(get_hub_repo),
    empresa_repo=Depends(get_empresa_repo),
):
    """Importa clusters via Excel (.xlsx). Colunas: uf, municipio (opcional),
    hub_codigo. Valida duplicidade (empresa + UF + município) e hub existente."""
    import openpyxl
    from io import BytesIO
    from app.infrastructure.parsers.macro_regiao import macro_por_uf

    if not empresa_repo.get(empresa_id):
        raise HTTPException(404, "Empresa não encontrada.")

    conteudo = await arquivo.read()
    if not conteudo.startswith(b"PK"):
        raise HTTPException(400, "Arquivo não é um Excel (.xlsx) válido.")
    wb = openpyxl.load_workbook(BytesIO(conteudo), data_only=True)
    ws = wb.active

    headers = [str(c.value).strip().lower() if c.value else "" for c in ws[1]]
    col = {h: i for i, h in enumerate(headers)}
    if "uf" not in col or "hub_codigo" not in col:
        raise HTTPException(400, "Colunas obrigatórias ausentes: uf, hub_codigo.")

    # dedup contra o que já existe + dentro do próprio arquivo
    existentes = {(c.uf.upper(), (c.municipio or "").strip().lower())
                  for c in repo.list_by_empresa(empresa_id)}
    vistos: set[tuple] = set()
    importados = 0
    ignorados = 0
    for row in ws.iter_rows(min_row=2, values_only=True):
        if all(c is None for c in row):
            continue
        uf = str(row[col["uf"]] or "").strip().upper()
        municipio = str(row[col["municipio"]] or "").strip() if "municipio" in col else ""
        cod = str(row[col["hub_codigo"]] or "").strip().upper()
        if macro_por_uf(uf) is None or not cod:
            ignorados += 1  # UF inválida ou hub vazio
            continue
        hub = hub_repo.get_by_codigo(cod)
        if not hub:
            ignorados += 1  # hub inexistente
            continue
        chave = (uf, municipio.lower())
        if chave in existentes or chave in vistos:
            ignorados += 1  # duplicado (banco ou planilha)
            continue
        vistos.add(chave)
        repo.create(ClusterCliente(
            empresa_id=empresa_id, uf=uf, municipio=municipio, hub_id=hub.id,
        ))
        importados += 1

    return {"importados": importados, "ignorados": ignorados}


@clusters_router.put("/{empresa_id}/clusters/{cluster_id}", response_model=ClusterClienteOut)
def atualizar_cluster(
    empresa_id: int,
    cluster_id: int,
    payload: ClusterClienteIn,
    _=Depends(verificar_acesso_empresa),
    repo=Depends(get_cluster_repo),
    hub_repo=Depends(get_hub_repo),
):
    atual = repo.get(cluster_id)
    if not atual or atual.empresa_id != empresa_id:
        raise HTTPException(404, "Cluster não encontrado para esta empresa.")
    if not hub_repo.get(payload.hub_id):
        raise HTTPException(422, "Hub inválido.")
    cluster = ClusterCliente(empresa_id=empresa_id, **payload.model_dump())
    return repo.update(cluster_id, cluster)


@clusters_router.delete("/{empresa_id}/clusters/{cluster_id}", status_code=204)
def remover_cluster(
    empresa_id: int,
    cluster_id: int,
    _=Depends(verificar_acesso_empresa),
    repo=Depends(get_cluster_repo),
):
    atual = repo.get(cluster_id)
    if not atual or atual.empresa_id != empresa_id:
        raise HTTPException(404, "Cluster não encontrado para esta empresa.")
    repo.delete(cluster_id)


# ─────────────── Referências de corredor (global, admin) ───────────────
corredor_router = APIRouter(prefix="/benchmarks-corredor", tags=["Benchmark OD — Referências"])


@corredor_router.get("", response_model=list[BenchmarkCorredorOut])
def listar_corredores(_=Depends(get_current_user), repo=Depends(get_benchmark_corredor_repo)):
    return repo.list()


@corredor_router.put("", response_model=BenchmarkCorredorOut)
def upsert_corredor(
    payload: BenchmarkCorredorIn,
    _=Depends(get_current_superuser),
    repo=Depends(get_benchmark_corredor_repo),
):
    """Cria ou atualiza a referência de um corredor (upsert por par de hubs)."""
    return repo.upsert(BenchmarkCorredor(**payload.model_dump()))


@corredor_router.delete("/{corredor_id}", status_code=204)
def remover_corredor(
    corredor_id: int,
    _=Depends(get_current_superuser),
    repo=Depends(get_benchmark_corredor_repo),
):
    if not repo.delete(corredor_id):
        raise HTTPException(404, "Referência de corredor não encontrada.")
