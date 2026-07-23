"""Router de importação de CT-e XML (RF008) e Excel (RF010).

Limites de upload (segurança):
  - XML:   máx 10 MB por arquivo, máx 500 arquivos por lote
  - Excel: máx 20 MB por arquivo
  - MIME type validado antes de processar
"""
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response

from app.application.use_cases.cancelamento import CancelamentoCteUseCase
from app.application.use_cases.carta_correcao import CartaCorrecaoCteUseCase
from app.application.use_cases.dlg import DlgUseCase
from app.application.use_cases.importacao import ImportarCTeUseCase
from app.core.config import settings
from app.infrastructure.parsers.excel_parser import gerar_modelo_excel
from app.presentation.api.dependencies import (
    bloquear_visualizador,
    get_cte_repo,
    get_current_user,
    get_db,
    require_admin,
    verificar_acesso_empresa,
    get_empresa_repo,
    get_filial_repo,
    get_transportadora_repo,
)
from app.application.dtos import ResultadoImportacao
from app.presentation.schemas import (
    CancelamentoLogOut,
    CompetenciaCteOut,
    ContagemImportacaoOut,
    CteListaPaginadaOut,
    ExcluirCtesIn,
    ResultadoCancelamentoOut,
    ResultadoExclusaoOut,
    ResultadoImportacaoCteOut,
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


def _classificar_xml(conteudo: bytes) -> str:
    """Classifica um XML do lote de upload em 'CTE', 'EVENTO_CANCELAMENTO' ou
    'EVENTO_CCE' (Carta de Correção, v6.11).

    Detecção tolerante por presença de tag (mesmo critério dos parsers, que
    também ignoram namespace/envelope): um XML de evento sempre contém
    <infEvento>, enquanto um CT-e contém <infCte>. Entre os eventos, a tag
    <tpEvento>110110</tpEvento> identifica uma Carta de Correção; qualquer
    outro tpEvento (110111 = cancelamento, ou algum não suportado) segue para
    o caminho de cancelamento e é rejeitado pelo parser com mensagem clara
    quando não for de fato um cancelamento (comportamento já existente).
    Arquivos sem nenhuma das duas tags seguem para o caminho de CT-e e são
    rejeitados pelo parser correspondente.
    """
    if b"infEvento" not in conteudo:
        return "CTE"
    if b"<tpEvento>110110</tpEvento>" in conteudo:
        return "EVENTO_CCE"
    return "EVENTO_CANCELAMENTO"


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


@router.post("/cte/{empresa_id}", response_model=ResultadoImportacaoCteOut)
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
    """Upload de múltiplos XMLs de CT-e (RF008), incluindo cancelamento e CCe.

    O lote pode misturar XMLs de CT-e, XMLs de evento de cancelamento
    (tpEvento 110111) e XMLs de Carta de Correção (CCe, tpEvento 110110) —
    cada arquivo é classificado automaticamente pelo conteúdo e roteado para
    o caso de uso correspondente (MELHORIA v6.11). CCe nunca altera o CT-e
    automaticamente — é apenas registrada no log para revisão manual, pois a
    correção pode incidir sobre campo que a própria CCe não deveria alterar
    (ex.: quantidade/peso de carga, vedado pelo Art. 58-B do Convênio
    SINIEF 06/89).

    Limites: máx 500 arquivos por lote, 10 MB por arquivo.
    """
    if not empresa_repo.get(empresa_id):
        raise HTTPException(404, "Empresa não encontrada")
    if len(arquivos) > MAX_XML_BATCH:
        raise HTTPException(400, f"Lote excede o limite de {MAX_XML_BATCH} arquivos.")

    conteudos_cte: list[tuple[str, bytes]] = []
    conteudos_cancelamento: list[tuple[str, bytes]] = []
    conteudos_cce: list[tuple[str, bytes]] = []
    for f in arquivos:
        dados = await _ler_com_limite(f, MAX_XML_BYTES)
        nome = f.filename or "arquivo.xml"
        _validar_xml(nome, dados)
        tipo = _classificar_xml(dados)
        if tipo == "EVENTO_CCE":
            conteudos_cce.append((nome, dados))
        elif tipo == "EVENTO_CANCELAMENTO":
            conteudos_cancelamento.append((nome, dados))
        else:
            conteudos_cte.append((nome, dados))

    if conteudos_cte:
        uc = _build_uc(cte_repo, filial_repo, transp_repo)
        try:
            resultado_importacao = uc.importar_xmls(empresa_id, conteudos_cte)
        except ValueError as exc:
            raise HTTPException(400, str(exc))
    else:
        resultado_importacao = ResultadoImportacao(total_processados=0)

    uc_cancelamento = CancelamentoCteUseCase(cte_repo)
    resultado_cancelamento = uc_cancelamento.importar_eventos(empresa_id, conteudos_cancelamento)

    uc_carta_correcao = CartaCorrecaoCteUseCase(cte_repo)
    resultado_carta_correcao = uc_carta_correcao.importar_eventos(empresa_id, conteudos_cce)

    return {
        "importacao": resultado_importacao,
        "cancelamento": resultado_cancelamento,
        "carta_correcao": resultado_carta_correcao,
    }


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


@router.get("/dados/{empresa_id}/ctes", response_model=CteListaPaginadaOut)
def listar_ctes(
    empresa_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    status: str | None = Query(None, description="ATIVO ou CANCELADO — omita para todos."),
    origem: str | None = Query(None, description="XML ou EXCEL — omita para todos."),
    _=Depends(verificar_acesso_empresa),
    cte_repo=Depends(get_cte_repo),
):
    """Lista os CT-es individuais da empresa, paginado, para a grid da tela de
    importação (v6.11). Leitura — disponível a qualquer usuário com acesso à
    empresa, sem exigir perfil administrador.
    """
    status_norm = (status or "").strip().upper() or None
    if status_norm and status_norm not in ("ATIVO", "CANCELADO"):
        raise HTTPException(400, "Status inválido. Use ATIVO, CANCELADO ou omita.")
    origem_norm = (origem or "").strip().upper() or None
    if origem_norm and origem_norm not in ("XML", "EXCEL"):
        raise HTTPException(400, "Origem inválida. Use XML, EXCEL ou omita.")

    itens, total = cte_repo.listar_paginado(
        empresa_id, page=page, page_size=page_size, status=status_norm, origem=origem_norm
    )
    return {"items": itens, "total": total}


@router.delete("/dados/{empresa_id}/ctes", response_model=ResultadoExclusaoOut)
def excluir_ctes_selecionados(
    empresa_id: int,
    payload: ExcluirCtesIn,
    _=Depends(verificar_acesso_empresa),
    __=Depends(require_admin),
    cte_repo=Depends(get_cte_repo),
    db=Depends(get_db),
):
    """Exclui os CT-es selecionados na grid (v6.11), pelos seus ids.

    Operação destrutiva restrita a administrador, mesma convenção de risco de
    `excluir_dados_importados`. Ids que não pertencem à empresa são
    ignorados silenciosamente (isolamento multi-tenant). Reprocessa o DLG em
    seguida para não deixar filial/período com contagem obsoleta.
    """
    if not payload.ids:
        raise HTTPException(400, "Nenhum CT-e selecionado.")
    excluidos = cte_repo.excluir_por_ids(empresa_id, payload.ids)
    if excluidos:
        DlgUseCase(db).limpar_e_reprocessar(empresa_id)
    return {"excluidos": excluidos}


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
    db=Depends(get_db),
):
    """Exclui dados importados da empresa (admin). Operação destrutiva.

    Proteção: o cliente deve informar `confirmar_quantidade` igual à contagem
    atual do escopo selecionado. Se divergir (dados mudaram ou número digitado
    incorreto), a exclusão é recusada sem alterar nada. Reprocessa o DLG em
    seguida para não deixar filial/período com contagem obsoleta.
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
    if excluidos:
        DlgUseCase(db).limpar_e_reprocessar(empresa_id)
    return {"excluidos": excluidos}
