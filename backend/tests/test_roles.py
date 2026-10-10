"""Comptes et rôles du back-office (V1.1) : administrateur, linguiste, lecteur."""

import sqlite3

from fastapi.testclient import TestClient
from gestukaay_backend import app as module_app
from gestukaay_backend import comptes
from gestukaay_backend.stockage import Stockage

MDP = "mot-de-passe-de-test-12"


def test_un_administrateur_cree_un_linguiste_qui_consulte_sans_gerer(connecter, base_admin):
    admin = TestClient(module_app.app)
    connecter(admin)
    assert admin.get("/admin/moi").json() == {"identifiant": "SAN", "role": "admin"}
    r = admin.post("/admin/comptes", json={"identifiant": "Awa", "mot_de_passe": MDP, "role": "linguiste"})
    assert r.status_code == 201
    liste = admin.get("/admin/comptes").json()
    assert {c["identifiant"]: c["role"] for c in liste["comptes"]} == {"Awa": "linguiste", "SAN": "admin"}
    assert "hachage" not in str(liste) and set(liste["roles"]) == {"admin", "linguiste", "lecteur"}

    awa = TestClient(module_app.app)
    assert awa.post("/admin/connexion", json={"identifiant": "Awa", "mot_de_passe": MDP}).json()["role"] == "linguiste"
    assert awa.get("/admin/journal").status_code == 200 and awa.get("/admin/tableau").status_code == 200
    r = awa.get("/admin/comptes")
    assert r.status_code == 403 and r.json()["title"] == "Réservé aux administrateurs"
    assert awa.post("/admin/comptes", json={"identifiant": "X1", "mot_de_passe": MDP, "role": "admin"}).status_code == 403
    assert awa.post("/admin/jeu-de-test/executions", json={"mode": "regles"}).status_code == 403


def test_garde_fous(connecter, base_admin):
    admin = TestClient(module_app.app)
    connecter(admin)
    # Le dernier administrateur ne perd ni son rôle ni son compte ; personne ne se désactive soi-même
    assert admin.post("/admin/comptes/SAN/role", json={"role": "lecteur"}).status_code == 409
    assert admin.post("/admin/comptes/SAN/desactiver").status_code == 409
    assert admin.post("/admin/comptes", json={"identifiant": "a b", "mot_de_passe": MDP, "role": "lecteur"}).status_code == 422
    assert admin.post("/admin/comptes", json={"identifiant": "Bob", "mot_de_passe": "court", "role": "lecteur"}).status_code == 422
    assert admin.post("/admin/comptes", json={"identifiant": "san", "mot_de_passe": MDP, "role": "lecteur"}).status_code == 409
    assert admin.post("/admin/comptes", json={"identifiant": "Bob", "mot_de_passe": MDP, "role": "chef"}).status_code == 422
    assert admin.post("/admin/comptes/Inconnu/role", json={"role": "lecteur"}).status_code == 404

    # Avec un second administrateur, le premier peut changer de rôle
    admin.post("/admin/comptes", json={"identifiant": "KBD", "mot_de_passe": MDP, "role": "admin"})
    assert admin.post("/admin/comptes/KBD/desactiver").status_code == 204
    assert admin.post("/admin/comptes/KBD/mot-de-passe", json={"mot_de_passe": MDP}).status_code == 204  # réactive
    assert next(c for c in base_admin.comptes() if c["identifiant"] == "KBD")["actif"] is True
    assert admin.post("/admin/comptes/SAN/role", json={"role": "lecteur"}).status_code == 204
    assert admin.get("/admin/comptes").status_code == 403  # SAN n'est plus administrateur


def test_une_base_d_avant_les_roles_garde_ses_administrateurs(tmp_path):
    chemin = tmp_path / "ancienne.db"
    cx = sqlite3.connect(chemin)
    cx.execute("CREATE TABLE comptes_admin (identifiant TEXT PRIMARY KEY, hachage TEXT NOT NULL, cree_le TEXT NOT NULL, "
               "actif INTEGER NOT NULL DEFAULT 1, echecs INTEGER NOT NULL DEFAULT 0, bloque_jusqu_a TEXT)")
    cx.execute("INSERT INTO comptes_admin (identifiant, hachage, cree_le) VALUES ('SAN', 'h', '2026-10-01')")
    cx.commit()
    cx.close()
    st = Stockage(f"sqlite:///{chemin}")
    assert st.compte("SAN")["role"] == "admin"
    Stockage(f"sqlite:///{chemin}")  # une seconde ouverture ne refait pas la migration


def test_ligne_de_commande(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("GESTUKAAY_BASE", f"sqlite:///{tmp_path / 'cli.db'}")
    monkeypatch.setenv("GESTUKAAY_MOT_DE_PASSE", MDP)
    comptes.main(["creer", "Awa", "--role", "lecteur"])
    comptes.main(["role", "Awa", "linguiste"])
    comptes.main(["lister"])
    sortie = capsys.readouterr().out
    assert "Compte Awa créé (lecteur)." in sortie and "Awa\tlinguiste\tactif" in sortie
