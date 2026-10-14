"""Testes das ferramentas e da checagem de guardrails. Não chamam a API."""

import json

from brax_sdr import config
from brax_sdr.ferramentas import executar
from brax_sdr.guardrails import checar_confiabilidade, checar_resposta, parece_texto_interno, sem_frases_de_registro
from brax_sdr.memoria import Lead


def _executar(nome, entrada, lead, aprovador=None):
    saida, erro = executar(nome, entrada, lead, aprovador)
    return json.loads(saida), erro


def test_qualificacao_acumula_dados_e_calcula_prioridade():
    lead = Lead(id="t")
    _executar("registrar_qualificacao", {"empresa": "Lumen", "sinais_de_compra": ["rodada_recente"]}, lead)
    _executar("registrar_qualificacao", {"funcionarios": 28, "decisor": True, "sinais_de_compra": ["gastos_em_dolar"]}, lead)
    assert lead.dados["empresa"] == "Lumen"
    assert lead.dados["sinais_de_compra"] == ["gastos_em_dolar", "rodada_recente"]
    assert lead.prioridade == 3 + 2 + 2


def test_qualificacao_rejeita_dado_invalido_sem_alterar_o_lead():
    lead = Lead(id="t")
    resultado, erro = _executar("registrar_qualificacao", {"funcionarios": "vinte"}, lead)
    assert erro is True
    assert "funcionarios" in resultado["erro"]
    assert lead.dados == {}
    _, erro = _executar("registrar_qualificacao", {"tipo_empresa": "cooperativa"}, lead)
    assert erro is True


def test_qualificacao_descarta_textos_sem_informacao():
    # Caso real da primeira conversa: o modelo enviou nome_contato="Não informado".
    lead = Lead(id="t")
    _executar(
        "registrar_qualificacao",
        {"nome_contato": "Não informado", "site": "  ", "cargo": "desconhecido", "empresa": " Nexora "},
        lead,
    )
    assert lead.dados == {"empresa": "Nexora"}


def test_qualificacao_descarta_nome_generico():
    # Achado nos evals: nome_contato="Lead" virou "Entendido, Lead!", e a despedida foi bloqueada como texto interno.
    lead = Lead(id="t")
    for generico in ("User", "Lead", "usuário", "Cliente"):
        _executar("registrar_qualificacao", {"nome_contato": generico}, lead)
    assert "nome_contato" not in lead.dados
    _executar("registrar_qualificacao", {"nome_contato": "Leandro"}, lead)
    assert lead.dados["nome_contato"] == "Leandro"


def test_rotear_self_service_devolve_link_do_app():
    lead = Lead(id="t", dados={"tipo_empresa": "ltda", "funcionarios": 6, "gasto_mensal": 8000, "setor": "SaaS"})
    resultado, _ = _executar("rotear_lead", {}, lead)
    assert resultado["faixa"] == "self_service"
    assert resultado["link_app"] == config.LINK_APP
    assert lead.faixa == "self_service"


def test_rotear_com_dados_insuficientes_nao_grava_faixa():
    lead = Lead(id="t", dados={"tipo_empresa": "ltda"})
    resultado, _ = _executar("rotear_lead", {}, lead)
    assert resultado["faixa"] == "dados_insuficientes"
    assert lead.faixa is None


def test_aprovacao_exige_faixa_executivo():
    lead = Lead(id="t", faixa="self_service")
    _, erro = _executar("solicitar_aprovacao_executivo", {"resumo": "x", "disponibilidade": "tarde"}, lead)
    assert erro is True


def test_aprovacao_aprovada_libera_link_de_agenda():
    lead = Lead(id="t", faixa="executivo")
    resultado, _ = _executar(
        "solicitar_aprovacao_executivo",
        {"resumo": "Lumen, 28 pessoas", "disponibilidade": "tarde"},
        lead,
        aprovador=lambda lead, resumo, disp: ("aprovada", "ok"),
    )
    assert resultado["link_agenda"] == config.LINK_AGENDA_EXECUTIVO
    assert lead.aprovacao == "aprovada"


def test_aprovacao_com_novo_horario_libera_link_e_repassa_sugestao():
    lead = Lead(id="t", faixa="executivo")
    resultado, _ = _executar(
        "solicitar_aprovacao_executivo",
        {"resumo": "Lumen", "disponibilidade": "hoje"},
        lead,
        aprovador=lambda lead, resumo, disp: ("novo_horario", "amanhã às 15h"),
    )
    assert resultado["link_agenda"] == config.LINK_AGENDA_EXECUTIVO
    assert resultado["observacao_do_time"] == "amanhã às 15h"
    assert lead.aprovacao == "novo_horario"


def test_aprovacao_recusada_nao_libera_link():
    lead = Lead(id="t", faixa="executivo")
    resultado, _ = _executar(
        "solicitar_aprovacao_executivo", {"resumo": "x", "disponibilidade": "y"}, lead,
        aprovador=lambda *_: ("recusada", "indicar o app"),
    )
    assert "link_agenda" not in resultado


def test_aprovacao_sem_aprovador_fica_pendente_e_sem_link():
    lead = Lead(id="t", faixa="executivo")
    resultado, _ = _executar("solicitar_aprovacao_executivo", {"resumo": "x", "disponibilidade": "manhã"}, lead)
    assert resultado["aprovacao"] == "pendente"
    assert "link_agenda" not in resultado


def test_opt_out_marca_o_lead():
    lead = Lead(id="t")
    _executar("registrar_opt_out", {}, lead)
    assert lead.opt_out is True
    assert lead.eventos[-1]["tipo"] == "opt_out"


def test_ferramenta_desconhecida_vira_erro():
    _, erro = _executar("apagar_tudo", {}, Lead(id="t"))
    assert erro is True


# --- Guardrails ---

def test_resposta_segura_nao_gera_alerta():
    texto = "Oi! Aqui é o P.H., assistente virtual da BRAX. O limite depende de uma análise feita no app."
    assert checar_resposta(texto, primeira_mensagem=True) == []


def test_alertas_de_guardrail():
    assert checar_resposta("Seu limite será de R$ 20 mil.", False) == ["G1: possível valor de limite informado"]
    assert checar_resposta("Pode me enviar o contrato social por aqui?", False) == ["G2: possível pedido de dado sensível"]
    assert checar_resposta("O saldo rende 1,2% ao mês.", False) == ["G3: possível rendimento com percentual"]
    assert checar_resposta("Oi! Tudo bem?", True) == ["G4: primeira mensagem sem identificação como assistente virtual"]


def test_alertas_de_estilo_no_whatsapp():
    longa = "Entendi perfeitamente. " * 20
    assert checar_resposta(longa, False, "whatsapp") == [f"Estilo: mensagem longa para WhatsApp ({len(longa)} caracteres)"]
    assert checar_resposta("O link é **este**", False, "whatsapp") == ["Estilo: markdown (**) no WhatsApp"]
    assert checar_resposta(longa + "**x**", False, "email") == []  # no e-mail, texto maior é normal
    lista = "No plano Start vocês têm:\n- Conta PJ com Pix\n- Cartões virtuais"
    assert checar_resposta(lista, False, "whatsapp") == ["Estilo: lista com marcadores no WhatsApp"]
    assert checar_resposta("Custa R$ 490 - e inclui tudo", False, "whatsapp") == []  # hífen no meio da frase não é lista


def test_alertas_de_confiabilidade():
    # Frase real do teste "lumen2", dita sem nenhuma ferramenta.
    promessa = "Perfeito, Sara! Vou confirmar a agenda com o time e te mando o link em seguida."
    assert checar_confiabilidade(promessa, []) == [
        "Confiabilidade: promete uma ação para depois sem ter chamado nenhuma ferramenta"
    ]
    # A mesma frase é legítima quando a aprovação ficou pendente nesta resposta.
    assert checar_confiabilidade(promessa, ["solicitar_aprovacao_executivo"]) == []
    assert checar_confiabilidade("Aqui está o link: https://agenda.brax.example", []) == []


def test_deteccao_de_texto_interno():
    assert parece_texto_interno("Não há necessidade de responder: despedidas do lead não recebem resposta.")
    assert parece_texto_interno("Vou chamar rotear_lead agora.")
    assert parece_texto_interno("Despedidas seguintes não recebem resposta. Se tiver uma dúvida, é só chamar!")  # teste "mei4"
    # Frases legítimas não podem ser bloqueadas.
    assert not parece_texto_interno("O próximo passo é abrir a conta pelo app: https://app.brax.example")
    assert not parece_texto_interno("Nossa ferramenta de gestão de despesas lê o comprovante por foto.")
    assert not parece_texto_interno("Siga as instruções do app para enviar os documentos.")


def test_frase_de_protecao_nao_e_confundida_com_pedido():
    texto = "Eu nunca vou te pedir senha, código ou documento por aqui."
    assert checar_resposta(texto, False) == []


def test_pergunta_com_deixa_eu_confirmar_nao_e_promessa():
    # Falso positivo achado na 1ª bateria de evals.
    pergunta = "Deixa eu confirmar uma coisa: quem mais participa dessa decisão de banco e cartão aí?"
    assert checar_confiabilidade(pergunta, []) == []
    promessa = "Deixa eu confirmar com o time se quinta à tarde ainda tá disponível."
    assert checar_confiabilidade(promessa, []) != []


def test_setor_especial_e_roteado_na_hora_para_humano():
    # Achado na 2ª bateria: a IA transferiu a corretora de cripto sem rotear; o CRM ficaria sem a faixa.
    lead = Lead(id="t")
    resultado, _ = _executar("registrar_qualificacao", {"empresa": "Cripta", "setor": "corretora de cripto"}, lead)
    assert resultado["roteamento"]["faixa"] == "humano"
    assert lead.faixa == "humano" and lead.motivo_faixa == "setor_analise_especial"


def test_lead_transferido_e_roteado_sem_link():
    # Achado na 2ª bateria: o lead esperava o vendedor e recebeu o link do app.
    lead = Lead(id="t", transferido_para_vendedor=True,
                dados={"tipo_empresa": "ltda", "funcionarios": 15, "gasto_mensal": 30000, "setor": "B2B"})
    resultado, _ = _executar("rotear_lead", {}, lead)
    assert lead.faixa == "self_service" and "link_app" not in resultado
    assert "vendedor" in resultado["proximo_passo"]
    # E pode encerrar sem faixa: o próximo passo é do vendedor.
    lead2 = Lead(id="t2", transferido_para_vendedor=True)
    _, erro = _executar("encerrar_conversa", {"motivo": "proximo_passo_entregue"}, lead2)
    assert erro is False and lead2.encerrada


def test_ultimo_dado_registrado_roteia_na_hora():
    # Decisão 049 (teste da Bianca): com tipo, setor, tamanho e gasto, a IA fez outra pergunta em vez de rotear.
    lead = Lead(id="t", dados={"tipo_empresa": "ltda", "setor": "logística", "funcionarios": 8})
    resultado, _ = _executar("registrar_qualificacao", {"gasto_mensal": 20000}, lead)
    assert lead.faixa == "self_service"
    assert resultado["roteamento"]["link_app"] == config.LINK_APP
    # Chamar rotear_lead logo depois não duplica o evento na linha do tempo.
    _executar("rotear_lead", {}, lead)
    assert [e["tipo"] for e in lead.eventos].count("roteamento") == 1


def test_dados_incompletos_nao_roteiam():
    lead = Lead(id="t", dados={"tipo_empresa": "ltda", "funcionarios": 8})
    resultado, _ = _executar("registrar_qualificacao", {"gasto_mensal": 20000}, lead)  # falta o setor
    assert lead.faixa is None and "roteamento" not in resultado


def test_campo_desconhecido_lista_os_campos_aceitos():
    resultado, erro = _executar("registrar_qualificacao", {"motivo": "sem cnpj"}, Lead(id="t"))
    assert erro is True and "motivo" in resultado["erro"] and "tipo_empresa" in resultado["erro"]


def test_frases_reais_do_wesley_e_do_sergio():
    # Decisão 054: as três falhas das conversas de demonstração (gravadas na Fase 2) ficam presas em teste.
    # 1. Raciocínio enviado como mensagem: bloqueado como texto interno.
    for texto in (
        'Conversa encerrada. Wesley recebeu a orientação sobre MEI na mensagem anterior e se despediu naturalmente com '
        '"é nois". Não há necessidade de nova mensagem — seguindo o protocolo.',
        "Conversa encerrada. O lead recebeu o contexto e a despedida é natural — seguindo o protocolo, não há resposta "
        "a despedidas após o próximo passo ser entregue.",
        "Despedidas seguintes não recebem resposta. Se tiver uma dúvida nova sobre a BRAX, é só chamar! 😊",
    ):
        assert parece_texto_interno(texto), texto
    # 3. Promessa de retorno: as duas frases agora são reconhecidas.
    assert checar_confiabilidade("Não posso te passar informação errada, então vou confirmar com o time e te retorno.", [])
    assert checar_confiabilidade("De nada! Assim que eu confirmar com o time, te retorno por aqui. Abraço!", [])
    assert not checar_confiabilidade("Deixa eu confirmar uma coisa: quem mais participa dessa decisão?", [])


def test_planejamento_narrado_e_texto_interno():
    from brax_sdr.guardrails import sem_paragrafos_internos

    assert parece_texto_interno("Vou registrar de novo, com o gasto em dólar como sinal de compra.")
    assert parece_texto_interno("Falta confirmar o tipo de empresa para rotear. Respondo a dúvida e pergunto isso.")
    assert sem_paragrafos_internos("Falta confirmar o tipo para rotear.\n\nQual o tipo da empresa?") == "Qual o tipo da empresa?"
    assert sem_paragrafos_internos("Vou registrar de novo.") == ""  # tudo interno: vale o bloqueio da mensagem inteira
    # Fala legítima continua passando (inclusive a confirmação de opt-out).
    assert not parece_texto_interno("Pronto, registrei seu pedido: não vou mais te enviar mensagens.")
    assert not parece_texto_interno("Para o tamanho de vocês, o caminho é abrir a conta pelo app.")


def test_bastidor_sai_por_paragrafo_inteiro():
    # Bateria de 11/10: "Registro os dados" passava. E a remoção é por parágrafo, nunca por frase: as outras frases de
    # um parágrafo de bastidor também são bastidor, mesmo sem termo interno.
    from brax_sdr.guardrails import sem_paragrafos_internos

    assert sem_paragrafos_internos("Registro os dados e já verifico o próximo passo.\n\nQual o setor?") == "Qual o setor?"
    assert sem_paragrafos_internos("Conversa encerrada. Wesley recebeu a orientação e se despediu naturalmente.") == ""


def test_transferencia_de_cliente_atual_nao_segue_qualificando():
    # Decisão 059: com o cartão bloqueado, o P.H. fazia o questionário de vendas e induzia o envio do CNPJ completo.
    lead = Lead(id="t")
    resultado, _ = _executar("transferir_para_humano", {"motivo": "cartão bloqueado", "cliente_atual": True}, lead)
    assert "não faça perguntas de qualificação" in resultado["proximo_passo"]
    assert "nunca peça CNPJ" in resultado["proximo_passo"]
    assert lead.eventos[-1]["detalhe"].startswith("cliente atual (suporte)")
    # Lead de vendas que pede uma pessoa continua no fluxo da decisão 037 (segue coletando para o vendedor).
    resultado, _ = _executar("transferir_para_humano", {"motivo": "pediu uma pessoa"}, Lead(id="t2"))
    assert "continue a qualificação" in resultado["proximo_passo"]


def test_bastidor_em_ingles_e_texto_interno():
    # Bateria de 11/10: o P.H. narrou em inglês uma falha de ferramenta para o lead.
    assert parece_texto_interno("The registration failed because of an unknown field, and routing still needs the "
                                "company's sector. I'll retry the registration with the valid fields.")
    # Palavras estrangeiras comuns numa fala em português continuam passando.
    assert not parece_texto_interno("Você pode pagar o software em dólar com o cartão internacional, e o app faz o resto.")
    assert not parece_texto_interno("Os comprovantes ficam no app, inclusive de assinaturas como Google Workspace e Slack.")


def test_frases_de_registro_saem_e_o_resto_fica():
    # Decisão 061 (simulador): "Vou registrar o que você me contou" é bastidor narrado ao lead.
    assert sem_frases_de_registro("Perfeito, Marina! Vou registrar o que você me contou. O caminho é o app.") == (
        "Perfeito, Marina! O caminho é o app.")
    assert sem_frases_de_registro("Registrei: 12 pessoas e R$ 15.000 por mês. Qual o setor?") == "Qual o setor?"
    assert sem_frases_de_registro("Anotado! E quantas pessoas?") == "Anotado! E quantas pessoas?"  # reação natural
    # Frase com link nunca sai; uso comum do verbo também não.
    com_link = "Vou registrar e te mando o link: https://app.brax.example/abrir-conta"
    assert sem_frases_de_registro(com_link) == com_link
    comum = "Você pode registrar despesas pelo app. O cartão fica registrado no nome da empresa."
    assert sem_frases_de_registro(comum) == comum
