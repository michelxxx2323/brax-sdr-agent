"""O agente P.H.: recebe a mensagem de um lead e devolve a resposta.

Laço manual de ferramentas (decisão 015): precisamos salvar o histórico
completo (incluindo chamadas de ferramentas) na memória do lead.
"""

import re
from dataclasses import dataclass, field

import anthropic

from brax_sdr import config, memoria
from brax_sdr.cerebro import carregar_cerebro
from brax_sdr.ferramentas import FERRAMENTAS, Aprovador, executar
from brax_sdr.guardrails import LIMITE_CARACTERES_WHATSAPP, checar_confiabilidade, checar_resposta, tipo_de_evento
from brax_sdr.memoria import Lead
from brax_sdr.mensagens import mensagem_fora_do_icp
from brax_sdr.prompt import montar_system
from brax_sdr.protecao import verificar_antes_da_api

MENSAGEM_DE_SEGURANCA = "Vou te passar para uma pessoa do nosso time, que continua o atendimento em seguida."


@dataclass
class Resposta:
    texto: str | None  # None = o P.H. não deve responder (ver motivo_silencio)
    lead: Lead
    motivo_silencio: str | None = None  # opt_out | conversa_encerrada | limite_diario | limite_de_custo
    ferramentas_usadas: list[str] = field(default_factory=list)
    alertas: list[str] = field(default_factory=list)
    uso: dict = field(default_factory=dict)

    @property
    def custo_usd(self) -> float:
        return config.custo_estimado_usd(config.MODELO_CONVERSA, self.uso)


def _somar_uso(total: dict, usage) -> None:
    for campo in ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"):
        total[campo] = total.get(campo, 0) + (getattr(usage, campo, None) or 0)


def _remover_texto(mensagem: dict) -> None:
    """Tira os blocos de texto de uma mensagem com ferramenta (os blocos tool_use continuam)."""
    mensagem["content"] = [b for b in mensagem["content"] if b["type"] != "text"]


def _trocar_texto(mensagem: dict, texto: str) -> None:
    """Substitui os blocos de texto de uma mensagem do assistente por um único texto (mantém tool_use)."""
    outros = [b for b in mensagem["content"] if b["type"] != "text"] if isinstance(mensagem["content"], list) else []
    mensagem["content"] = [{"type": "text", "text": texto}, *outros]


INSTRUCOES_ENCURTAR = (
    "Você reescreve mensagens de WhatsApp de um assistente de vendas. Reescreva a mensagem recebida em até "
    "300 caracteres, em português do Brasil, mantendo o sentido, o tom, o nome da pessoa, todos os links exatamente "
    "como estão e qualquer aviso de segurança (ex.: cadastro e documentos só no app). Sem markdown e sem listas. "
    "No máximo uma pergunta. Não acrescente informações. Responda apenas com a mensagem reescrita."
)


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

    def _encurtar(self, texto: str, uso: dict) -> str:
        """Pede uma versão curta da mensagem. Na dúvida (erro, ficou maior, perdeu link), mantém a original."""
        try:
            msg = self.client.messages.create(
                model=config.MODELO_CONVERSA,
                max_tokens=1024,
                system=INSTRUCOES_ENCURTAR,
                messages=[{"role": "user", "content": texto}],
            )
        except anthropic.APIError:
            return texto
        _somar_uso(uso, msg.usage)
        curto = "\n\n".join(b.text.strip() for b in msg.content if b.type == "text").strip()
        links = re.findall(r"https?://[^\s)]+", texto)
        if not curto or len(curto) >= len(texto) or any(link not in curto for link in links):
            return texto
        return curto

    def responder(self, lead_id: str, texto: str, canal: str = "whatsapp") -> Resposta:
        lead = memoria.carregar(lead_id, canal=canal, pasta=self.pasta_leads)

        # Guardrail G5 garantido em código: depois do opt-out, o P.H. não responde.
        if lead.opt_out:
            lead.registrar_evento("mensagem_apos_opt_out", "não respondida; encaminhar a humano se necessário")
            memoria.salvar(lead, pasta=self.pasta_leads)
            return Resposta(texto=None, lead=lead, motivo_silencio="opt_out")

        # Proteção de custo e encerramento (decisão 021): decide sem chamar a API.
        protecao = verificar_antes_da_api(lead, texto)
        if protecao:
            motivo, resposta_fixa = protecao
            lead.registrar_evento("sem_chamada_a_api", motivo)
            if resposta_fixa:
                recebida = texto if len(texto) <= config.LIMITE_CARACTERES_MENSAGEM else f"[mensagem de {len(texto)} caracteres, não processada]"
                lead.mensagens += [{"role": "user", "content": recebida}, {"role": "assistant", "content": resposta_fixa}]
            memoria.salvar(lead, pasta=self.pasta_leads)
            return Resposta(texto=resposta_fixa, lead=lead, motivo_silencio=None if resposta_fixa else motivo)

        primeira = not any(m["role"] == "assistant" for m in lead.mensagens)
        faixa_inicial = lead.faixa
        mensagens = [*lead.mensagens, {"role": "user", "content": texto}]
        resposta = Resposta(texto=None, lead=lead)
        # Cada rodada: (posição da mensagem do assistente em `mensagens`, textos escritos nela).
        rodadas_com_ferramenta: list[tuple[int, list[str]]] = []
        textos_finais: list[str] = []
        mensagem_do_codigo = None

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
                mensagem_do_codigo = MENSAGEM_DE_SEGURANCA
                break

            conteudo = _conteudo_salvavel(msg.content)
            if conteudo:
                mensagens.append({"role": "assistant", "content": conteudo})
            textos_da_rodada = [b["text"].strip() for b in conteudo if b["type"] == "text"]

            if msg.stop_reason != "tool_use":
                if msg.stop_reason == "max_tokens":
                    lead.registrar_evento("alerta", "resposta cortada por max_tokens")
                textos_finais = textos_da_rodada
                break

            rodadas_com_ferramenta.append((len(mensagens) - 1, textos_da_rodada))

            resultados = []
            for bloco in (b for b in conteudo if b["type"] == "tool_use"):
                resposta.ferramentas_usadas.append(bloco["name"])
                saida, erro = executar(bloco["name"], bloco["input"], lead, self.aprovador)
                resultados.append({"type": "tool_result", "tool_use_id": bloco["id"], "content": saida, "is_error": erro})
            mensagens.append({"role": "user", "content": resultados})
        else:
            lead.registrar_evento("alerta", "limite de rodadas de ferramentas atingido")
            mensagem_do_codigo = MENSAGEM_DE_SEGURANCA

        # O lead vê UMA mensagem: a escrita depois dos resultados das ferramentas. Texto escrito antes de uma
        # ferramenta pode contradizer o resultado (ex.: perguntar horário e depois receber recusa), então sai
        # do histórico. Exceção: se a rodada final vier vazia, vale o último texto escrito antes.
        rodada_exibida = None
        if mensagem_do_codigo:
            texto_final = mensagem_do_codigo
            mensagens.append({"role": "assistant", "content": mensagem_do_codigo})
        elif textos_finais:
            texto_final = "\n\n".join(textos_finais)
        else:
            com_texto = [r for r in rodadas_com_ferramenta if r[1]]
            rodada_exibida = com_texto[-1][0] if com_texto else None
            texto_final = "\n\n".join(com_texto[-1][1]) if com_texto else ""
        for posicao, _ in rodadas_com_ferramenta:
            if posicao != rodada_exibida:
                _remover_texto(mensagens[posicao])

        def fixar_texto(novo: str) -> None:
            """Troca o texto que o lead vai ver, mantendo o histórico igual ao que foi enviado."""
            if textos_finais:
                _trocar_texto(mensagens[-1], novo)
            elif rodada_exibida is not None:
                _trocar_texto(mensagens[rodada_exibida], novo)
            else:
                mensagens.append({"role": "assistant", "content": [{"type": "text", "text": novo}]})

        if not mensagem_do_codigo and lead.faixa == "fora_do_icp" and faixa_inicial != "fora_do_icp":
            # Recusa com texto padronizado e encerramento feitos pelo código (decisão 023).
            texto_final = mensagem_fora_do_icp(lead.motivo_faixa, lead.dados.get("nome_contato"), primeira)
            fixar_texto(texto_final)
            if not lead.encerrada:
                lead.encerrada = True
                lead.registrar_evento("conversa_encerrada", f"fora do perfil: {lead.motivo_faixa}")
        elif not mensagem_do_codigo and lead.canal == "whatsapp" and len(texto_final) > LIMITE_CARACTERES_WHATSAPP:
            # Mensagem longa no WhatsApp: pede uma versão curta ao modelo (decisão 022).
            curto = self._encurtar(texto_final, resposta.uso)
            if curto != texto_final:
                lead.registrar_evento("mensagem_encurtada", f"{len(texto_final)} → {len(curto)} caracteres")
                fixar_texto(curto)
                texto_final = curto

        resposta.alertas = (
            checar_resposta(texto_final, primeira, lead.canal) + checar_confiabilidade(texto_final, resposta.ferramentas_usadas)
            if texto_final
            else []
        )
        for alerta in resposta.alertas:
            lead.registrar_evento(tipo_de_evento(alerta), alerta)

        lead.mensagens = mensagens
        lead.custo_total_usd += resposta.custo_usd
        memoria.salvar(lead, pasta=self.pasta_leads)
        resposta.texto = texto_final
        return resposta
