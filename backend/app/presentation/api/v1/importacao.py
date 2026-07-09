"""Router de importação de CT-e XML (RF008) e Excel (RF010).

Limites de upload (segurança):
  - XML:   máx 10 MB por arquivo, máx 500 arquivos por lote
  - Excel: máx 20 MB por arquivo
  - MIME type validado antes de processar
"""
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response

from app.application.use_cases.cancelamento import CancelamentoCteUseCase
from app.application.use_cases.importacao import ImportarCTeUseCase
from app.core.config import settings
from app.infrastructure.parsers.excel_parser import gerar_modelo_excel
from app.presentation.api.dependencies import (
    bloquear_visualizador,
    get_cte_repo,
    get_current_user,
    require_admin,
    verificar_acesso_empresa,
    get_empresa_repo,
    get_filial_repo,
    get_transportadora_repo,
)
from app.presentation.schemas import (
    CancelamentoLogOut,
    CompetenciaCteOut,
    ContagemImportacaoOut,
    ResultadoCancelamentoOut,
    ResultadoExclusaoOut,
    ResultadoImportacaoOut,
)

router = APIRouter(prefix="/importacao", tags=["Importação"])

# ── Limites de upload ─────────────────────────────────────────────────────────
MAX_XML_BYTES  = 10 * 1024 * 1024   # 10 MB por arquivo XML
MAX_XLS_BYTES  = 20 * 1024 * 1024   # 20 MB para planilha Excel
MAX_XML_BATCH  = 500                 # max arquivos por lote

# Assinaturas mágicas (magic bytes) aceitas
_XML_MAGIC  = (b"<?xml", b"\xef\xbb\xbf<?xml")   # UTF-8 BOM opcional
_XLSX_MAGIC = b"PK"                                # ZIP-based Office formats


def _build_uc(cte_repo, filial_repo, transp_repo) -> ImportarCTeUseCase:
    return ImportarCTeUseCase(cte_repo, filial_repo, transp_repo)


def _validar_xml(nome: str, conteudo: bytes) -> None:
    """Valida tamanho e assinatura de um arquivo XML antes de processar."""
    if len(conteudo) > MAX_XML_BYTES:
        raise HTTPException(
            413,
            f"Arquivo '{nome}' excede o limite de {MAX_XML_BYTES // 1024 // 1024} MB.",
        )
    # Verifica se começa com marcador XML (após BOM opcional)
    cabecalho = conteudo.lstrip(b"\xef\xbb\xbf")
    if not cabecalho.startswith(b"<?xml") and not cabecalho.lstrip(b" \t\r\n").startswith(b"<"):
        raise HTTPException(400, f"Arquivo '{nome}' não parece ser um XML válido.")


def _validar_excel(nome: str, conteudo: bytes) -> None:
    """Valida tamanho e assinatura de um arquivo Excel."""
    if len(conteudo) > MAX_XLS_BYTES:
        raise HTTPException(
            413,
            f"Arquivo '{nome}' excede o limite de {MAX_XLS_BYTES // 1024 // 1024} MB.",
        )
    if not conteudo.startswith(_XLSX_MAGIC):
        raise HTTPException(400, f"Arquivo '{nome}' não é um Excel (.xlsx) válido.")


async def _ler_com_limite(arquivo: UploadFile, limite: int) -> bytes:
    """Lê um upload em blocos, abortando assim que ultrapassar o limite (R-08).

    Evita carregar arquivos enormes inteiros em memória: checa o tamanho
    declarado (quando disponível) e, durante a leitura, interrompe no
    primeiro byte acima do limite.
    """
    nome = arquivo.filename or "arquivo"
    # 1) Checagem rápida pelo tamanho declarado pelo cliente, quando houver.
    tamanho_declarado = getattr(arquivo, "size", None)
    if tamanho_declarado is not None and tamanho_declarado > limite:
        raise HTTPException(
            413, f"Arquivo '{nome}' excede o limite de {limite // 1024 // 1024} MB."
        )
    # 2) Leitura em blocos com corte defensivo.
    CHUNK = 1024 * 1024  # 1 MB
    buffer = bytearray()
    while True:
        bloco = await arquivo.read(CHUNK)
        if not bloco:
            break
        buffer.extend(bloco)
        if len(buffer) > limite:
            raise HTTPException(
                413, f"Arquivo '{nome}' excede o limite de {limite // 1024 // 1024} MB."
            )
    return bytes(buffer)


@router.post("/cte/{empresa_id}", response_model=ResultadoImportacaoOut)
async def importar_cte_xml(
    empresa_id: int,
    arquivos: list[UploadFile] = File(...),
    _=Depends(verificar_acesso_empresa),
    __=Depends(bloquear_visualizador),
    empresa_repo=Depends(get_empresa_repo),
    cte_repo=Depends(get_cte_repo),
    filial_repo=Depends(get_filial_repo),
    transp_repo=Depends(get_transportadora_repo),
):
    """Upload de múltiplos XMLs de CT-e (RF008).

    Limites: máx 500 arquivos por lote, 10 MB por arquivo.
    """
    if not empresa_repo.get(empresa_id):
        raise HTTPException(404, "Empresa não encontrada")
    if len(arquivos) > MAX_XML_BATCH:
        raise HTTPException(400, f"Lote excede o limite de {MAX_XML_BATCH} arquivos.")

    conteudos = []
    for f in arquivos:
        dados = await _ler_com_limite(f, MAX_XML_BYTES)
        _validar_xml(f.filename or "arquivo.xml", dados)
        conteudos.append((f.filename or "arquivo.xml", dados))

    uc = _build_uc(cte_repo, filial_repo, transp_repo)
    try:
        resultado = uc.importar_xmls(empresa_id, conteudos)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return resultado


@router.post("/cte/cancelamento/{empresa_id}", response_model=ResultadoCancelamentoOut)
async def importar_evento_cancelamento(
    empresa_id: int,
    arquivos: list[UploadFile] = File(...),
    _=Depends(verificar_acesso_empresa),
    __=Depends(bloquear_visualizador),
    empresa_repo=Depends(get_empresa_repo),
    cte_repo=Depends(get_cte_repo),
):
    """Importa eventos de cancelamento de CT-e via XML oficial (MELHORIA 1).

    Para cada evento: localiza o CT-e pela chave de acesso (no escopo da
    empresa), marca-o como CANCELADO e registra data, protocolo e nº do evento.
    Duplicidades e CT-es inexistentes são registrados no log sem interromper o
    lote. Limites: máx 500 arquivos por lote, 10 MB por arquivo.
    """
    if not empresa_repo.get(empresa_id):
        raise HTTPException(404, "Empresa não encontrada")
    if len(arquivos) > MAX_XML_BATCH:
        raise HTTPException(400, f"Lote excede o limite de {MAX_XML_BATCH} arquivos.")

    conteudos = []
    for f in arquivos:
        dados = await _ler_com_limite(f, MAX_XML_BYTES)
        _validar_xml(f.filename or "evento.xml", dados)
        conteudos.append((f.filename or "evento.xml", dados))

    uc = CancelamentoCteUseCase(cte_repo)
    return uc.importar_eventos(empresa_id, conteudos)


@router.get(
    "/dados/{empresa_id}/cancelamentos",
    response_model=list[CancelamentoLogOut],
)
def listar_log_cancelamentos(
    empresa_id: int,
    _=Depends(verificar_acesso_empresa),
    cte_repo=Depends(get_cte_repo),
):
    """Lista o histórico (log) de eventos de cancelamento importados da empresa,
    do mais recente para o mais antigo. Auditoria completa (RF008 — evolução)."""
    return cte_repo.listar_ocorrencias_cancelamento(empresa_id)


@router.get("/excel/modelo")
def baixar_modelo_excel(_=Depends(get_current_user)):
    """Baixa a planilha modelo de importação (.xlsx) com cabeçalho, exemplo e
    instruções. As colunas coincidem com as reconhecidas na importação Excel.
    """
    conteudo = gerar_modelo_excel()
    return Response(
        content=conteudo,
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": 'attachment; filename="modelo_importacao_frete.xlsx"'
        },
    )


@router.post("/excel/{empresa_id}", response_model=ResultadoImportacaoOut)
async def importar_excel(
    empresa_id: int,
    arquivo: UploadFile = File(...),
    atualizar_existentes: bool = Form(False),
    _=Depends(verificar_acesso_empresa),
    __=Depends(bloquear_visualizador),
    empresa_repo=Depends(get_empresa_repo),
    cte_repo=Depends(get_cte_repo),
    filial_repo=Depends(get_filial_repo),
    transp_repo=Depends(get_transportadora_repo),
):
    """Importação alternativa via Excel quando não há XML (RF010).

    Limite: 20 MB por arquivo.

    Parâmetros:
      - atualizar_existentes: quando True, registros já importados (mesma
        empresa + NF/CT-e) são atualizados em vez de recriados. Default False
        preserva o comportamento original (importa apenas novos).
    """
    if not empresa_repo.get(empresa_id):
        raise HTTPException(404, "Empresa não encontrada")

    conteudo = await _ler_com_limite(arquivo, MAX_XLS_BYTES)
    _validar_excel(arquivo.filename or "planilha.xlsx", conteudo)

    uc = _build_uc(cte_repo, filial_repo, transp_repo)
    try:
        resultado = uc.importar_excel(empresa_id, conteudo, atualizar_existentes)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return resultado


# ── Gestão de dados importados (somente administrador) ────────────────────────

@router.get("/dados/{empresa_id}/contagem", response_model=ContagemImportacaoOut)
def contar_dados_importados(
    empresa_id: int,
    _=Depends(verificar_acesso_empresa),
    __=Depends(require_admin),
    cte_repo=Depends(get_cte_repo),
):
    """Conta os registros importados da empresa, separados por origem (XML/Excel).

    Usado pelo painel administrativo de exclusão para exibir a quantidade
    exata antes de qualquer remoção.
    """
    return cte_repo.contar_por_origem(empresa_id)


@router.get(
    "/dados/{empresa_id}/competencias",
    response_model=list[CompetenciaCteOut],
)
def listar_competencias_cte(
    empresa_id: int,
    _=Depends(verificar_acesso_empresa),
    cte_repo=Depends(get_cte_repo),
):
    """Indicador de base de CT-e: quantidade de CT-es por competência (mês/ano).

    Agrupado pela data de emissão e ordenado do período mais recente para o
    mais antigo. Competências sem registros não são retornadas. Permite ao
    usuário visualizar rapidamente o histórico já existente antes de novas
    importações. Disponível a qualquer usuário com acesso à empresa.
    """
    return cte_repo.contar_por_competencia(empresa_id)


@router.delete("/dados/{empresa_id}", response_model=ResultadoExclusaoOut)
def excluir_dados_importados(
    empresa_id: int,
    confirmar_quantidade: int = Query(
        ..., ge=0,
        description="Quantidade exata de registros a excluir (confirmação obrigatória).",
    ),
    origem: str | None = Query(
        None,
        description="XML, EXCEL ou omitido para excluir todos os importados.",
    ),
    _=Depends(verificar_acesso_empresa),
    __=Depends(require_admin),
    cte_repo=Depends(get_cte_repo),
):
    """Exclui dados importados da empresa (admin). Operação destrutiva.

    Proteção: o cliente deve informar `confirmar_quantidade` igual à contagem
    atual do escopo selecionado. Se divergir (dados mudaram ou número digitado
    incorreto), a exclusão é recusada sem alterar nada.
    """
    origem_norm = (origem or "").strip().upper() or None
    if origem_norm and origem_norm not in ("XML", "EXCEL"):
        raise HTTPException(400, "Origem inválida. Use XML, EXCEL ou omita.")

    contagem = cte_repo.contar_por_origem(empresa_id)
    if origem_norm == "XML":
        esperado = contagem["xml"]
    elif origem_norm == "EXCEL":
        esperado = contagem["excel"]
    else:
        esperado = contagem["total"]

    if confirmar_quantidade != esperado:
        raise HTTPException(
            409,
            f"Confirmação não confere: informado {confirmar_quantidade}, "
            f"registros a excluir {esperado}. Operação cancelada.",
        )

    excluidos = cte_repo.excluir_por_empresa(empresa_id, origem_norm)
    return {"excluidos": excluidos}
