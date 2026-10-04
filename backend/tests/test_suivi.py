"""Suivi sur 3 échanges (EF-09, décision 0021) : le backend garde le fil et le passe au moteur."""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from gestukaay_backend import app as module_app

client = TestClient(module_app.app)


class _Espion:
    """Faux moteur qui retient le contexte reçu à chaque question."""

    def __init__(self, vrai):
        self.vrai, self.recus = vrai, []

    def repondre(self, req, contexte=None):
        self.recus.append(contexte)
        return self.vrai.repondre(req, contexte)

    def __getattr__(self, nom):
        return getattr(self.vrai, nom)


def _poser(question, conversation="onglet-1"):
    r = client.post("/v1/ask", json={"question": question, "conversation_id": conversation})
    assert r.status_code == 200
    return r.json()["reponse"]


def test_le_contexte_des_echanges_precedents_est_transmis(monkeypatch):
    espion = _Espion(module_app.moteur)
    monkeypatch.setattr(module_app, "moteur", espion)
    premiere = _poser("Combien d'habitants à Thiès ?", "conv-a")
    _poser("Et pour Kaolack ?", "conv-a")
    assert espion.recus[0] == []  # première question : rien avant
    assert [r.model_dump(mode="json") for r in espion.recus[1]] == [premiere["requete"]]


def test_trois_echanges_au_plus_et_incomprehension_gardee(monkeypatch):
    espion = _Espion(module_app.moteur)
    monkeypatch.setattr(module_app, "moteur", espion)
    for q in ["Combien d'habitants à Thiès ?", "blabla incompréhensible", "Population de Dakar et de Thiès en 2023",
              "Combien d'habitants à Thiès ?"]:
        _poser(q, "conv-b")
    _poser("Et pour Kaolack ?", "conv-b")
    dernier = espion.recus[-1]
    assert len(dernier) == 3 and dernier[0] is None  # l'incompréhension compte, la plus ancienne est sortie


def test_conversations_separees_et_sans_identifiant(monkeypatch):
    espion = _Espion(module_app.moteur)
    monkeypatch.setattr(module_app, "moteur", espion)
    _poser("Combien d'habitants à Thiès ?", "conv-c")
    _poser("Et pour Kaolack ?", "conv-d")
    client.post("/v1/ask", json={"question": "Et pour Kaolack ?"})
    assert espion.recus[1] == [] and espion.recus[2] is None


def test_choix_confirme_remplace_la_reponse_approchee():
    approchee = _poser("Population de la ville de Thiès en 2023", "conv-e")
    confirmee = client.post(f"/v1/ask/{approchee['id']}/confirm", json={"choix_id": "1"}).json()["reponse"]
    ctx = module_app.stockage.contexte("conv-e")
    assert [r.model_dump(mode="json") for r in ctx] == [confirmee["requete"]]


def test_contexte_oublie_apres_30_minutes():
    _poser("Combien d'habitants à Thiès ?", "conv-f")
    assert len(module_app.stockage.contexte("conv-f")) == 1
    plus_tard = datetime.now(UTC) + timedelta(minutes=31)
    assert module_app.stockage.contexte("conv-f", maintenant=plus_tard) == []
