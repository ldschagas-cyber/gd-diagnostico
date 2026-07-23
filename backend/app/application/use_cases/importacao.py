"""Caso de uso: importação de CT-e (RF008) e Excel (RF010).

Regras RF008:
- Validar tomador contra matriz e filiais cadastradas.
- Ignorar CT-es sem vínculo com a empresa selecionada.
- Evitar duplicidade pela chave do CT-e.
"""
from datetime import date
from typing import List, Tuple

from app.application.dtos import ResultadoImportacao
from app.core.config import settings
from app.core.logging_config import get_logger
from app.domain.entities import CTe, NFe, Transportadora
from app.domain.repositories import (
    ICTeRepository,
    IFilialRepository,
    ITransportadoraRepository,
)
from app.infrastructure.parsers.cte_parser import parse_cte_xml
from app.infrastructure.parsers.excel_parser import LinhaExcel, parse_excel
from app.infrastructure.parsers.macro_regiao import macro_por_uf

logger = get_logger(__name__)


class ImportarCTeUseCase:
    def __init__(
        self,
        cte_repo: ICTeRepository,
        filial_repo: IFilialRepository,
        transp_repo: ITransportadoraRepository,
    ):
        self.cte_repo = cte_repo
        self.filial_repo = filial_repo
        self.transp_repo = transp_repo

    def importar_xmls(
        self, empresa_id: int, arquivos: List[Tuple[str, bytes]]
    ) -> ResultadoImportacao:
        resultado = ResultadoImportacao(total_processados=len(arquivos))

        if len(arquivos) > settings.MAX_CTE_BATCH:
            raise ValueError(
                f"Lote excede o limite de {settings.MAX_CTE_BATCH} CT-es (RNF006)."
            )

        cnpjs_empresa = set(self.filial_repo.list_cnpjs_da_empresa(empresa_id))
        if not cnpjs_empresa:
            raise ValueError(
                "Empresa selecionada não possui CNPJ de matriz/filiais cadastrados."
            )

        # Parse de todos os arquivos primeiro, para poder checar duplicidade
        # contra o banco com UMA única query (em vez de uma por arquivo).
        parseados: list = []
        for nome, conteudo in arquivos:
            try:
                parsed = parse_cte_xml(conteudo)
            except Exception as exc:  # noqa: BLE001
                resultado.erros.append(f"{nome}: {exc}")
                continue
            if not parsed.chave:
                resultado.erros.append(f"{nome}: chave do CT-e não encontrada.")
                continue
            parseados.append(parsed)

        chaves_existentes = self.cte_repo.get_chaves_existentes(
            [p.chave for p in parseados]
        )

        # Cache de resolução de transportadora dentro do lote — evita repetir
        # a query (ou o INSERT de auto-criação) para a mesma transportadora
        # em cada arquivo do lote.
        cache_transportadora: dict[str, int | None] = {}

        novos: List[CTe] = []
        chaves_no_lote: set[str] = set()

        for parsed in parseados:
            # Regra: validar tomador contra matriz/filiais
            if parsed.tomador_cnpj not in cnpjs_empresa:
                resultado.ignorados_sem_vinculo += 1
                logger.info(
                    "CT-e %s ignorado: tomador %s sem vínculo com empresa %s",
                    parsed.chave, parsed.tomador_cnpj, empresa_id,
                )
                continue

            # Regra: evitar duplicidade (no lote e no banco)
            if parsed.chave in chaves_no_lote or parsed.chave in chaves_existentes:
                resultado.duplicados += 1
                continue

            transportadora_id = self._resolver_transportadora_cacheado(
                parsed, empresa_id, cache_transportadora
            )

            cte = CTe(
                empresa_id=empresa_id,
                transportadora_id=transportadora_id,
                chave=parsed.chave,
                numero=parsed.numero,
                serie=parsed.serie,
                data_emissao=parsed.data_emissao,
                tomador_cnpj=parsed.tomador_cnpj,
                destinatario_cnpj=parsed.destinatario_cnpj,
                destinatario_nome=parsed.destinatario_nome,
                peso=parsed.peso,
                valor_frete=parsed.valor_frete,
                valor_mercadoria=parsed.valor_mercadoria,
                municipio_origem=parsed.municipio_origem,
                uf_origem=parsed.uf_origem,
                municipio_destino=parsed.municipio_destino,
                uf_destino=parsed.uf_destino,
                macro_regiao_destino=macro_por_uf(parsed.uf_destino),
                origem_importacao="XML",
                composicao_frete=parsed.composicao,
                nfes=[NFe(chave=ch) for ch in parsed.chaves_nfe],
            )
            novos.append(cte)
            chaves_no_lote.add(parsed.chave)

        if novos:
            resultado.importados = self.cte_repo.bulk_create(novos)

        logger.info(
            "Importação XML empresa=%s: %s importados, %s ignorados, %s duplicados, %s erros",
            empresa_id, resultado.importados, resultado.ignorados_sem_vinculo,
            resultado.duplicados, len(resultado.erros),
        )
        return resultado

    def importar_excel(
        self, empresa_id: int, conteudo: bytes, atualizar_existentes: bool = False
    ) -> ResultadoImportacao:
        linhas, sem_identificador = parse_excel(conteudo)
        resultado = ResultadoImportacao(
            total_processados=len(linhas), sem_identificador=sem_identificador
        )

        novos: List[CTe] = []
        for i, linha in enumerate(linhas, start=2):  # linha 1 = cabeçalho
            try:
                transportadora_id = self._resolver_transportadora_por_nome(
                    linha.transportadora, empresa_id
                )
                # Número do documento: usa o CT-e quando informado na planilha;
                # caso contrário mantém a NF (comportamento atual preservado).
                numero_doc = linha.cte or linha.nota_fiscal

                entidade = CTe(
                    empresa_id=empresa_id,
                    transportadora_id=transportadora_id,
                    chave="",  # definida abaixo (apenas no caminho de criação)
                    numero=numero_doc,
                    # Data Emissão é coluna obrigatória na planilha (fonte real
                    # da competência do CT-e). O fallback para Data
                    # Embarque/Saída/Entrega e, por fim, para a data da
                    # importação só cobre planilhas antigas (pré-existentes)
                    # que ainda não têm a coluna — evita CT-e com
                    # data_emissao nula, que ficaria invisível em todo
                    # indicador/filtro por período (base por competência,
                    # Dashboard, DLG etc.).
                    data_emissao=linha.data_emissao or linha.data_embarque
                    or linha.data_saida or linha.data_entrega or date.today(),
                    tomador_cnpj=linha.tomador_cnpj,
                    destinatario_cnpj=linha.destinatario_cnpj,
                    destinatario_nome=linha.destinatario_nome,
                    peso=linha.peso,
                    valor_frete=linha.valor_frete,
                    valor_mercadoria=linha.valor_mercadoria,
                    municipio_origem=linha.cidade_origem,
                    uf_origem=linha.uf_origem,
                    municipio_destino=linha.cidade_destino,
                    uf_destino=linha.uf_destino,
                    macro_regiao_destino=macro_por_uf(linha.uf_destino),
                    data_saida=linha.data_saida,
                    data_entrega=linha.data_entrega,
                    origem_importacao="EXCEL",
                    composicao_frete=linha.composicao,
                    nfes=[NFe(
                        chave="", numero=linha.nota_fiscal,
                        valor_mercadoria=linha.valor_mercadoria, peso=linha.peso,
                        municipio_destino=linha.cidade_destino,
                    )],
                )

                # Opção 2: atualizar registro já existente (mesma empresa + NF/CT-e).
                if atualizar_existentes:
                    existente_id = self.cte_repo.buscar_excel_existente(
                        empresa_id, linha.nota_fiscal, linha.cte
                    )
                    if existente_id:
                        self.cte_repo.atualizar_importacao_excel(existente_id, entidade)
                        resultado.atualizados += 1
                        continue

                # Opção 1 (padrão): importar como novo registro.
                # Chave sintética inclui empresa_id + NF para evitar colisão entre empresas
                # (duas empresas podem ter NF de mesmo número).
                chave_sintetica = f"EXCEL-{empresa_id}-{linha.nota_fiscal}-{i}"
                if self.cte_repo.get_by_chave(chave_sintetica):
                    resultado.duplicados += 1
                    continue
                entidade.chave = chave_sintetica
                novos.append(entidade)
            except Exception as exc:  # noqa: BLE001
                resultado.erros.append(f"Linha {i}: {exc}")

        if novos:
            resultado.importados = self.cte_repo.bulk_create(novos)
        logger.info(
            "Importação Excel empresa=%s: %s importados, %s atualizados, "
            "%s sem identificador (NF/CT-e em branco), %s erros",
            empresa_id, resultado.importados, resultado.atualizados,
            resultado.sem_identificador, len(resultado.erros),
        )
        return resultado

    def _resolver_transportadora_cacheado(
        self, parsed: "CTeParseResult", empresa_id: int, cache: dict[str, int | None]
    ) -> int | None:
        """Envolve `_resolver_transportadora` com um cache por lote.

        Lotes grandes costumam repetir a mesma transportadora em muitos
        arquivos; sem cache, cada arquivo dispararia uma query (e possível
        INSERT de auto-criação) redundante para a mesma transportadora.
        """
        chave_cache = f"cnpj:{parsed.transportadora_cnpj}" if parsed.transportadora_cnpj \
            else f"nome:{(parsed.transportadora_nome or '').strip().lower()}"
        if chave_cache in cache:
            return cache[chave_cache]
        resultado = self._resolver_transportadora(parsed, empresa_id)
        cache[chave_cache] = resultado
        return resultado

    def _resolver_transportadora(self, parsed: "CTeParseResult", empresa_id: int) -> int | None:
        """Resolve (ou auto-cria) transportadora no escopo da empresa.

        Busca primeiro por (CNPJ + empresa_id). Se não encontrar, cria nova
        transportadora já com o cadastro completo extraído do XML (razão
        social, CNPJ, endereço, cidade, UF, CEP, telefone) — evolução v6.11.
        Isso garante isolamento entre clientes.
        """
        cnpj = parsed.transportadora_cnpj
        nome = parsed.transportadora_nome
        if cnpj:
            t = self.transp_repo.get_by_cnpj_empresa(cnpj, empresa_id)
            if t:
                return t.id
            criada = self.transp_repo.create(
                Transportadora(
                    empresa_id=empresa_id, razao_social=nome or cnpj, cnpj=cnpj,
                    endereco=parsed.transportadora_endereco,
                    cidade=parsed.transportadora_cidade,
                    uf=parsed.transportadora_uf,
                    cep=parsed.transportadora_cep,
                    telefone=parsed.transportadora_telefone,
                )
            )
            return criada.id
        return self._resolver_transportadora_por_nome(nome, empresa_id)

    def _resolver_transportadora_por_nome(self, nome: str, empresa_id: int) -> int | None:
        """Busca por nome dentro do escopo da empresa. Cria se não existir."""
        if not nome:
            return None
        nome_norm = nome.strip().lower()
        for t in self.transp_repo.list_by_empresa(empresa_id, limit=1000):
            if t.razao_social.strip().lower() == nome_norm or \
               t.nome_fantasia.strip().lower() == nome_norm:
                return t.id
        criada = self.transp_repo.create(
            Transportadora(empresa_id=empresa_id, razao_social=nome)
        )
        return criada.id
