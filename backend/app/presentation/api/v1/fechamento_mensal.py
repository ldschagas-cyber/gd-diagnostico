"""Router do Fechamento de Custo de Frete (fechamento mensal), por empresa-cliente.

Mesmo padrão de acesso de `metas.py`: leitura exige vínculo com a empresa
(qualquer papel); escrita (salvar/fechar/reabrir) bloqueia o papel
VISUALIZADOR.
"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.application.use_cases.fechamento_mensal import FechamentoMensalUseCase
from app.presentation.api.dependencies import (
    bloquear_visualizador,
    get_db,
    verificar_acesso_empresa,
)
from app.presentation.schemas import (
    FechamentoAcaoIn,
    FechamentoHistoricoItemOut,
    FechamentoMensalIn,
    FechamentoMensalOut,
)

router = APIRouter(prefix="/empresas/{empresa_id}/fechamento-mensal", tags=["Fechamento de Custo de Frete"])


def _uc(db: Session = Depends(get_db)) -> FechamentoMensalUseCase:
    return FechamentoMensalUseCase(db)


def _competencia_atual() -> str:
    hoje = date.today()
    return f"{hoje.year}-{hoje.month:02d}"


@router.get("", response_model=FechamentoMensalOut)
def obter_fechamento(
    empresa_id: int,
    competencia: str | None = None,
    _=Depends(verificar_acesso_empresa),
    uc: FechamentoMensalUseCase = Depends(_uc),
):
    return uc.obter(empresa_id, competencia or _competencia_atual())


@router.put("", response_model=FechamentoMensalOut)
def salvar_fechamento(
    empresa_id: int,
    payload: FechamentoMensalIn,
    _ac=Depends(verificar_acesso_empresa),
    _=Depends(bloquear_visualizador),
    uc: FechamentoMensalUseCase = Depends(_uc),
):
    dados = payload.model_dump(exclude={"competencia"})
    try:
        return uc.salvar(empresa_id, payload.competencia, dados)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/fechar", response_model=FechamentoMensalOut)
def fechar_mes(
    empresa_id: int,
    payload: FechamentoAcaoIn,
    _ac=Depends(verificar_acesso_empresa),
    _=Depends(bloquear_visualizador),
    uc: FechamentoMensalUseCase = Depends(_uc),
):
    try:
        return uc.fechar(empresa_id, payload.competencia)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/reabrir", response_model=FechamentoMensalOut)
def reabrir_mes(
    empresa_id: int,
    payload: FechamentoAcaoIn,
    _ac=Depends(verificar_acesso_empresa),
    _=Depends(bloquear_visualizador),
    uc: FechamentoMensalUseCase = Depends(_uc),
):
    try:
        return uc.reabrir(empresa_id, payload.competencia)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/historico", response_model=list[FechamentoHistoricoItemOut])
def historico_fechamentos(
    empresa_id: int,
    limite: int = 13,
    _=Depends(verificar_acesso_empresa),
    uc: FechamentoMensalUseCase = Depends(_uc),
):
    return uc.historico(empresa_id, limite)
