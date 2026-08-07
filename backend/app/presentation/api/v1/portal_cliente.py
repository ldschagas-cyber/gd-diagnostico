"""Router do Portal do Cliente (v6.18.0) — primeiro recorte do Portal do Cliente.

Autenticação própria (cookies `gd_frete_cliente_*`, claim aud=portal_cliente
— nunca aceitos pela sessão interna nem vice-versa). Toda leitura reaproveita
os use cases já existentes do motor analítico (ScoreLogisticoUseCase,
BenchmarkUseCase, RecomendacoesUseCase) — nenhum cálculo novo. O único
endpoint de escrita ("priorizar") grava numa tabela desacoplada, sem alterar
nenhum dado do motor. Ver Especificação Técnica v6.18.0 (docs/specs/v6.18.0/)
para o desenho completo e os 2 ajustes de escopo (§3.8) refletidos abaixo.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.application.use_cases.benchmark import BenchmarkUseCase
from app.application.use_cases.diagnostico import DiagnosticoUseCase
from app.application.use_cases.portal_auth import PortalAuthUseCase
from app.application.use_cases.recomendacoes import RecomendacoesUseCase
from app.application.use_cases.score_logistico import ScoreLogisticoUseCase
from app.core.database import get_db
from app.core.logging_config import get_logger
from app.core.security import (
    CLIENTE_REFRESH_COOKIE_NAME,
    decode_cliente_refresh_token,
    definir_cookie_cliente_access,
    definir_cookie_cliente_refresh,
    limpar_cookies_cliente_auth,
)
from app.infrastructure.database.repositories import PortalOportunidadeFlagRepository
from app.presentation.api.dependencies import (
    get_benchmark_repo,
    get_cliente_portal_user_repo,
    get_cte_repo,
    get_current_cliente_user,
    get_empresa_repo,
    get_meta_nacional_repo,
    get_meta_regional_repo,
    get_transportadora_repo,
)
from app.presentation.schemas import RefreshRequest, Token
from app.presentation.schemas.portal_schemas import (
    PortalBenchmarkRegiaoOut,
    PortalClienteUserOut,
    PortalCustoRegiaoOut,
    PortalDashboardOut,
    PortalEconomiaRegiaoOut,
    PortalEvolucaoItemOut,
    PortalKpisOut,
    PortalOportunidadeOut,
    PortalPlanoAcaoItemOut,
    PortalPotencialEconomiaOut,
    PortalResumoItemOut,
)

router = APIRouter(prefix="/portal", tags=["Portal do Cliente"])
logger = get_logger(__name__)
limiter = Limiter(key_func=get_remote_address)

# Prioridade real (CRITICA/ALTA/MEDIA/BAIXA, RecomendacaoModel) → 3 níveis do
# Portal (o protótipo só tem alta/média/baixa) — CRITICA e ALTA colapsam em
# "alta", nunca escondendo a mais severa.
_MAPA_PRIORIDADE = {"CRITICA": "alta", "ALTA": "alta", "MEDIA": "media", "BAIXA": "baixa"}
# Status real (ABERTA/EM_ANDAMENTO/CONCLUIDA/DESCARTADA) → 3 estados do Portal.
# DESCARTADA é filtrada antes de chegar aqui (não faz sentido mostrar ao cliente).
_MAPA_STATUS = {"ABERTA": "pendente", "EM_ANDAMENTO": "andamento", "CONCLUIDA": "concluido"}


def _build_benchmark_uc(
    cte_repo, empresa_repo, transp_repo, meta_nac, meta_reg, bench_repo, db,
) -> BenchmarkUseCase:
    """Mesma montagem de `_build_uc` em benchmark_analise.py — sem
    BenchmarkODUseCase (opcional, não usado pelo Portal nesta versão)."""
    diag = DiagnosticoUseCase(cte_repo, empresa_repo, transp_repo, meta_nac, meta_reg)
    return BenchmarkUseCase(diag, cte_repo, bench_repo, benchmark_od_uc=None, db=db)


def _deps_benchmark(
    cte_repo=Depends(get_cte_repo),
    empresa_repo=Depends(get_empresa_repo),
    transp_repo=Depends(get_transportadora_repo),
    meta_nac=Depends(get_meta_nacional_repo),
    meta_reg=Depends(get_meta_regional_repo),
    bench_repo=Depends(get_benchmark_repo),
    db: Session = Depends(get_db),
) -> BenchmarkUseCase:
    return _build_benchmark_uc(cte_repo, empresa_repo, transp_repo, meta_nac, meta_reg, bench_repo, db)


# ═══════════════════════════ Autenticação ═══════════════════════════

@router.post("/auth/login", response_model=Token)
@limiter.limit("10/minute")
def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    cliente_repo=Depends(get_cliente_portal_user_repo),
):
    """Login via OAuth2 password flow. 'username' = e-mail do usuário-cliente."""
    uc = PortalAuthUseCase(cliente_repo)
    user = uc.authenticate(form_data.username, form_data.password)
    if not user:
        logger.warning("Tentativa de login (Portal do Cliente) falhou para %s", form_data.username)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="E-mail ou senha incorretos")
    logger.info("Login bem-sucedido (Portal do Cliente): %s", user.email)
    access, refresh = uc.gerar_tokens(user)
    definir_cookie_cliente_access(response, access)
    definir_cookie_cliente_refresh(response, refresh)
    cliente_repo.atualizar_ultimo_acesso(user.id)
    return Token(access_token=access, refresh_token=refresh)


@router.post("/auth/refresh", response_model=Token)
@limiter.limit("30/minute")
def refresh_token(
    request: Request,
    response: Response,
    payload: Optional[RefreshRequest] = None,
    cliente_repo=Depends(get_cliente_portal_user_repo),
):
    refresh = request.cookies.get(CLIENTE_REFRESH_COOKIE_NAME) or (payload.refresh_token if payload else None)
    sub = decode_cliente_refresh_token(refresh) if refresh else None
    if sub is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token inválido ou expirado")
    user = cliente_repo.get(int(sub))
    if user is None or not user.ativo:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário inválido")
    from app.core.security import create_cliente_access_token
    novo_access = create_cliente_access_token(subject=user.id)
    definir_cookie_cliente_access(response, novo_access)
    return Token(access_token=novo_access)


@router.post("/auth/logout", status_code=204)
def logout(response: Response):
    limpar_cookies_cliente_auth(response)


@router.get("/auth/me", response_model=PortalClienteUserOut)
def me(
    current=Depends(get_current_cliente_user),
    empresa_repo=Depends(get_empresa_repo),
):
    empresa = empresa_repo.get(current.empresa_id)
    return PortalClienteUserOut(
        id=current.id, empresa_id=current.empresa_id, nome=current.nome, email=current.email,
        empresa_nome=(empresa.nome_fantasia or empresa.razao_social) if empresa else "",
    )


# ═══════════════════════════ Dashboard Executivo ═══════════════════════════

@router.get("/dashboard", response_model=PortalDashboardOut)
def dashboard(
    current=Depends(get_current_cliente_user),
    empresa_repo=Depends(get_empresa_repo),
    benchmark_uc: BenchmarkUseCase = Depends(_deps_benchmark),
    db: Session = Depends(get_db),
):
    """Agregado do Dashboard Executivo — todo campo vem de um use case já
    existente para o analista (Especificação Técnica v6.18.0 §3.6)."""
    empresa_id = current.empresa_id  # nunca de path/query — ver §3.4
    empresa = empresa_repo.get(empresa_id)
    empresa_nome = (empresa.nome_fantasia or empresa.razao_social) if empresa else ""

    exec_dash = benchmark_uc.dashboard_executivo(empresa_id)
    economia = benchmark_uc.potencial_economia(empresa_id)
    score = ScoreLogisticoUseCase(db).ultimo(empresa_id)
    recomendacoes = [r for r in RecomendacoesUseCase(db).listar(empresa_id) if r.status != "DESCARTADA"]

    # KPIs
    performance = score.score_total if score else 0.0
    regioes_com_dado = exec_dash.regionais
    aderencia_pct = (
        100.0 * sum(1 for r in regioes_com_dado if r.frete_kg.dentro_faixa) / len(regioes_com_dado)
        if regioes_com_dado else 0.0
    )
    # "Rotas acima do benchmark": o motor de Benchmark não tem uma dimensão
    # "rota" (essa dimensão existe no módulo DLG, não neste). Substituição
    # honesta e documentada (Especificação Técnica §3.6): contagem de
    # macrorregiões fora da faixa de benchmark.
    rotas_acima = sum(1 for r in regioes_com_dado if not r.frete_kg.dentro_faixa)
    kpis = PortalKpisOut(
        economia_potencial_anual=economia.proj_anual,
        aderencia_mercado_pct=round(aderencia_pct, 1),
        performance_logistica=performance,
        rotas_acima_benchmark=rotas_acima,
        transportadoras_monitoradas=len(exec_dash.transportadoras),
    )

    # Resumo executivo (semáforo)
    resumo = [
        PortalResumoItemOut(
            chave="performance", titulo="Performance Logística",
            status="verde" if performance >= 70 else ("amarelo" if performance >= 50 else "vermelho"),
            valor=(score.classificacao if score else "Sem dado calculado ainda"),
        ),
        PortalResumoItemOut(
            chave="benchmark", titulo="Benchmark Mercado",
            status="verde" if aderencia_pct >= 90 else "amarelo",
            valor=f"{aderencia_pct:.0f}% de aderência ao mercado",
        ),
        PortalResumoItemOut(
            chave="economia", titulo="Economia Potencial Identificada",
            status="vermelho",  # potencial > 0 é sempre uma oportunidade em aberto, por definição
            valor=f"R$ {economia.proj_anual:,.0f}/ano".replace(",", "."),
        ),
    ]
    total_plano = len(recomendacoes)
    concluidas = sum(1 for r in recomendacoes if r.status == "CONCLUIDA")
    pct_concluido = (concluidas / total_plano) if total_plano else 0.0
    resumo.append(PortalResumoItemOut(
        chave="plano_acao", titulo="Plano de Ação",
        status="verde" if pct_concluido >= 0.7 else "amarelo",
        valor=f"{concluidas} de {total_plano} ações concluídas",
    ))

    return PortalDashboardOut(
        empresa_nome=empresa_nome,
        resumo=resumo,
        kpis=kpis,
        evolucao_frete=[
            PortalEvolucaoItemOut(mes=e.mes, custo_real_kg=e.frete_rs_kg) for e in exec_dash.evolucao
        ],
        # Linha de referência única (benchmark nacional atual) — não existe
        # série histórica de benchmark por mês hoje; ver Especificação
        # Técnica v6.18.0 §3.6.
        referencia_mercado_kg=exec_dash.benchmark_nacional_kg,
        benchmark_mercado=[
            PortalBenchmarkRegiaoOut(
                regiao=r.macro_regiao, valor_empresa_kg=r.frete_kg.valor,
                valor_mercado_kg=r.frete_kg.benchmark_medio,
            ) for r in regioes_com_dado
        ],
        custo_por_regiao=[
            PortalCustoRegiaoOut(regiao=r.macro_regiao, custo_kg=r.frete_kg.valor) for r in regioes_com_dado
        ],
        potencial_economia=PortalPotencialEconomiaOut(
            total_anual=economia.proj_anual,
            por_regiao=[
                PortalEconomiaRegiaoOut(regiao=r.macro_regiao, valor=r.economia) for r in economia.por_regiao
            ],
        ),
        plano_acao=[
            PortalPlanoAcaoItemOut(
                id=r.id, titulo=r.titulo, categoria=r.indicador or "Geral",
                status=_MAPA_STATUS.get(r.status, "pendente"),
            ) for r in recomendacoes
        ],
        plano_acao_concluidas=concluidas,
        plano_acao_total=total_plano,
    )


# ═══════════════════════════ Oportunidades Prioritárias ═══════════════════════════

@router.get("/oportunidades", response_model=list[PortalOportunidadeOut])
def oportunidades(
    current=Depends(get_current_cliente_user),
    db: Session = Depends(get_db),
):
    empresa_id = current.empresa_id
    recomendacoes = [r for r in RecomendacoesUseCase(db).listar(empresa_id) if r.status != "DESCARTADA"]
    recomendacoes.sort(key=lambda r: r.economia_estimada or 0, reverse=True)
    flag_repo = PortalOportunidadeFlagRepository(db)
    priorizadas = flag_repo.mapa_priorizadas([r.id for r in recomendacoes], current.id)
    return [
        PortalOportunidadeOut(
            id=r.id, titulo=r.titulo, descricao=r.descricao, categoria=r.indicador or "Geral",
            prioridade=_MAPA_PRIORIDADE.get(r.prioridade, "media"),
            status=_MAPA_STATUS.get(r.status, "pendente"),
            impacto_estimado=r.economia_estimada or 0.0,
            priorizada_pelo_cliente=priorizadas.get(r.id, False),
        )
        for r in recomendacoes
    ]


@router.patch("/oportunidades/{recomendacao_id}/priorizar")
def priorizar_oportunidade(
    recomendacao_id: int,
    current=Depends(get_current_cliente_user),
    db: Session = Depends(get_db),
):
    """Alterna o estado "priorizada pelo cliente". Não altera nenhum dado do
    motor analítico (grava só em `portal_oportunidade_flags`, ver §3.7)."""
    from app.infrastructure.database.repositories import RecomendacaoRepository
    rec = next(
        (r for r in RecomendacaoRepository(db).listar(current.empresa_id) if r.id == recomendacao_id), None
    )
    if rec is None:
        raise HTTPException(status_code=404, detail="Oportunidade não encontrada")
    novo_estado = PortalOportunidadeFlagRepository(db).alternar(
        recomendacao_id=recomendacao_id, empresa_id=current.empresa_id, cliente_portal_user_id=current.id,
    )
    return {"id": recomendacao_id, "priorizada_pelo_cliente": novo_estado}
