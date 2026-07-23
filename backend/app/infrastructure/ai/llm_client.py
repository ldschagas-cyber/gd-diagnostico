"""Camada de abstração de LLM para o GD Diagnóstico Logístico V4.

Suporta:
- Modo simulado (mock) — sem custo de API, para desenvolvimento sem chaves
- GPT-4.1 (OpenAI) — modelo principal
- Claude Haiku (Anthropic) — modelo de volume
- Tool-Calling — orquestração de ferramentas (números sempre via SQL)
- Registro de uso (tokens, custo) para auditoria e controle de custo

A IA NUNCA calcula números diretamente. Ela interpreta resultados que o
backend já calculou e produz narrativas. Esta regra é estrutural.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


# ─────────────────────────── Tipos ───────────────────────────
class ModeloTipo(str, Enum):
    PRINCIPAL = "principal"   # GPT-4.1 — análise complexa
    VOLUME = "volume"         # Haiku — tarefas simples/volume


# Preços por 1M de tokens (USD) — atualizados Jun/2026
PRECOS = {
    "gpt-4.1":            {"input": 2.00, "output": 8.00},
    "gpt-4o":             {"input": 2.50, "output": 10.00},
    "claude-haiku-4-5":   {"input": 1.00, "output": 5.00},
    "claude-sonnet-4-6":  {"input": 3.00, "output": 15.00},
}


@dataclass
class RespostaLLM:
    """Resultado de uma chamada ao LLM."""
    texto: str
    modelo: str
    tokens_input: int
    tokens_output: int
    custo_usd: float
    custo_brl: float
    simulado: bool
    tool_calls: list[dict] = field(default_factory=list)
    raw: Any = None


def _calcular_custo(modelo: str, tokens_in: int, tokens_out: int) -> tuple[float, float]:
    preco = PRECOS.get(modelo, {"input": 2.0, "output": 8.0})
    usd = (tokens_in / 1_000_000) * preco["input"] + (tokens_out / 1_000_000) * preco["output"]
    brl = usd * settings.USD_TO_BRL
    return round(usd, 6), round(brl, 6)


def _estimar_tokens(texto: str) -> int:
    """Estimativa simples: ~4 caracteres por token."""
    return max(1, len(texto) // 4)


# ─────────────────────────── Cliente ───────────────────────────
class LLMClient:
    """Cliente unificado para os modelos de IA.

    Em modo simulado, retorna respostas mock realistas sem chamar APIs.
    Quando as chaves forem configuradas e AI_SIMULATION_MODE=False, chama
    os modelos reais.
    """

    def __init__(self) -> None:
        self.simulado = not settings.ai_ativa
        self._openai = None
        self._anthropic = None
        if not self.simulado:
            self._inicializar_clientes()

    def _inicializar_clientes(self) -> None:
        """Inicializa os SDKs reais apenas quando há chaves e modo real."""
        try:
            if settings.OPENAI_API_KEY:
                from openai import OpenAI
                self._openai = OpenAI(api_key=settings.OPENAI_API_KEY)
        except ImportError:
            logger.warning("SDK openai não instalado. Rode: pip install openai")
        try:
            if settings.ANTHROPIC_API_KEY:
                from anthropic import Anthropic
                self._anthropic = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        except ImportError:
            logger.warning("SDK anthropic não instalado. Rode: pip install anthropic")

    def _modelo_para(self, tipo: ModeloTipo) -> str:
        return settings.AI_MODEL_PRINCIPAL if tipo == ModeloTipo.PRINCIPAL else settings.AI_MODEL_VOLUME

    # ─────────── Geração de texto (narrativa, diagnóstico, relatório) ───────────
    def gerar(
        self,
        prompt: str,
        *,
        system: str = "",
        tipo: ModeloTipo = ModeloTipo.PRINCIPAL,
        max_tokens: int = 1500,
        contexto_simulado: Optional[dict] = None,
    ) -> RespostaLLM:
        """Gera texto a partir de um prompt. Usa o modelo do tipo indicado."""
        modelo = self._modelo_para(tipo)

        if self.simulado:
            return self._gerar_simulado(prompt, system, modelo, contexto_simulado)

        if modelo.startswith("gpt") and self._openai:
            return self._gerar_openai(prompt, system, modelo, max_tokens)
        if modelo.startswith("claude") and self._anthropic:
            return self._gerar_anthropic(prompt, system, modelo, max_tokens)

        # Sem cliente disponível → fallback simulado
        logger.warning("Modelo %s indisponível; usando modo simulado.", modelo)
        return self._gerar_simulado(prompt, system, modelo, contexto_simulado)

    # ─────────── Embeddings (RAG) ───────────
    def gerar_embedding(self, texto: str) -> list[float]:
        """Gera o vetor de embedding de um texto.

        Em modo simulado, retorna um vetor determinístico derivado do texto
        (mesmo texto → mesmo vetor), permitindo testar a busca semântica sem
        custo. Em modo real, usa a API de embeddings da OpenAI.
        """
        if self.simulado or not self._openai:
            return self._embedding_simulado(texto)
        try:
            resp = self._openai.embeddings.create(
                model=settings.EMBEDDING_MODEL, input=texto[:8000],
            )
            return resp.data[0].embedding
        except Exception as e:  # noqa: BLE001
            logger.warning("Falha ao gerar embedding real (%s); usando simulado.", e)
            return self._embedding_simulado(texto)

    def _embedding_simulado(self, texto: str) -> list[float]:
        """Vetor pseudo-aleatório determinístico baseado no hash do texto.

        Não é semanticamente perfeito, mas textos idênticos geram vetores
        idênticos e textos parecidos compartilham tokens, o que torna a busca
        por similaridade demonstrável em modo simulado.
        """
        import hashlib
        import struct

        dim = settings.EMBEDDING_DIM
        # Combina hash do texto inteiro + hashes de palavras para alguma semântica
        palavras = texto.lower().split()
        vetor = [0.0] * dim
        for palavra in palavras or [texto]:
            h = hashlib.sha256(palavra.encode()).digest()
            for i in range(0, min(len(h), dim * 4), 4):
                idx = (i // 4) % dim
                val = struct.unpack("f", h[i:i + 4])[0]
                if val == val and abs(val) < 1e30:  # ignora NaN/inf
                    vetor[idx] += val
        # Normaliza (vetor unitário) para cosseno estável
        norma = sum(v * v for v in vetor) ** 0.5 or 1.0
        return [v / norma for v in vetor]

    # ─────────── Tool-Calling (assistente logístico) ───────────
    def conversar_com_ferramentas(
        self,
        mensagem: str,
        *,
        ferramentas: list[dict],
        executor: Callable[[str, dict], Any],
        system: str = "",
        historico: Optional[list[dict]] = None,
        tipo: ModeloTipo = ModeloTipo.PRINCIPAL,
        contexto_simulado: Optional[dict] = None,
    ) -> RespostaLLM:
        """Conversa usando Tool-Calling.

        A IA escolhe ferramentas; o `executor` roda a função SQL real e
        devolve o resultado; a IA narra. Números sempre vêm do executor.
        """
        modelo = self._modelo_para(tipo)

        if self.simulado:
            return self._conversar_simulado(mensagem, ferramentas, executor, contexto_simulado)

        if modelo.startswith("gpt") and self._openai:
            return self._conversar_openai(mensagem, ferramentas, executor, system, historico, modelo)
        if modelo.startswith("claude") and self._anthropic:
            return self._conversar_anthropic(mensagem, ferramentas, executor, system, historico, modelo)

        return self._conversar_simulado(mensagem, ferramentas, executor, contexto_simulado)

    # ═══════════════════ Implementações simuladas ═══════════════════
    def _gerar_simulado(self, prompt, system, modelo, contexto) -> RespostaLLM:
        time.sleep(0.3)  # simula latência de rede
        texto = self._mock_narrativa(prompt, contexto or {})
        t_in = _estimar_tokens(system + prompt)
        t_out = _estimar_tokens(texto)
        usd, brl = _calcular_custo(modelo, t_in, t_out)
        return RespostaLLM(
            texto=texto, modelo=f"{modelo} (simulado)", tokens_input=t_in,
            tokens_output=t_out, custo_usd=usd, custo_brl=brl, simulado=True,
        )

    def _conversar_simulado(self, mensagem, ferramentas, executor, contexto) -> RespostaLLM:
        time.sleep(0.3)
        # Heurística simples para escolher ferramenta no modo simulado
        msg = mensagem.lower()
        ferramenta_escolhida = None
        mapa = {
            "mais cara": "get_transportadora_mais_cara",
            "transportadora": "get_transportadora_mais_cara",
            "região": "get_regiao_mais_cara",
            "regiao": "get_regiao_mais_cara",
            "economizar": "get_economia_potencial",
            "economia": "get_economia_potencial",
            "filial": "get_pior_filial",
            "score": "get_score_logistico",
            "nota": "get_score_logistico",
            "oportunidade": "get_oportunidades",
            "bid": "get_recomendacao_bid",
            "setor": "get_benchmark_setorial",
        }
        nomes_disp = {f["name"] if "name" in f else f.get("function", {}).get("name") for f in ferramentas}
        for chave, nome in mapa.items():
            if chave in msg and nome in nomes_disp:
                ferramenta_escolhida = nome
                break

        tool_calls = []
        resultado_tool = None
        if ferramenta_escolhida:
            resultado_tool = executor(ferramenta_escolhida, {})
            tool_calls.append({"ferramenta": ferramenta_escolhida, "resultado": resultado_tool})

        texto = self._mock_resposta_chat(mensagem, ferramenta_escolhida, resultado_tool)
        t_in = _estimar_tokens(mensagem)
        t_out = _estimar_tokens(texto)
        usd, brl = _calcular_custo(self._modelo_para(ModeloTipo.PRINCIPAL), t_in, t_out)
        return RespostaLLM(
            texto=texto, modelo="assistente (simulado)", tokens_input=t_in,
            tokens_output=t_out, custo_usd=usd, custo_brl=brl, simulado=True,
            tool_calls=tool_calls,
        )

    def _mock_narrativa(self, prompt: str, contexto: dict) -> str:
        """Gera narrativa simulada plausível com base no contexto fornecido."""
        if contexto.get("tipo") == "diagnostico":
            score = contexto.get("score", 72)
            economia = contexto.get("economia_potencial", 0)
            return (
                "**Resumo Executivo**\n\n"
                f"A operação logística apresenta um Score Logístico de {score}/100, "
                "classificado como Regular. A análise dos CT-es do período revela "
                "oportunidades concretas de redução de custo, especialmente na "
                "concentração de volume em poucas transportadoras.\n\n"
                "**Pontos Fortes**\n"
                "- Boa cobertura geográfica nas regiões Sul e Sudeste\n"
                "- Prazo de entrega dentro da meta na maioria das rotas\n\n"
                "**Pontos de Atenção**\n"
                "- Frete por kg acima do benchmark na região Nordeste\n"
                "- Alta dependência de uma única transportadora\n\n"
                "**Principais Desvios**\n"
                "- Custo 18% acima da média de mercado em rotas de longa distância\n\n"
                "**Potencial de Economia**\n"
                f"- Estimativa de R$ {economia:,.2f} ao ano com renegociação e BID\n\n"
                "**Plano de Ação Sugerido**\n"
                "1. Realizar BID para a região Nordeste (prazo: 60 dias)\n"
                "2. Diversificar a base de transportadoras\n"
                "3. Renegociar contratos das rotas mais caras\n\n"
                "_[Conteúdo gerado em modo simulado. Configure as chaves de API "
                "para análises reais com GPT-4.1.]_"
            )
        return (
            "Análise gerada em modo simulado. Este texto demonstra o formato "
            "da resposta da IA. Configure as chaves de API (OpenAI/Anthropic) e "
            "desative AI_SIMULATION_MODE para gerar análises reais.\n\n"
            f"Prompt recebido: {prompt[:120]}..."
        )

    def _mock_resposta_chat(self, mensagem, ferramenta, resultado) -> str:
        if not ferramenta:
            return (
                "Não consegui identificar uma ferramenta específica para essa "
                "pergunta no modo simulado. Quando as chaves de API estiverem "
                "configuradas, o assistente entenderá perguntas em linguagem "
                "natural e escolherá a ferramenta certa automaticamente.\n\n"
                "Experimente perguntar: 'Qual minha transportadora mais cara?' "
                "ou 'Quanto posso economizar?'"
            )
        r = resultado or {}
        return (
            f"Com base nos dados da sua operação:\n\n"
            f"{json.dumps(r, ensure_ascii=False, indent=2)}\n\n"
            "_[Resposta em modo simulado. O número acima vem de consulta SQL real "
            "ao seu banco — apenas a narrativa é simulada. Com a chave de API, a "
            "IA interpretará esse dado em linguagem natural.]_"
        )

    # ═══════════════════ Implementações reais ═══════════════════
    def _gerar_openai(self, prompt, system, modelo, max_tokens) -> RespostaLLM:
        msgs = ([{"role": "system", "content": system}] if system else []) + \
               [{"role": "user", "content": prompt}]
        resp = self._openai.chat.completions.create(
            model=modelo, messages=msgs, max_tokens=max_tokens,
        )
        texto = resp.choices[0].message.content or ""
        t_in = resp.usage.prompt_tokens
        t_out = resp.usage.completion_tokens
        usd, brl = _calcular_custo(modelo, t_in, t_out)
        return RespostaLLM(texto, modelo, t_in, t_out, usd, brl, False, raw=resp)

    def _gerar_anthropic(self, prompt, system, modelo, max_tokens) -> RespostaLLM:
        resp = self._anthropic.messages.create(
            model=modelo, max_tokens=max_tokens,
            system=system or "Você é um analista logístico especializado.",
            messages=[{"role": "user", "content": prompt}],
        )
        texto = "".join(b.text for b in resp.content if hasattr(b, "text"))
        t_in = resp.usage.input_tokens
        t_out = resp.usage.output_tokens
        usd, brl = _calcular_custo(modelo, t_in, t_out)
        return RespostaLLM(texto, modelo, t_in, t_out, usd, brl, False, raw=resp)

    def _conversar_openai(self, mensagem, ferramentas, executor, system, historico, modelo) -> RespostaLLM:
        msgs = ([{"role": "system", "content": system}] if system else []) + \
               (historico or []) + [{"role": "user", "content": mensagem}]
        tools = [{"type": "function", "function": f} for f in ferramentas]
        resp = self._openai.chat.completions.create(model=modelo, messages=msgs, tools=tools)
        msg = resp.choices[0].message
        tool_calls = []
        t_in = resp.usage.prompt_tokens
        t_out = resp.usage.completion_tokens

        if msg.tool_calls:
            msgs.append(msg)
            for tc in msg.tool_calls:
                args = json.loads(tc.function.arguments or "{}")
                resultado = executor(tc.function.name, args)
                tool_calls.append({"ferramenta": tc.function.name, "resultado": resultado})
                msgs.append({
                    "role": "tool", "tool_call_id": tc.id,
                    "content": json.dumps(resultado, ensure_ascii=False, default=str),
                })
            resp2 = self._openai.chat.completions.create(model=modelo, messages=msgs)
            texto = resp2.choices[0].message.content or ""
            t_in += resp2.usage.prompt_tokens
            t_out += resp2.usage.completion_tokens
        else:
            texto = msg.content or ""

        usd, brl = _calcular_custo(modelo, t_in, t_out)
        return RespostaLLM(texto, modelo, t_in, t_out, usd, brl, False, tool_calls=tool_calls)

    def _conversar_anthropic(self, mensagem, ferramentas, executor, system, historico, modelo) -> RespostaLLM:
        tools = [{
            "name": f["name"], "description": f.get("description", ""),
            "input_schema": f.get("parameters", {"type": "object", "properties": {}}),
        } for f in ferramentas]
        msgs = (historico or []) + [{"role": "user", "content": mensagem}]
        resp = self._anthropic.messages.create(
            model=modelo, max_tokens=1500,
            system=system or "Você é um analista logístico especializado.",
            messages=msgs, tools=tools,
        )
        tool_calls = []
        t_in = resp.usage.input_tokens
        t_out = resp.usage.output_tokens

        if resp.stop_reason == "tool_use":
            msgs.append({"role": "assistant", "content": resp.content})
            tool_results = []
            for block in resp.content:
                if block.type == "tool_use":
                    resultado = executor(block.name, block.input or {})
                    tool_calls.append({"ferramenta": block.name, "resultado": resultado})
                    tool_results.append({
                        "type": "tool_result", "tool_use_id": block.id,
                        "content": json.dumps(resultado, ensure_ascii=False, default=str),
                    })
            msgs.append({"role": "user", "content": tool_results})
            resp2 = self._anthropic.messages.create(
                model=modelo, max_tokens=1500,
                system=system or "Você é um analista logístico especializado.",
                messages=msgs, tools=tools,
            )
            texto = "".join(b.text for b in resp2.content if hasattr(b, "text"))
            t_in += resp2.usage.input_tokens
            t_out += resp2.usage.output_tokens
        else:
            texto = "".join(b.text for b in resp.content if hasattr(b, "text"))

        usd, brl = _calcular_custo(modelo, t_in, t_out)
        return RespostaLLM(texto, modelo, t_in, t_out, usd, brl, False, tool_calls=tool_calls)


# Instância singleton reutilizável
_cliente: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    global _cliente
    if _cliente is None:
        _cliente = LLMClient()
    return _cliente
