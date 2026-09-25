"""Ferramentas (tools) do P.H.

Fase 2: todas agem sobre a memória local do lead. Nas fases seguintes,
as mesmas ferramentas passam a chamar HubSpot (CRM) e Slack (aprovação).
"""

import json
from collections.abc import Callable

from brax_sdr import config
from brax_sdr.memoria import Lead
from brax_sdr.roteamento import PONTOS_POR_SINAL, TIPOS_EMPRESA, prioridade, rotear

# Recebe (lead, resumo, disponibilidade) e devolve (decisao, observacao),
# com decisao em "aprovada" | "recusada" | "pendente".
Aprovador = Callable[[Lead, str, str], tuple[str, str]]

PERSONAS = ("founder_ceo", "financas_cfo", "operacoes_people", "outro")

FERRAMENTAS = [
    {
        "name": "registrar_qualificacao",
        "description": (
            "Registra dados de qualificação que o lead revelou na conversa. Envie apenas os campos novos "
            "ou corrigidos; os demais são mantidos. Converta estimativas em números."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "empresa": {"type": "string", "description": "Nome da empresa."},
                "site": {"type": "string"},
                "tipo_empresa": {
                    "type": "string",
                    "enum": list(TIPOS_EMPRESA),
                    "description": "ltda, sa, outro_cnpj (outro tipo com CNPJ), mei, sem_cnpj ou pessoa_fisica.",
                },
                "funcionarios": {"type": "integer", "description": "Número aproximado de pessoas na empresa."},
                "gasto_mensal": {"type": "number", "description": "Gasto mensal estimado com cartão e despesas, em reais."},
                "nome_contato": {"type": "string"},
                "cargo": {"type": "string"},
                "persona": {"type": "string", "enum": list(PERSONAS)},
                "decisor": {"type": "boolean", "description": "Se quem conversa decide sobre banco e cartões."},
                "setor": {"type": "string"},
                "dor": {"type": "string", "description": "Principal motivo do contato, em poucas palavras."},
                "solucao_atual": {"type": "string", "description": "Banco, cartão ou ferramenta que usam hoje."},
                "sinais_de_compra": {
                    "type": "array",
                    "items": {"type": "string", "enum": list(PONTOS_POR_SINAL)},
                },
                "so_quer_credito": {"type": "boolean", "description": "Verdadeiro se o lead busca apenas crédito ou empréstimo."},
                "setor_especial": {
                    "type": "boolean",
                    "description": "Verdadeiro se o setor está na lista de análise especial de vendas/qualificacao.md.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "rotear_lead",
        "description": (
            "Aplica a tabela de roteamento do ICP aos dados já registrados e devolve a faixa "
            "(self_service, executivo, fora_do_icp, humano ou dados_insuficientes) e o próximo passo. "
            "Registre os dados com registrar_qualificacao antes de chamar."
        ),
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "solicitar_aprovacao_executivo",
        "description": (
            "Pede a um humano aprovação para agendar o lead com um executivo. Use só depois que "
            "rotear_lead devolver a faixa executivo e o lead informar sua disponibilidade."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "resumo": {"type": "string", "description": "Resumo do lead para o executivo, em até 5 linhas."},
                "disponibilidade": {"type": "string", "description": "Dias e períodos que o lead indicou."},
            },
            "required": ["resumo", "disponibilidade"],
            "additionalProperties": False,
        },
    },
    {
        "name": "transferir_para_humano",
        "description": (
            "Encaminha a conversa para uma pessoa do time. Use quando o lead pedir, em assuntos fora do "
            "escopo de pré-vendas ou quando você não tiver certeza da resposta."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"motivo": {"type": "string"}},
            "required": ["motivo"],
            "additionalProperties": False,
        },
    },
    {
        "name": "registrar_opt_out",
        "description": "Registra que o lead pediu para não receber mais mensagens (LGPD). Depois disso, nenhum contato é feito.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
]

_TIPOS_JSON = {"string": str, "integer": int, "number": (int, float), "boolean": bool, "array": list}


def _validar_qualificacao(entrada: dict) -> dict:
    """Confere tipos e valores permitidos; o modelo às vezes erra o formato."""
    schema = FERRAMENTAS[0]["input_schema"]["properties"]
    limpo = {}
    for campo, valor in entrada.items():
        regra = schema.get(campo)
        if regra is None:
            raise ValueError(f"campo desconhecido: {campo}")
        tipo = _TIPOS_JSON[regra["type"]]
        if isinstance(valor, bool) and regra["type"] in ("integer", "number"):
            raise ValueError(f"{campo} deve ser número")
        if not isinstance(valor, tipo):
            raise ValueError(f"{campo} deve ser do tipo {regra['type']}")
        if "enum" in regra and valor not in regra["enum"]:
            raise ValueError(f"{campo} deve ser um de {regra['enum']}")
        if regra["type"] == "array":
            permitidos = regra["items"]["enum"]
            if any(item not in permitidos for item in valor):
                raise ValueError(f"{campo} só aceita {permitidos}")
        if campo in ("funcionarios", "gasto_mensal") and valor < 0:
            raise ValueError(f"{campo} não pode ser negativo")
        limpo[campo] = valor
    return limpo


def _registrar_qualificacao(lead: Lead, entrada: dict) -> dict:
    novos = _validar_qualificacao(entrada)
    if "sinais_de_compra" in novos:
        novos["sinais_de_compra"] = sorted(set(lead.dados.get("sinais_de_compra", [])) | set(novos["sinais_de_compra"]))
    lead.dados.update(novos)
    lead.prioridade = prioridade(lead.dados.get("sinais_de_compra"), lead.dados.get("decisor"))
    lead.registrar_evento("qualificacao", ", ".join(sorted(novos)))
    return {"ok": True, "dados_coletados": lead.dados}


_PROXIMO_PASSO = {
    "self_service": "Envie o link oficial do app (link_app) e reforce que cadastro e documentos são feitos só no app.",
    "executivo": "Pergunte a disponibilidade do lead e depois chame solicitar_aprovacao_executivo. Não envie link de agenda ainda.",
    "fora_do_icp": "Agradeça, explique com educação que o produto é para outro perfil, não prometa nada e encerre.",
    "humano": "Diga que uma pessoa do time vai continuar o atendimento e chame transferir_para_humano.",
    "dados_insuficientes": "Pergunte, uma coisa por vez, o que falta para rotear.",
}


def _rotear_lead(lead: Lead) -> dict:
    d = lead.dados
    resultado = rotear(
        tipo_empresa=d.get("tipo_empresa"),
        funcionarios=d.get("funcionarios"),
        gasto_mensal=d.get("gasto_mensal"),
        so_quer_credito=bool(d.get("so_quer_credito")),
        setor_especial=bool(d.get("setor_especial")),
    )
    resposta = {"faixa": resultado.faixa, "motivo": resultado.motivo, "proximo_passo": _PROXIMO_PASSO[resultado.faixa]}
    if resultado.faixa != "dados_insuficientes":
        lead.faixa, lead.motivo_faixa = resultado.faixa, resultado.motivo
        lead.registrar_evento("roteamento", f"{resultado.faixa}: {resultado.motivo}")
    if resultado.faixa == "self_service":
        resposta["link_app"] = config.LINK_APP
    return resposta


def _solicitar_aprovacao(lead: Lead, entrada: dict, aprovador: Aprovador | None) -> dict:
    if lead.faixa != "executivo":
        raise ValueError("só é possível pedir aprovação para leads na faixa executivo (chame rotear_lead antes)")
    resumo, disponibilidade = entrada["resumo"], entrada["disponibilidade"]
    decisao, observacao = aprovador(lead, resumo, disponibilidade) if aprovador else ("pendente", "")
    lead.aprovacao = decisao
    lead.registrar_evento(f"aprovacao_{decisao}", observacao or resumo)
    resposta = {"aprovacao": decisao, "observacao_do_time": observacao}
    if decisao == "aprovada":
        resposta["link_agenda"] = config.LINK_AGENDA_EXECUTIVO
        resposta["proximo_passo"] = "Envie o link de agenda do executivo."
    elif decisao == "recusada":
        resposta["proximo_passo"] = "Não envie agenda. Siga a observação do time; se não houver, diga que o time vai retornar."
    else:
        resposta["proximo_passo"] = "Diga que vai confirmar a agenda e retorna em seguida. Não envie link."
    return resposta


def _transferir_para_humano(lead: Lead, entrada: dict) -> dict:
    lead.registrar_evento("transferencia_humano", entrada["motivo"])
    return {
        "ok": True,
        "proximo_passo": "Avise que uma pessoa do time vai continuar a conversa em horário comercial (seg a sex, 9h às 18h).",
    }


def _registrar_opt_out(lead: Lead) -> dict:
    lead.opt_out = True
    lead.registrar_evento("opt_out", "lead pediu para parar")
    return {"ok": True, "proximo_passo": "Confirme em uma frase curta que não vai mais entrar em contato. Não faça perguntas."}


def executar(nome: str, entrada: dict, lead: Lead, aprovador: Aprovador | None = None) -> tuple[str, bool]:
    """Executa uma ferramenta. Devolve (conteúdo em JSON, é_erro)."""
    try:
        if nome == "registrar_qualificacao":
            resultado = _registrar_qualificacao(lead, entrada)
        elif nome == "rotear_lead":
            resultado = _rotear_lead(lead)
        elif nome == "solicitar_aprovacao_executivo":
            resultado = _solicitar_aprovacao(lead, entrada, aprovador)
        elif nome == "transferir_para_humano":
            resultado = _transferir_para_humano(lead, entrada)
        elif nome == "registrar_opt_out":
            resultado = _registrar_opt_out(lead)
        else:
            raise ValueError(f"ferramenta desconhecida: {nome}")
    except (ValueError, KeyError) as erro:
        lead.registrar_evento("erro_ferramenta", f"{nome}: {erro}")
        return json.dumps({"erro": str(erro)}, ensure_ascii=False), True
    return json.dumps(resultado, ensure_ascii=False), False
