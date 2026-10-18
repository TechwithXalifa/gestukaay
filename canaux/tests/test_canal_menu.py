"""Menu à boutons de WhatsApp et Telegram (menu.py) : thèmes, régions, questions qui partent au moteur."""

import json

import httpx
from gestukaay_canaux import menu, telegram, whatsapp
from gestukaay_canaux.conversation import traiter
from gestukaay_canaux.textes import commande, texte
from test_canal_conversation import Envoyeur, entrant, services


class EnvoyeurMenu(Envoyeur):
    def menu(self, destinataire, message, boutons):
        self.envois.append(("menu", (message, [b.id for b in boutons])))


def test_themes_questions_et_regions_par_pages():
    themes = menu.themes()
    assert [b.libelle for b in themes.boutons][:2] == ["Population", "Emploi"] and len(themes.boutons) == 8
    population = menu.reagir("menu-t0")
    assert population.complement == "Population" and population.boutons[0].id == "menu-q0-0"
    assert menu.reagir("menu-q0-0") == "Combien d'habitants à Thiès ?"
    page1, page2 = menu.liste_regions(0), menu.reagir("menu-rp1")
    assert len(page1.boutons) == len(page2.boutons) == 8  # 7 régions et le bouton de page
    assert page1.boutons[-1].id == "menu-rp1" and page2.boutons[-1].id == "menu-rp0"
    kolda = menu.reagir("menu-r-SN-KD")
    assert kolda.complement == "Kolda" and kolda.boutons[1].libelle == "Quel est le taux de pauvreté à Kolda ?"
    assert menu.reagir("menu-rq-SN-KD-1") == "Quel est le taux de pauvreté à Kolda ?"
    for inconnu in ("menu-t99", "menu-q0-9", "menu-r-SN-XX", "menu-rq-SN-KD-x", "menu-z"):
        assert menu.reagir(inconnu) is None


def test_limites_des_canaux():
    """Telegram : 64 octets par identifiant ; WhatsApp : 10 lignes par liste."""
    menus = [menu.themes(), menu.liste_regions(0), menu.liste_regions(1)]
    menus += [menu.reagir(f"menu-t{i}") for i in range(len(menu.THEMES))]
    menus += [menu.reagir(f"menu-r-{code}") for code, _ in menu.regions()]
    for m in menus:
        assert len(m.boutons) <= 10 and all(len(b.id.encode()) <= 64 for b in m.boutons)


def test_commandes_du_menu():
    assert commande("menu") == commande("/themes") == commande("Thèmes") == "themes"
    assert commande("/region") == commande("ma région") == "regions"
    assert texte("menu_themes", "fr") == "Choisissez un thème :"


def test_conversation_menu_puis_question():
    e, (s, _) = EnvoyeurMenu(), services(derniere=None)
    traiter(entrant(type="texte", texte="menu"), s, e)
    [(_, (message, ids))] = [x for x in e.envois if x[0] == "menu"]
    assert message.startswith("Choisissez un thème") and ids[0] == "menu-t0"
    # Un toucher dans le menu : pas d'accueil, puis le sous-menu ; une question touchée part au moteur
    e2, (s2, appels2) = EnvoyeurMenu(), services(derniere=None)
    traiter(entrant(type="menu", texte="menu-t5"), s2, e2)
    assert texte("accueil") not in e2.textes()
    assert next(x for x in e2.envois if x[0] == "menu")[1][0] == "Pauvreté : touchez une question."
    traiter(entrant(type="menu", texte="menu-q5-0"), s2, e2)
    assert appels2 == [("demander", "Quel est le taux de pauvreté à Kolda ?", {})]
    assert "463" in e2.textes()[-1]  # la réponse du moteur (faux : population de Thiès)
    traiter(entrant(type="menu", texte="menu-ancien"), s2, e2)
    assert e2.textes()[-1] == texte("aide")


def test_boutons_refuses_la_liste_part_en_texte():
    class Refus(EnvoyeurMenu):
        def menu(self, destinataire, message, boutons):
            raise RuntimeError("boutons refusés")

    e, (s, _) = Refus(), services(derniere=None)
    traiter(entrant(type="menu", texte="menu-t0"), s, e)
    assert e.textes()[-1].startswith("Population : touchez une question.\n• Combien d'habitants à Thiès ?")


def test_telegram_lit_et_envoie_le_menu(monkeypatch):
    rappel = {"update_id": 9, "callback_query": {"id": "cb1", "data": "menu-t3", "message": {"chat": {"id": 6}}}}
    [c] = telegram.lire(rappel)
    assert (c.contenu.type, c.contenu.texte, c.contenu.accuse) == ("menu", "menu-t3", "cb1")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    corps = []
    client = telegram.ClientTelegram(httpx.MockTransport(lambda r: corps.append(json.loads(r.content)) or
                                                         httpx.Response(200, json={"result": {}})))
    client.menu("6", "Choisissez un thème :", list(menu.themes().boutons))
    clavier = corps[0]["reply_markup"]["inline_keyboard"]
    assert len(clavier[0]) == 2 and clavier[0][0] == {"text": "Population", "callback_data": "menu-t0"}
    client.menu("6", "Population : touchez une question.", list(menu.reagir("menu-t0").boutons))
    assert all(len(ligne) == 1 for ligne in corps[1]["reply_markup"]["inline_keyboard"])  # questions : une par ligne
    client.declarer_commandes()
    assert [c["command"] for c in corps[2]["commands"]] == ["themes", "region"]


def test_whatsapp_lit_et_envoie_le_menu(monkeypatch):
    m = {"from": "221700000001", "id": "wamid.M", "type": "interactive",
         "interactive": {"type": "list_reply", "list_reply": {"id": "menu-r-SN-KD", "title": "Kolda"}}}
    [c] = whatsapp.lire({"entry": [{"changes": [{"value": {"messages": [m]}}]}]})
    assert (c.contenu.type, c.contenu.texte) == ("menu", "menu-r-SN-KD")
    monkeypatch.setenv("WHATSAPP_TOKEN", "jeton-meta")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "1331556276698765")
    corps = []
    client = whatsapp.ClientGraph(httpx.MockTransport(lambda r: corps.append(json.loads(r.content)) or
                                                      httpx.Response(200, json={"messages": [{"id": "x"}]})))
    client.menu("221700000001", "Kolda : touchez une question.", list(menu.reagir("menu-r-SN-KD").boutons))
    lignes = corps[0]["interactive"]["action"]["sections"][0]["rows"]
    assert len(lignes) == 4 and all(len(x["title"]) <= 24 for x in lignes)
    assert lignes[1]["description"] == "Quel est le taux de pauvreté à Kolda ?"  # titre coupé : libellé entier dessous
