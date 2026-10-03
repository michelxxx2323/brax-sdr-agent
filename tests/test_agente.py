"""Testes do laço do agente com um cliente FALSO: nenhuma chamada real à API."""

import copy

from anthropic.types import Message, TextBlock, ToolUseBlock, Usage

from brax_sdr import memoria
from brax_sdr.agente import Agente


def _msg(conteudo, stop_reason):
    return Message(
        id="msg_teste",
        type="message",
        role="assistant",
        model="claude-haiku-4-5",
        content=conteudo,
        stop_reason=stop_reason,
        stop_sequence=None,
        usage=Usage(input_tokens=100, output_tokens=20),
    )


class ClienteFalso:
    """Imita client.messages.create devolvendo respostas pré-programadas, em ordem."""

    def __init__(self, respostas):
        self.respostas = list(respostas)
        self.chamadas = []
        self.messages = self

    def create(self, **kwargs):
        self.chamadas.append(copy.deepcopy(kwargs))  # cópia: o agente continua mexendo na lista depois
        return self.respostas.pop(0)


def _em_andamento(pasta, lead_id, **campos):
    """Lead com uma troca anterior: a resposta testada não é a primeira (que ganha a apresentação do G4)."""
    lead = memoria.carregar(lead_id, pasta=pasta)
    lead.mensagens = [{"role": "user", "content": "oi"},
                      {"role": "assistant", "content": "Oi! Aqui é o P.H., assistente virtual da BRAX."}]
    for campo, valor in campos.items():
        setattr(lead, campo, valor)
    memoria.salvar(lead, pasta=pasta)


def test_conversa_com_ferramenta_salva_historico_completo(tmp_path):
    cliente = ClienteFalso([
        _msg([ToolUseBlock(id="t1", name="registrar_qualificacao", input={"funcionarios": 6}, type="tool_use")], "tool_use"),
        _msg([TextBlock(text="Oi! Aqui é o P.H., assistente virtual da BRAX.", type="text")], "end_turn"),
    ])
    agente = Agente(client=cliente, pasta_leads=tmp_path)
    resposta = agente.responder("lead1", "Somos 6 pessoas")

    assert resposta.texto == "Oi! Aqui é o P.H., assistente virtual da BRAX."
    assert resposta.ferramentas_usadas == ["registrar_qualificacao"]
    assert resposta.alertas == []
    assert resposta.uso["input_tokens"] == 200

    salvo = memoria.carregar("lead1", pasta=tmp_path)
    assert salvo.dados == {"funcionarios": 6}
    assert [m["role"] for m in salvo.mensagens] == ["user", "assistant", "user", "assistant"]
    assert salvo.mensagens[2]["content"][0]["tool_use_id"] == "t1"

    # A segunda chamada já enxerga o dado registrado no contexto do lead.
    assert '"funcionarios": 6' in cliente.chamadas[1]["system"][1]["text"]


def test_texto_escrito_junto_com_ferramenta_nao_se_perde(tmp_path):
    # Caso real da primeira conversa: texto + ferramenta na mesma rodada, depois rodada final vazia.
    cliente = ClienteFalso([
        _msg([
            TextBlock(text="Perfeito! Hoje como o time paga as despesas?", type="text"),
            ToolUseBlock(id="t1", name="registrar_qualificacao", input={"funcionarios": 12}, type="tool_use"),
        ], "tool_use"),
        _msg([], "end_turn"),
    ])
    _em_andamento(tmp_path, "lead7")
    resposta = Agente(client=cliente, pasta_leads=tmp_path).responder("lead7", "Somos 12 pessoas")
    assert resposta.texto == "Perfeito! Hoje como o time paga as despesas?"


def test_texto_antes_da_ferramenta_nao_aparece_quando_ha_texto_depois(tmp_path):
    # Caso real "lumen2": pergunta escrita antes da aprovação + resposta depois da recusa = duas mensagens contraditórias.
    _em_andamento(tmp_path, "lead8", faixa="executivo")
    cliente = ClienteFalso([
        _msg([
            TextBlock(text="Qual horário funciona melhor para você hoje: manhã ou tarde?", type="text"),
            ToolUseBlock(id="t1", name="solicitar_aprovacao_executivo",
                         input={"resumo": "Lumen", "disponibilidade": "Hoje"}, type="tool_use"),
        ], "tool_use"),
        _msg([TextBlock(text="Hoje não dá, mas amanhã às 15h está livre: link", type="text")], "end_turn"),
    ])
    agente = Agente(client=cliente, pasta_leads=tmp_path, aprovador=lambda *_: ("novo_horario", "amanhã às 15h"))
    resposta = agente.responder("lead8", "Quero conversar hoje")

    assert resposta.texto == "Hoje não dá, mas amanhã às 15h está livre: link"
    salvo = memoria.carregar("lead8", pasta=tmp_path)
    textos_salvos = [b["text"] for m in salvo.mensagens if isinstance(m["content"], list) for b in m["content"] if b["type"] == "text"]
    assert textos_salvos == ["Hoje não dá, mas amanhã às 15h está livre: link"]  # o histórico mostra só o que o lead viu
    assert salvo.mensagens[3]["content"][0]["type"] == "tool_use"


def test_confirmacao_inventada_gera_alerta(tmp_path):
    # Caso real "lumen2": o P.H. disse que o time confirmou sem ter pedido aprovação.
    cliente = ClienteFalso([_msg([TextBlock(
        text="O time confirmou: amanhã às 15h está fechado. Link: [link será enviado pelo time]", type="text")], "end_turn")])
    lead = memoria.carregar("lead9", pasta=tmp_path)
    lead.mensagens = [{"role": "user", "content": "oi"}, {"role": "assistant", "content": "Olá, sou o P.H., assistente virtual."}]
    memoria.salvar(lead, pasta=tmp_path)
    resposta = Agente(client=cliente, pasta_leads=tmp_path).responder("lead9", "E aí?")
    assert "Confiabilidade: afirma confirmação do time sem ter pedido aprovação nesta resposta" in resposta.alertas
    assert "Confiabilidade: texto de exemplo entre colchetes (ex.: [link])" in resposta.alertas
    assert memoria.carregar("lead9", pasta=tmp_path).eventos[-1]["tipo"] == "alerta_confiabilidade"


LONGA = (
    "Fico feliz em te dar uma visão, Paulo! No plano Start (gratuito), vocês têm conta PJ com Pix, TED e boletos, "
    "cartões virtuais ilimitados e até 5 cartões físicos, gestão de despesas com foto do comprovante no app e "
    "integração com contador. Não tem custo mensal. O limite do cartão sai da análise depois que vocês abrem a conta. "
    "Quer começar? É só abrir a conta direto lá: https://app.brax.example/abrir-conta"
)


def test_mensagem_longa_no_whatsapp_e_encurtada(tmp_path):
    curta = "Paulo, o limite sai da análise feita no app, não consigo estimar. Abre a conta aqui: https://app.brax.example/abrir-conta"
    cliente = ClienteFalso([
        _msg([TextBlock(text=LONGA, type="text")], "end_turn"),
        _msg([TextBlock(text=curta, type="text")], "end_turn"),  # resposta da chamada de reescrita
    ])
    _em_andamento(tmp_path, "longo")
    resposta = Agente(client=cliente, pasta_leads=tmp_path).responder("longo", "Me passa uma estimativa")
    assert resposta.texto == curta
    assert cliente.chamadas[1]["messages"] == [{"role": "user", "content": f"<mensagem>\n{LONGA}\n</mensagem>"}]
    assert "tools" not in cliente.chamadas[1]  # a reescrita não usa ferramentas
    salvo = memoria.carregar("longo", pasta=tmp_path)
    assert salvo.mensagens[-1]["content"] == [{"type": "text", "text": curta}]  # histórico = o que o lead viu
    assert salvo.eventos[0]["tipo"] == "mensagem_encurtada"


def test_reescrita_que_perde_o_link_e_descartada(tmp_path):
    cliente = ClienteFalso([
        _msg([TextBlock(text=LONGA, type="text")], "end_turn"),
        _msg([TextBlock(text="Paulo, abre a conta pelo app!", type="text")], "end_turn"),  # sumiu o link
    ])
    _em_andamento(tmp_path, "longo2")
    resposta = Agente(client=cliente, pasta_leads=tmp_path).responder("longo2", "Me passa uma estimativa")
    assert resposta.texto == LONGA


def test_email_nao_e_encurtado(tmp_path):
    cliente = ClienteFalso([_msg([TextBlock(text=LONGA, type="text")], "end_turn")])
    _em_andamento(tmp_path, "email1")
    resposta = Agente(client=cliente, pasta_leads=tmp_path).responder("email1", "Oi", canal="email")
    assert resposta.texto == LONGA
    assert len(cliente.chamadas) == 1


def test_lead_mei_recebe_mensagem_padronizada_e_conversa_encerra(tmp_path):
    # Caso real "mei2": o modelo registrou MEI, encerrou como "fora do assunto" e respondeu
    # só "Boa sorte com os cupcakes!", sem explicar o motivo nem registrar a faixa.
    lead = memoria.carregar("mei", pasta=tmp_path)
    lead.mensagens = [{"role": "user", "content": "aqui é a Joana"}, {"role": "assistant", "content": "Oi, Joana! Sou o P.H., assistente virtual da BRAX."}]
    memoria.salvar(lead, pasta=tmp_path)
    cliente = ClienteFalso([
        _msg([
            ToolUseBlock(id="t1", name="registrar_qualificacao",
                         input={"nome_contato": "Joana", "empresa": "Joana Cupcake", "tipo_empresa": "mei"}, type="tool_use"),
            ToolUseBlock(id="t2", name="encerrar_conversa", input={"motivo": "fora_do_assunto"}, type="tool_use"),
        ], "tool_use"),
        _msg([TextBlock(text="Boa sorte com os cupcakes! 🧁", type="text")], "end_turn"),
    ])
    resposta = Agente(client=cliente, pasta_leads=tmp_path).responder("mei", "sou mei")

    assert resposta.texto.startswith("Obrigado pelo interesse, Joana!")
    assert "MEI" in resposta.texto
    salvo = memoria.carregar("mei", pasta=tmp_path)
    assert (salvo.faixa, salvo.motivo_faixa, salvo.encerrada) == ("fora_do_icp", "mei", True)
    assert salvo.mensagens[-1]["content"][0]["text"] == resposta.texto  # histórico = o que a Joana viu


def test_mei_na_primeira_mensagem_inclui_identificacao(tmp_path):
    cliente = ClienteFalso([
        _msg([ToolUseBlock(id="t1", name="registrar_qualificacao", input={"tipo_empresa": "mei"}, type="tool_use")], "tool_use"),
        _msg([], "end_turn"),
    ])
    resposta = Agente(client=cliente, pasta_leads=tmp_path).responder("mei-direto", "Sou MEI, quero um cartão")
    assert "assistente virtual" in resposta.texto
    assert resposta.alertas == []


VAZAMENTO_REAL = (
    "Conversa encerrada. Wesley recebeu a orientação sobre MEI na mensagem anterior e se despediu naturalmente "
    'com "é nois". Não há necessidade de nova mensagem — seguindo o protocolo, despedidas do lead após o próximo '
    "passo ser entregue não recebem resposta."
)


def test_texto_interno_ao_encerrar_nao_chega_ao_cliente(tmp_path):
    # Caso real "mei3": ao encerrar, o P.H. escreveu um comentário interno para o cliente.
    lead = memoria.carregar("wesley", pasta=tmp_path)
    lead.faixa, lead.motivo_faixa = "fora_do_icp", "mei"
    lead.mensagens = [{"role": "user", "content": "é mei"}, {"role": "assistant", "content": "Obrigado pelo interesse, Wesley!"}]
    memoria.salvar(lead, pasta=tmp_path)
    cliente = ClienteFalso([
        _msg([ToolUseBlock(id="t1", name="encerrar_conversa", input={"motivo": "proximo_passo_entregue"}, type="tool_use")], "tool_use"),
        _msg([TextBlock(text=VAZAMENTO_REAL, type="text")], "end_turn"),
    ])
    resposta = Agente(client=cliente, pasta_leads=tmp_path).responder("wesley", "valeu, até mais meu chapa")

    assert resposta.texto is None
    assert resposta.motivo_silencio == "conversa_encerrada"
    salvo = memoria.carregar("wesley", pasta=tmp_path)
    textos = [b.get("text", "") for m in salvo.mensagens if isinstance(m["content"], list) for b in m["content"]]
    assert not any("protocolo" in t for t in textos)  # o vazamento não fica no histórico
    assert any(e["tipo"] == "vazamento_bloqueado" for e in salvo.eventos)


def test_texto_interno_no_meio_da_conversa_vira_transferencia(tmp_path):
    cliente = ClienteFalso([_msg([TextBlock(text="O lead ainda não informou o gasto mensal.", type="text")], "end_turn")])
    resposta = Agente(client=cliente, pasta_leads=tmp_path).responder("vaza2", "oi")
    assert "pessoa do nosso time" in resposta.texto


def test_encerrar_sem_escrever_nada_fica_em_silencio(tmp_path):
    lead = memoria.carregar("mudo", pasta=tmp_path)
    lead.faixa = "self_service"
    memoria.salvar(lead, pasta=tmp_path)
    cliente = ClienteFalso([
        _msg([ToolUseBlock(id="t1", name="encerrar_conversa", input={"motivo": "proximo_passo_entregue"}, type="tool_use")], "tool_use"),
        _msg([], "end_turn"),
    ])
    resposta = Agente(client=cliente, pasta_leads=tmp_path).responder("mudo", "valeu mesmo, vou abrir hoje ainda")
    assert resposta.texto is None
    assert resposta.motivo_silencio == "conversa_encerrada"


def test_historico_e_relido_na_mensagem_seguinte(tmp_path):
    cliente = ClienteFalso([
        _msg([TextBlock(text="Olá! Sou o P.H., assistente virtual da BRAX.", type="text")], "end_turn"),
        _msg([TextBlock(text="Entendi.", type="text")], "end_turn"),
    ])
    agente = Agente(client=cliente, pasta_leads=tmp_path)
    agente.responder("lead2", "Oi")
    agente.responder("lead2", "Tudo bem?")
    enviadas = cliente.chamadas[1]["messages"]
    assert [m["role"] for m in enviadas] == ["user", "assistant", "user"]
    assert enviadas[0]["content"] == "Oi"
    assert enviadas[2]["content"] == "Tudo bem?"


def test_primeira_mensagem_sem_identificacao_e_completada_pelo_codigo(tmp_path):
    # Guardrail G4 garantido em código (achado nos evals: 2 de 20 primeiras mensagens sem "assistente virtual").
    cliente = ClienteFalso([_msg([TextBlock(text="Oi, tudo bem? Qual o nome da empresa?", type="text")], "end_turn")])
    resposta = Agente(client=cliente, pasta_leads=tmp_path).responder("lead3", "Oi")
    assert resposta.texto == "Oi, tudo bem? Aqui é o P.H., assistente virtual da BRAX. Qual o nome da empresa?"
    assert resposta.alertas == []
    assert memoria.carregar("lead3", pasta=tmp_path).mensagens[-1]["content"][0]["text"] == resposta.texto


def test_markdown_em_negrito_sai_do_whatsapp(tmp_path):
    cliente = ClienteFalso([
        _msg([TextBlock(text="Oi! Aqui é o P.H., assistente virtual da BRAX. O plano **Start** é gratuito.", type="text")],
             "end_turn"),
    ])
    resposta = Agente(client=cliente, pasta_leads=tmp_path).responder("lead4", "Quanto custa?")
    assert resposta.texto == "Oi! Aqui é o P.H., assistente virtual da BRAX. O plano Start é gratuito."


def test_depois_do_opt_out_o_agente_nao_chama_a_api(tmp_path):
    lead = memoria.carregar("lead4", pasta=tmp_path)
    lead.opt_out = True
    memoria.salvar(lead, pasta=tmp_path)
    cliente = ClienteFalso([])
    resposta = Agente(client=cliente, pasta_leads=tmp_path).responder("lead4", "Oi de novo")
    assert resposta.texto is None
    assert cliente.chamadas == []


def test_erro_da_api_nao_corrompe_o_historico(tmp_path):
    class ClienteQueFalha(ClienteFalso):
        def create(self, **kwargs):
            if self.respostas:
                return super().create(**kwargs)
            raise RuntimeError("API fora do ar")

    cliente = ClienteQueFalha([
        _msg([ToolUseBlock(id="t1", name="registrar_opt_out", input={}, type="tool_use")], "tool_use"),
    ])
    agente = Agente(client=cliente, pasta_leads=tmp_path)
    try:
        agente.responder("lead5", "Para de me mandar mensagem")
    except RuntimeError:
        pass
    salvo = memoria.carregar("lead5", pasta=tmp_path)
    assert salvo.mensagens == []  # nada salvo pela metade
    assert salvo.opt_out is False


def test_recusa_do_modelo_vira_transferencia_segura(tmp_path):
    cliente = ClienteFalso([_msg([], "refusal")])
    resposta = Agente(client=cliente, pasta_leads=tmp_path).responder("lead6", "...")
    assert "pessoa do nosso time" in resposta.texto
    salvo = memoria.carregar("lead6", pasta=tmp_path)
    assert salvo.mensagens[-1]["role"] == "assistant"


# --- Achados do teste "mei3" (continuação) ---

def test_reescrita_fora_do_papel_e_descartada():
    from brax_sdr.agente import _reescrita_confiavel

    original = (
        "Oi, Wesley! Para abrir a conta, basta baixar o app oficial da BRAX, cadastrar a empresa e enviar os "
        "documentos por lá. A análise costuma sair em até 2 dias úteis. " * 3
    )
    # Respostas reais do editor no teste: falou de si mesmo e das próprias funções.
    assert not _reescrita_confiavel(original, "Entendi! Estou pronto para reescrever mensagens de WhatsApp. Envie a mensagem.")
    assert not _reescrita_confiavel(original, "Oi! Sou P.H. Estou aqui para conversar com leads e qualificar empresas.")
    assert _reescrita_confiavel(
        original, "Wesley, para abrir a conta baixe o app oficial da BRAX, cadastre a empresa e envie os documentos por lá. A análise costuma sair em até 2 dias úteis."
    )


def test_despedida_de_lead_roteado_encerra_automaticamente(tmp_path):
    _em_andamento(tmp_path, "abs", faixa="self_service")
    cliente = ClienteFalso([_msg([TextBlock(text="Abraço, Wesley!", type="text")], "end_turn")])
    agente = Agente(client=cliente, pasta_leads=tmp_path)
    assert agente.responder("abs", "Abs").texto == "Abraço, Wesley!"
    assert memoria.carregar("abs", pasta=tmp_path).encerrada is True
    segunda = agente.responder("abs", "tmj")  # não chega à IA: o ClienteFalso não tem mais respostas
    assert segunda.motivo_silencio == "conversa_encerrada"


def test_nao_encerra_se_o_ph_fez_uma_pergunta(tmp_path):
    lead = memoria.carregar("pergunta", pasta=tmp_path)
    lead.faixa = "executivo"
    memoria.salvar(lead, pasta=tmp_path)
    cliente = ClienteFalso([_msg([TextBlock(text="Perfeito! Pode ser amanhã às 15h?", type="text")], "end_turn")])
    Agente(client=cliente, pasta_leads=tmp_path).responder("pergunta", "ok")
    assert memoria.carregar("pergunta", pasta=tmp_path).encerrada is False
