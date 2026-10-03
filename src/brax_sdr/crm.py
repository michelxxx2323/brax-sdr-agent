"""Sincronização com o HubSpot (CRM): contato, empresa e negócio de cada lead (Fase 5, decisão 033).

Chamadas diretas à API REST do HubSpot com httpx (sem SDK extra). A regra de negócio (qual etapa do funil,
quais campos) fica em funções puras, testáveis sem internet; o envio fica na classe HubSpot.
Se o HubSpot falhar, a conversa com o lead NÃO para: o lead fica marcado como pendente e a próxima
sincronização tenta de novo.
"""

from datetime import datetime, timezone

import httpx

from brax_sdr import config
from brax_sdr.memoria import Lead

# --- Campos próprios da BRAX no HubSpot -----------------------------------------------------------
# (nome interno, rótulo, tipo, tipo de campo)
GRUPO = ("brax", "BRAX SDR (P.H.)")
CAMPOS = {
    "contacts": [
        ("brax_lead_id", "ID do lead na BRAX", "string", "text"),
        ("brax_canal", "Canal de origem", "string", "text"),
        ("brax_faixa", "Faixa de roteamento", "string", "text"),
        ("brax_motivo_faixa", "Motivo da faixa", "string", "textarea"),
        ("brax_prioridade", "Prioridade (sinais de compra)", "number", "number"),
        ("brax_sinais_de_compra", "Sinais de compra", "string", "textarea"),
        ("brax_decisor", "É quem decide", "string", "text"),
        ("brax_dor", "Dor principal", "string", "textarea"),
        ("brax_solucao_atual", "Solução atual", "string", "textarea"),
        ("brax_motivo_encerramento", "Motivo do encerramento ou da perda", "string", "text"),
        ("brax_opt_out", "Pediu para não receber mensagens (LGPD)", "string", "text"),
    ],
    "companies": [
        ("brax_tipo_empresa", "Tipo de empresa (informado)", "string", "text"),
        ("brax_gasto_mensal", "Gasto mensal estimado (R$)", "number", "number"),
        ("brax_setor", "Setor (informado pelo lead)", "string", "text"),
    ],
    "deals": [
        ("brax_faixa", "Faixa de roteamento", "string", "text"),
        ("brax_aprovacao", "Aprovação do executivo", "string", "text"),
    ],
}

# Funil "BRAX Inbound": (chave interna, rótulo, probabilidade). Probabilidade 0 = negócio perdido (fechado).
ETAPAS = [
    ("qualificado_app", "Qualificado – abertura pelo app", "0.4"),
    ("reuniao_solicitada", "Reunião solicitada", "0.5"),
    ("reuniao_aprovada", "Reunião aprovada", "0.7"),
    ("perdido", "Perdido", "0.0"),
]
# Se não for possível criar o funil próprio, usa as etapas do funil padrão do HubSpot.
ETAPAS_DO_FUNIL_PADRAO = {
    "qualificado_app": "qualifiedtobuy",
    "reuniao_solicitada": "appointmentscheduled",
    "reuniao_aprovada": "presentationscheduled",
    "perdido": "closedlost",
}


# --- Regras (funções puras) ---------------------------------------------------------------------

def motivo_de_perda(lead: Lead) -> str | None:
    if lead.opt_out:
        return "opt_out"
    if lead.dados.get("motivo_encerramento"):
        return lead.dados["motivo_encerramento"]
    if lead.sem_resposta:
        return "sem_resposta"
    if lead.faixa == "fora_do_icp":
        return f"fora_do_perfil:{lead.motivo_faixa}"
    return None


def etapa_do_negocio(lead: Lead, ja_tem_negocio: bool) -> str | None:
    """Em que etapa do funil o negócio deve estar, ou None se o lead não gera negócio."""
    qualificado = lead.faixa in ("self_service", "executivo")
    if motivo_de_perda(lead) and (ja_tem_negocio or qualificado):
        return "perdido"
    if lead.faixa == "self_service":
        return "qualificado_app"
    if lead.faixa == "executivo":
        if lead.aprovacao in ("aprovada", "novo_horario"):
            return "reuniao_aprovada"
        if lead.aprovacao == "recusada":
            return "qualificado_app"  # o time indicou o app em vez da reunião
        return "reuniao_solicitada"
    return None  # fora do perfil, humano, dados insuficientes: só contato e empresa


def _sem_vazios(campos: dict) -> dict:
    return {k: v for k, v in campos.items() if v not in (None, "", [])}


def campos_do_contato(lead: Lead) -> dict:
    d = lead.dados
    campos = {
        "firstname": d.get("nome_contato"),
        "jobtitle": d.get("cargo"),
        "brax_lead_id": lead.id,
        "brax_canal": lead.canal,
        "brax_faixa": lead.faixa,
        "brax_motivo_faixa": lead.motivo_faixa,
        "brax_prioridade": str(lead.prioridade),
        "brax_sinais_de_compra": ", ".join(d.get("sinais_de_compra", [])),
        "brax_decisor": {True: "sim", False: "não"}.get(d.get("decisor")),
        "brax_dor": d.get("dor"),
        "brax_solucao_atual": d.get("solucao_atual"),
        "brax_motivo_encerramento": motivo_de_perda(lead),
        "brax_opt_out": "sim" if lead.opt_out else None,
    }
    if "@" in lead.id:
        campos["email"] = lead.id
    else:
        campos["phone"] = f"+{lead.id}"
    return _sem_vazios(campos)


def campos_da_empresa(lead: Lead) -> dict:
    d = lead.dados
    return _sem_vazios({
        "name": d.get("empresa"),
        "domain": (d.get("site") or "").replace("https://", "").replace("http://", "").strip("/") or None,
        "numberofemployees": str(d["funcionarios"]) if d.get("funcionarios") is not None else None,
        "brax_tipo_empresa": d.get("tipo_empresa"),
        "brax_gasto_mensal": str(d["gasto_mensal"]) if d.get("gasto_mensal") is not None else None,
        "brax_setor": d.get("setor"),
    })


# --- Cliente do HubSpot -------------------------------------------------------------------------

class ErroHubSpot(RuntimeError):
    pass


class HubSpot:
    # Tipos de associação padrão do HubSpot (contato↔empresa, negócio↔contato, negócio↔empresa).
    def __init__(self, token: str = "", transporte: httpx.BaseTransport | None = None):
        token = token or config.HUBSPOT_ACCESS_TOKEN
        if not token:
            raise ErroHubSpot("Falta HUBSPOT_ACCESS_TOKEN no .env.")
        self.http = httpx.Client(
            base_url="https://api.hubapi.com",
            headers={"Authorization": f"Bearer {token}"},
            timeout=20,
            transport=transporte,
        )
        self._etapas: dict[str, tuple[str, str]] | None = None  # chave → (id do funil, id da etapa)

    def _pedir(self, metodo: str, caminho: str, corpo: dict | None = None, aceitar: tuple[int, ...] = ()) -> dict:
        resposta = self.http.request(metodo, caminho, json=corpo)
        if resposta.status_code >= 400 and resposta.status_code not in aceitar:
            raise ErroHubSpot(f"HubSpot recusou {metodo} {caminho} (HTTP {resposta.status_code}): {resposta.text[:300]}")
        return resposta.json() if resposta.content else {}

    # --- Configuração (uma vez) ---

    def configurar(self) -> list[str]:
        """Cria grupo, campos e funil da BRAX. Pode rodar de novo: o que já existe é mantido."""
        feito = []
        for objeto, campos in CAMPOS.items():
            self._pedir("POST", f"/crm/v3/properties/{objeto}/groups", {"name": GRUPO[0], "label": GRUPO[1]}, aceitar=(409,))
            for nome, rotulo, tipo, tipo_campo in campos:
                r = self.http.post(f"/crm/v3/properties/{objeto}", json={
                    "name": nome, "label": rotulo, "type": tipo, "fieldType": tipo_campo, "groupName": GRUPO[0],
                })
                if r.status_code not in (200, 201, 409):
                    raise ErroHubSpot(f"Não consegui criar o campo {objeto}.{nome} (HTTP {r.status_code}): {r.text[:200]}")
                feito.append(f"{objeto}.{nome}: {'criado' if r.status_code in (200, 201) else 'já existia'}")
        feito.append(f"funil: {self._garantir_funil()}")
        return feito

    def _garantir_funil(self) -> str:
        funis = self._pedir("GET", "/crm/v3/pipelines/deals").get("results", [])
        if any(f["label"] == config.HUBSPOT_FUNIL for f in funis):
            return f"'{config.HUBSPOT_FUNIL}' já existia"
        r = self.http.post("/crm/v3/pipelines/deals", json={
            "label": config.HUBSPOT_FUNIL,
            "displayOrder": 1,
            "stages": [
                {"label": rotulo, "displayOrder": i, "metadata": {"probability": prob}}
                for i, (_, rotulo, prob) in enumerate(ETAPAS)
            ],
        })
        if r.status_code in (200, 201):
            return f"'{config.HUBSPOT_FUNIL}' criado"
        return f"não foi possível criar (HTTP {r.status_code}); os negócios vão usar o funil padrão do HubSpot"

    def _etapa(self, chave: str) -> tuple[str, str]:
        if self._etapas is None:
            funis = self._pedir("GET", "/crm/v3/pipelines/deals").get("results", [])
            proprio = next((f for f in funis if f["label"] == config.HUBSPOT_FUNIL), None)
            if proprio:
                por_rotulo = {e["label"]: e["id"] for e in proprio["stages"]}
                self._etapas = {k: (proprio["id"], por_rotulo[rotulo]) for k, rotulo, _ in ETAPAS if rotulo in por_rotulo}
            else:
                self._etapas = {k: ("default", v) for k, v in ETAPAS_DO_FUNIL_PADRAO.items()}
        return self._etapas[chave]

    # --- Busca e gravação ---

    def _buscar(self, objeto: str, campo: str, valor: str) -> str | None:
        resultado = self._pedir("POST", f"/crm/v3/objects/{objeto}/search", {
            "filterGroups": [{"filters": [{"propertyName": campo, "operator": "EQ", "value": valor}]}],
            "limit": 1,
        })
        resultados = resultado.get("results", [])
        return resultados[0]["id"] if resultados else None

    def _gravar(self, objeto: str, id_: str | None, campos: dict) -> str:
        if id_:
            self._pedir("PATCH", f"/crm/v3/objects/{objeto}/{id_}", {"properties": campos})
            return id_
        return self._pedir("POST", f"/crm/v3/objects/{objeto}", {"properties": campos})["id"]

    def _associar(self, de: str, de_id: str, para: str, para_id: str) -> None:
        self._pedir("PUT", f"/crm/v4/objects/{de}/{de_id}/associations/default/{para}/{para_id}")

    # --- Sincronização de um lead ---

    def sincronizar(self, lead: Lead) -> list[str]:
        """Cria ou atualiza contato, empresa e negócio do lead. Guarda os ids em lead.crm. Devolve o que fez."""
        crm, feito = lead.crm, []

        contato = campos_do_contato(lead)
        if not crm.get("contato_id"):
            chave = "email" if "email" in contato else "phone"
            crm["contato_id"] = self._buscar("contacts", chave, contato[chave])
        crm["contato_id"] = self._gravar("contacts", crm.get("contato_id"), contato)
        feito.append("contato")

        empresa = campos_da_empresa(lead)
        if empresa.get("name"):
            if not crm.get("empresa_id"):
                # Mesma empresa, outro contato (pendência da Fase 2): reaproveita a empresa que já está no CRM.
                existente = self._buscar("companies", "name", empresa["name"])
                if existente:
                    lead.registrar_evento("crm_empresa_existente", empresa["name"])
                crm["empresa_id"] = self._gravar("companies", existente, empresa)
                self._associar("contacts", crm["contato_id"], "companies", crm["empresa_id"])
            else:
                self._gravar("companies", crm["empresa_id"], empresa)
            feito.append("empresa")

        etapa = etapa_do_negocio(lead, ja_tem_negocio=bool(crm.get("negocio_id")))
        if etapa:
            funil, etapa_id = self._etapa(etapa)
            negocio = _sem_vazios({
                "dealname": f"{lead.dados.get('empresa') or lead.id} · BRAX Inbound",
                "pipeline": funil,
                "dealstage": etapa_id,
                "brax_faixa": lead.faixa,
                "brax_aprovacao": lead.aprovacao,
            })
            novo = not crm.get("negocio_id")
            crm["negocio_id"] = self._gravar("deals", crm.get("negocio_id"), negocio)
            if novo:
                self._associar("deals", crm["negocio_id"], "contacts", crm["contato_id"])
                if crm.get("empresa_id"):
                    self._associar("deals", crm["negocio_id"], "companies", crm["empresa_id"])
            feito.append(f"negócio ({etapa})")

        crm["pendente"] = False
        crm["sincronizado_em"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        return feito


def sincronizar_com_seguranca(crm: HubSpot | None, lead: Lead) -> bool:
    """Sincroniza sem nunca derrubar a conversa. Em caso de erro, marca o lead como pendente (tenta de novo depois)."""
    if crm is None:
        return False
    try:
        crm.sincronizar(lead)
        return True
    except Exception as erro:
        lead.crm["pendente"] = True
        lead.registrar_evento("crm_erro", f"{type(erro).__name__}: {str(erro)[:200]}")
        return False


def criar_crm() -> HubSpot | None:
    """HubSpot se houver chave no .env; senão, None (o P.H. funciona sem CRM, como nas fases anteriores)."""
    return HubSpot() if config.HUBSPOT_ACCESS_TOKEN else None
