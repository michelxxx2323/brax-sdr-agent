"""O agente P.H.: recebe a mensagem de um lead e devolve a resposta.

Laço manual de ferramentas (decisão 015): precisamos salvar o histórico
completo (incluindo chamadas de ferramentas) na memória do lead.
"""

from dataclasses import dataclass, field

import anthropic

from brax_sdr import config, memoria
from brax_sdr.cerebro import carregar_cerebro
from brax_sdr.ferramentas import FERRAMENTAS, Aprovador, executar
from brax_sdr.guardrails import checar_resposta
from brax_sdr.memoria import Lead
from brax_sdr.prompt import montar_system

MENSAGEM_DE_SEGURANCA = "Vou te passar para uma pessoa do nosso time, que continua o atendimento em seguida."


@dataclass
class Resposta:
    texto: str | None  # None = o P.H. não deve responder (ex.: opt-out)
    lead: Lead
    ferramentas_usadas: list[str] = field(default_factory=list)
    alertas: list[str] = field(default_factory=list)
    uso: dict = field(default_factory=dict)

    @property
    def custo_usd(self) -> float:
        return config.custo_estimado_usd(config.MODELO_CONVERSA, self.uso)


def _somar_uso(total: dict, usage) -> None:
    for campo in ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"):
        total[campo] = total.get(campo, 0) + (getattr(usage, campo, None) or 0)


def _conteudo_salvavel(content) -> list[dict]:
    """Converte os blocos da resposta para dicionários, sem blocos de texto vazios (a API os rejeita)."""
    blocos = [b.to_dict() for b in content]
    return [b for b in blocos if not (b.get("type") == "text" and not b.get("text", "").strip())]


class Agente:
    def __init__(
        self,
        client: anthropic.Anthropic | None = None,
        aprovador: Aprovador | None = None,
        pasta_leads=config.PASTA_LEADS,
    ):
        self.client = client or anthropic.Anthropic()
        self.aprovador = aprovador
        self.pasta_leads = pasta_leads
        self.cerebro = carregar_cerebro()

    def responder(self, lead_id: str, texto: str, canal: str = "whatsapp") -> Resposta:
        lead = memoria.carregar(lead_id, canal=canal, pasta=self.pasta_leads)

        # Guardrail G5 garantido em código: depois do opt-out, o P.H. não responde.
        if lead.opt_out:
            lead.registrar_evento("mensagem_apos_opt_out", "não respondida; encaminhar a humano se necessário")
            memoria.salvar(lead, pasta=self.pasta_leads)
            return Resposta(texto=None, lead=lead)

        primeira = not any(m["role"] == "assistant" for m in lead.mensagens)
        mensagens = [*lead.mensagens, {"role": "user", "content": texto}]
        resposta = Resposta(texto=None, lead=lead)
        texto_final = ""

        for _ in range(config.MAX_RODADAS_FERRAMENTAS):
            # Se a API falhar aqui, a exceção sobe e NADA é salvo: o histórico continua válido.
            msg = self.client.messages.create(
                model=config.MODELO_CONVERSA,
                max_tokens=config.MAX_TOKENS_CONVERSA,
                system=montar_system(self.cerebro, lead),
                tools=FERRAMENTAS,
                messages=mensagens,
            )
            _somar_uso(resposta.uso, msg.usage)

            if msg.stop_reason == "refusal":
                lead.registrar_evento("recusa_do_modelo", str(getattr(msg, "stop_details", "")))
                texto_final = MENSAGEM_DE_SEGURANCA
                break

            conteudo = _conteudo_salvavel(msg.content)
            if conteudo:
                mensagens.append({"role": "assistant", "content": conteudo})

            if msg.stop_reason != "tool_use":
                if msg.stop_reason == "max_tokens":
                    lead.registrar_evento("alerta", "resposta cortada por max_tokens")
                texto_final = "\n\n".join(b["text"] for b in conteudo if b["type"] == "text")
                break

            resultados = []
            for bloco in (b for b in conteudo if b["type"] == "tool_use"):
                resposta.ferramentas_usadas.append(bloco["name"])
                saida, erro = executar(bloco["name"], bloco["input"], lead, self.aprovador)
                resultados.append({"type": "tool_result", "tool_use_id": bloco["id"], "content": saida, "is_error": erro})
            mensagens.append({"role": "user", "content": resultados})
        else:
            lead.registrar_evento("alerta", "limite de rodadas de ferramentas atingido")
            texto_final = MENSAGEM_DE_SEGURANCA

        if texto_final and mensagens[-1]["role"] != "assistant":
            # Mensagem de segurança gerada pelo código: registrar no histórico como fala do P.H.
            mensagens.append({"role": "assistant", "content": texto_final})

        resposta.alertas = checar_resposta(texto_final, primeira) if texto_final else []
        for alerta in resposta.alertas:
            lead.registrar_evento("alerta_guardrail", alerta)

        lead.mensagens = mensagens
        memoria.salvar(lead, pasta=self.pasta_leads)
        resposta.texto = texto_final
        return resposta
