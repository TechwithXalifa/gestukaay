"""Client LLM multi-fournisseur : une chaîne de maillons essayés dans l'ordre.

    client = charger_client()                      # depuis les variables d'environnement
    requete, appel = client.structurer(systeme, question, RequeteStructuree)

Chaque maillon a son délai (2 s par défaut, cahier 10.4), tenu pour de bon : au-delà, le maillon
est abandonné, même si le fournisseur continue d'envoyer des signaux d'attente (recette du 08/10 :
le délai de 3 s laissait passer jusqu'à 7,3 s). Un maillon échoue sur : délai dépassé, erreur réseau
ou HTTP, refus du fournisseur, JSON illisible, ou JSON non conforme au schéma Pydantic. On passe alors
au suivant. Si tous échouent : EchecLLM, et le moteur répond « incompréhension ».

Relais (LLM_<N>_RELAIS_S) : si le maillon N n'a pas répondu au bout de ce temps, le suivant part en
parallèle. La réponse du premier dans l'ordre de la chaîne reste préférée tant qu'il est dans son
délai : on garde le meilleur modèle quand il répond, et le plus rapide quand il tarde.

Le dernier recours peut être un maillon « regles » : une fonction locale,
sans réseau ni modèle (lexique + référentiel), branchée par le moteur (#10, #22).
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable, Mapping
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from .adaptateurs import ADAPTATEURS
from .base import Appel, Brut, EchecLLM, ErreurAdaptateur, Maillon, Tentative

M = TypeVar("M", bound=BaseModel)
# Fournisseurs qui exigent une clé (openai_compatible non : Ollama local n'en a pas)
CLE_OBLIGATOIRE = {"gemini", "anthropic", "huggingface"}
# Secours local : (système, utilisateur) -> dict, ou None si les règles ne savent pas répondre
Regles = Callable[[str, str], dict | None]


class ClientLLM:
    def __init__(self, chaine: list[Maillon], regles: Regles | None = None,
                 transport: httpx.BaseTransport | None = None):
        if not chaine:
            raise ValueError("chaîne LLM vide : définir LLM_CHAINE")
        self.chaine = chaine
        self.regles = regles
        self._transport = transport  # tests : httpx.MockTransport

    def structurer(self, systeme: str, utilisateur: str, modele: type[M]) -> tuple[M, Appel]:
        schema = modele.model_json_schema()
        appel = Appel()
        debut_appel = time.perf_counter()
        n = len(self.chaine)
        issues: dict[int, tuple[M, Brut] | ErreurAdaptateur] = {}  # maillon -> réponse validée ou échec
        lances: dict[int, tuple[Future, float]] = {}  # maillon réseau en cours -> (tâche, début)
        debuts: dict[int, float] = {}
        fins: dict[int, float] = {}

        def essai(m: Maillon) -> tuple[M, Brut]:
            brut = self._appeler(m, systeme, utilisateur, schema)
            return self._valider(brut.texte, modele), brut

        def lancer(i: int) -> None:
            debuts[i] = time.perf_counter()
            if self.chaine[i].fournisseur == "regles":  # local et immédiat : pas de fil
                try:
                    issues[i] = essai(self.chaine[i])
                except ErreurAdaptateur as e:
                    issues[i] = e
                fins[i] = time.perf_counter()
            else:
                lances[i] = (pool.submit(essai, self.chaine[i]), debuts[i])

        pool = ThreadPoolExecutor(max_workers=n, thread_name_prefix="llm")
        try:
            while True:
                # le premier maillon (dans l'ordre) qui n'a pas échoué décide
                j = next((i for i in range(n) if not isinstance(issues.get(i), ErreurAdaptateur)), None)
                if j is None:
                    break
                if j in issues:
                    return self._bilan(appel, j, issues, debuts, fins, debut_appel)
                if j not in debuts:
                    lancer(j)
                    continue
                # attendre : une réponse, une échéance, ou le moment de passer le relais
                maintenant = time.perf_counter()
                echeances = [d + self.chaine[i].delai_s for i, (_, d) in lances.items()]
                dernier = max(debuts)
                suivant = dernier + 1
                relais = self.chaine[dernier].relais_s
                if relais is not None and suivant < n and suivant not in debuts and dernier not in issues:
                    echeances.append(debuts[dernier] + relais)
                attente = max(0.0, min(echeances) - maintenant) if echeances else None
                faits, _ = wait([f for f, _ in lances.values()], timeout=attente, return_when=FIRST_COMPLETED)
                maintenant = time.perf_counter()
                for i, (f, d) in list(lances.items()):
                    if f in faits:
                        try:
                            issues[i] = f.result()
                        except ErreurAdaptateur as e:
                            issues[i] = e
                    elif maintenant - d >= self.chaine[i].delai_s:
                        issues[i] = ErreurAdaptateur("delai", f"délai total de {self.chaine[i].delai_s:g} s dépassé")
                    else:
                        continue
                    fins[i] = maintenant
                    del lances[i]
                if (relais is not None and suivant < n and suivant not in debuts and dernier not in issues
                        and maintenant - debuts[dernier] >= relais):
                    lancer(suivant)
        finally:
            pool.shutdown(wait=False, cancel_futures=True)  # un maillon abandonné finit seul, sans nous retenir
        self._noter(appel, issues, debuts, fins, debut_appel)
        raise EchecLLM(appel)

    def _bilan(self, appel: Appel, j: int, issues: dict, debuts: dict, fins: dict, debut_appel: float):
        objet, brut = issues[j]
        m = self.chaine[j]
        self._noter(appel, issues, debuts, fins, debut_appel)
        appel.maillon, appel.fournisseur, appel.modele = m.nom, m.fournisseur, brut.modele or m.modele
        appel.jetons_entree, appel.jetons_sortie = brut.jetons_entree, brut.jetons_sortie
        appel.cout_usd = brut.cout_usd if brut.cout_usd is not None else self._cout(m, brut)
        return objet, appel

    def _noter(self, appel: Appel, issues: dict, debuts: dict, fins: dict, debut_appel: float) -> None:
        """Une tentative par maillon lancé, dans l'ordre de la chaîne ; durée réelle de l'appel."""
        fin_appel = time.perf_counter()
        for i in sorted(debuts):
            m, issue = self.chaine[i], issues.get(i)
            statut, detail = ("abandon", "un maillon préféré a répondu") if issue is None else (
                (issue.statut, str(issue)) if isinstance(issue, ErreurAdaptateur) else ("ok", ""))
            fin = fins.get(i, fin_appel)
            appel.tentatives.append(Tentative(maillon=m.nom, fournisseur=m.fournisseur, modele=m.modele,
                                              statut=statut, latence_ms=round((fin - debuts[i]) * 1000),
                                              detail=detail[:300]))
        appel.latence_ms = round((fin_appel - debut_appel) * 1000)

    # ------------------------------------------------------------------

    def _appeler(self, m: Maillon, systeme: str, utilisateur: str, schema: dict) -> Brut:
        if m.fournisseur == "regles":
            if self.regles is None:
                raise ErreurAdaptateur("indisponible", "aucune règle locale branchée")
            d = self.regles(systeme, utilisateur)
            if d is None:
                raise ErreurAdaptateur("indisponible", "règles sans réponse")
            return Brut(texte=json.dumps(d, ensure_ascii=False), modele="regles")
        if not m.cle and m.fournisseur in CLE_OBLIGATOIRE:
            raise ErreurAdaptateur("indisponible", f"clé absente : définir LLM_{m.nom.upper()}_CLE")
        with httpx.Client(timeout=m.delai_s, transport=self._transport) as client:
            return ADAPTATEURS[m.fournisseur](client, m, systeme, utilisateur, schema)

    @staticmethod
    def _valider(texte: str, modele: type[M]) -> M:
        t = texte.strip()
        if t.startswith("```"):  # certains modèles entourent le JSON d'un bloc de code
            t = t.strip("`").removeprefix("json").strip()
        try:
            donnees = json.loads(t)
        except ValueError as e:
            raise ErreurAdaptateur("json", t[:120]) from e
        try:
            return modele.model_validate(donnees)
        except ValidationError as e:
            raise ErreurAdaptateur("schema", str(e.errors()[:2])) from e

    @staticmethod
    def _cout(m: Maillon, b: Brut) -> float | None:
        if m.prix_entree is None or m.prix_sortie is None or b.jetons_entree is None:
            return None
        return (b.jetons_entree * m.prix_entree + (b.jetons_sortie or 0) * m.prix_sortie) / 1e6


# --------------------------------------------------------------------------
# Configuration par variables d'environnement
# --------------------------------------------------------------------------

def _flottant(v: str | None) -> float | None:
    return float(v) if v not in (None, "") else None


def lire_chaine(env: Mapping[str, str] = os.environ) -> list[Maillon]:
    """LLM_CHAINE=principal,repli,secours puis, pour chaque nom N :
    LLM_N_FOURNISSEUR, LLM_N_MODELE, LLM_N_CLE, LLM_N_URL, LLM_N_DELAI_S, LLM_N_RELAIS_S,
    LLM_N_TEMPERATURE (« aucune » pour ne pas l'envoyer), LLM_N_JSON,
    LLM_N_PRIX_ENTREE, LLM_N_PRIX_SORTIE ($ par million de jetons),
    LLM_N_HEBERGEURS (OpenRouter : « cerebras,groq »), LLM_N_TRI (« latency »…),
    LLM_N_RAISONNEMENT (OpenRouter : « non », « minimal », « low »… ; Gemini direct : « non » seulement, les autres
    valeurs y sont ignorées)."""
    noms = [n.strip() for n in env.get("LLM_CHAINE", "").split(",") if n.strip()]
    delai_defaut = float(env.get("LLM_DELAI_S", "2"))
    chaine = []
    for nom in noms:
        p = f"LLM_{nom.upper()}_"
        fournisseur = env.get(p + "FOURNISSEUR", "")
        if fournisseur not in (*ADAPTATEURS, "regles"):
            raise ValueError(f"{p}FOURNISSEUR invalide : {fournisseur!r} "
                             f"(attendu : {', '.join((*ADAPTATEURS, 'regles'))})")
        if fournisseur != "regles" and not env.get(p + "MODELE"):
            raise ValueError(f"{p}MODELE manquant")
        temp = env.get(p + "TEMPERATURE", "0")
        chaine.append(Maillon(
            nom=nom, fournisseur=fournisseur, modele=env.get(p + "MODELE", ""),
            cle=env.get(p + "CLE", ""), url=env.get(p + "URL", ""),
            delai_s=float(env.get(p + "DELAI_S") or delai_defaut),
            relais_s=_flottant(env.get(p + "RELAIS_S")),
            temperature=None if temp.lower() == "aucune" else float(temp),
            mode_json=env.get(p + "JSON") or None,
            prix_entree=_flottant(env.get(p + "PRIX_ENTREE")),
            prix_sortie=_flottant(env.get(p + "PRIX_SORTIE")),
            hebergeurs=tuple(h.strip() for h in env.get(p + "HEBERGEURS", "").split(",") if h.strip()),
            tri=env.get(p + "TRI") or None,
            raisonnement=env.get(p + "RAISONNEMENT") or None,
        ))
    return chaine


def charger_client(regles: Regles | None = None, env: Mapping[str, str] = os.environ) -> ClientLLM:
    return ClientLLM(lire_chaine(env), regles=regles)
