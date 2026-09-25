"""Testes da memória por lead. Usam uma pasta temporária, nunca data/local."""

from brax_sdr import memoria


def test_lead_novo_comeca_vazio(tmp_path):
    lead = memoria.carregar("ana@lumen.example", canal="email", pasta=tmp_path)
    assert lead.mensagens == []
    assert lead.canal == "email"
    assert lead.opt_out is False


def test_salvar_e_carregar_preserva_tudo(tmp_path):
    lead = memoria.carregar("5511999990000", pasta=tmp_path)
    lead.mensagens.append({"role": "user", "content": "Olá, sou a Ana, da Lumen"})
    lead.dados["funcionarios"] = 28
    lead.faixa = "executivo"
    lead.registrar_evento("roteamento", "executivo")
    memoria.salvar(lead, pasta=tmp_path)

    relido = memoria.carregar("5511999990000", pasta=tmp_path)
    assert relido.mensagens[0]["content"] == "Olá, sou a Ana, da Lumen"  # acentos preservados
    assert relido.dados == {"funcionarios": 28}
    assert relido.faixa == "executivo"
    assert relido.eventos[0]["tipo"] == "roteamento"


def test_id_malicioso_nao_sai_da_pasta(tmp_path):
    lead = memoria.carregar("../../etc/passwd", pasta=tmp_path)
    memoria.salvar(lead, pasta=tmp_path)
    arquivos = list(tmp_path.iterdir())
    assert len(arquivos) == 1
    assert arquivos[0].parent == tmp_path
