"""Questions non résolues regroupées par thème (back-office)."""

from fastapi.testclient import TestClient
from gestukaay_backend import app as module_app
from gestukaay_backend.regroupement import regrouper


def ligne(question: str, recu: str = "2026-10-10T08:00:00", langue: str = "fr", motif: str = "hors_socle") -> dict:
    return {"question": question, "langue": langue, "motif": motif, "recu_le": recu, "reponse_id": f"r{abs(hash(question + recu))}"}


def test_meme_theme_quelle_que_soit_la_zone_ou_l_annee():
    groupes = regrouper([
        ligne("Chômage des jeunes à Dakar"),
        ligne("taux de chômage des jeunes à Kolda en 2024", "2026-10-10T09:00:00"),
        ligne("Combien de personnes parlent sérère ?", "2026-10-10T10:00:00"),
        ligne("chômage des jeunes à Dakar", "2026-10-10T11:00:00"),
    ])
    assert [g["occurrences"] for g in groupes] == [3, 1]
    chomage = groupes[0]
    assert chomage["theme"].startswith("chômage") and "jeune" in chomage["mots"]  # forme écrite, accents gardés
    # Exemples distincts, le plus récent d'abord ; la même question deux fois n'y figure qu'une
    assert [e["question"] for e in chomage["exemples"]] == ["chômage des jeunes à Dakar", "taux de chômage des jeunes à Kolda en 2024"]
    assert chomage["derniere"] == "2026-10-10T11:00:00" and chomage["motifs"] == {"hors_socle": 3}


def test_sans_mot_utile_et_langues():
    groupes = regrouper([ligne("Quel est le taux ?"), ligne("Ñaata la ?", langue="wo"), ligne("combien ?")])
    autres = next(g for g in groupes if g["theme"] == "autres questions")
    assert autres["occurrences"] >= 2
    assert sum(g["langues"].get("wo", 0) for g in groupes) == 1


def test_route_du_back_office(connecter, base_admin):
    client = TestClient(module_app.app)
    for q in ("Combien de personnes parlent sérère au Sénégal ?", "Combien de gens parlent sérère à Thiès ?",
              "Bonjour", "Combien d'habitants à Thiès ?"):
        client.post("/v1/ask", json={"question": q})
    assert client.get("/admin/non-resolues").status_code == 401
    connecter(client)
    r = client.get("/admin/non-resolues", params={"jours": 30}).json()
    serere = r["groupes"][0]
    assert serere["occurrences"] == 2 and "parlent" in serere["theme"] and "indicateurs_proches" in serere
    assert all("Thiès ?" != e["question"] for g in r["groupes"] for e in g["exemples"])  # une réponse exacte n'y est pas
    assert client.get("/admin/non-resolues", params={"jours": 12}).status_code == 422
    assert client.get("/admin/non-resolues", params={"issue": "approchee"}).json()["questions"] == 0
