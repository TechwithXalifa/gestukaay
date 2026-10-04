"""Persistance du backend : réponses, journal des requêtes, retours.

    GESTUKAAY_BASE=postgresql://gestukaay:…@db:5432/gestukaay   # Docker, préprod
    GESTUKAAY_BASE=sqlite:///gestukaay.db                       # un fichier en local
    (non définie)                                               # SQLite en mémoire

Le moteur ne stocke rien (contrat-v1 §7) : c'est ici que vivent les réponses
(pour l'URL stable /r/{id}, EF-29), le journal (back-office) et les retours.
Aucune donnée personnelle : la conversation n'est connue que par un hachage
salé, et « Où je me situe » n'est jamais journalisé (EF-40).

sqlite3 (bibliothèque standard) et psycopg seulement : psycopg n'est importé
que pour une base PostgreSQL.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
import statistics
import threading
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from gestukaay_contracts.models import AskRequest, AskResponse, FeedbackRequest, RequeteStructuree

_TABLES = [
    """CREATE TABLE IF NOT EXISTS reponses (
        id TEXT PRIMARY KEY,
        cree_le TEXT NOT NULL,
        contenu TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS journal (
        reponse_id TEXT PRIMARY KEY,
        recu_le TEXT NOT NULL,
        canal TEXT NOT NULL,
        source TEXT NOT NULL,
        langue TEXT NOT NULL,
        question TEXT NOT NULL,
        transcription_brute TEXT,
        issue TEXT NOT NULL,
        indicateur TEXT,
        latence_ms INTEGER,
        version_socle TEXT NOT NULL,
        conversation TEXT,
        confirme_depuis TEXT
    )""",
    "CREATE INDEX IF NOT EXISTS journal_recu_le ON journal (recu_le)",
    # Webhooks WhatsApp / Telegram : un même message n'est jamais traité deux fois (10.7), purgé à 48 h
    """CREATE TABLE IF NOT EXISTS messages_recus (
        canal TEXT NOT NULL,
        message_id TEXT NOT NULL,
        recu_le TEXT NOT NULL,
        PRIMARY KEY (canal, message_id)
    )""",
    # Exécutions du benchmark lancées depuis le back-office (jeu_de_test.py)
    """CREATE TABLE IF NOT EXISTS executions_benchmark (
        id TEXT PRIMARY KEY,
        mode TEXT NOT NULL,
        lancee_le TEXT NOT NULL,
        statut TEXT NOT NULL,
        erreur TEXT,
        resultat TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS retours (
        reponse_id TEXT NOT NULL,
        recu_le TEXT NOT NULL,
        type TEXT NOT NULL,
        vote TEXT,
        motif TEXT,
        commentaire TEXT
    )""",
]

# Suivi de conversation (décision 0021) : 3 derniers échanges, oubliés après 30 min sans échange
ECHANGES_SUIVI = 3
EXPIRATION_SUIVI = timedelta(minutes=30)
# Unicité des messages des webhooks : Meta renvoie un message non acquitté pendant 24 h au plus
CONSERVATION_MESSAGES = timedelta(hours=48)

COLONNES_JOURNAL = ["recu_le", "canal", "source", "langue", "question", "transcription_brute", "issue",
                    "indicateur", "latence_ms", "version_socle", "conversation", "confirme_depuis", "reponse_id"]


@dataclass(frozen=True)
class FiltreJournal:
    issue: str | None = None
    canal: str | None = None
    langue: str | None = None
    texte: str | None = None
    limite: int = 50
    decalage: int = 0


class Stockage:
    def __init__(self, url: str | None = None):
        url = url if url is not None else os.environ.get("GESTUKAAY_BASE", "")
        # Sel du hachage des conversations : fixe en préprod pour suivre une conversation
        # d'un redémarrage à l'autre ; tiré au hasard sinon.
        self._sel = os.environ.get("GESTUKAAY_SEL") or secrets.token_hex(16)
        self._verrou = threading.Lock()
        if url.startswith(("postgresql://", "postgres://")):
            import psycopg

            self._pg = True
            self._url = url
            self._cx = psycopg.connect(url, autocommit=True)
        else:
            self._pg = False
            chemin = url.removeprefix("sqlite:///") if url.startswith("sqlite:///") else ":memory:"
            self._cx = sqlite3.connect(chemin, check_same_thread=False, isolation_level=None)
        with self._curseur() as c:
            for sql in _TABLES:
                c.execute(sql)

    @contextmanager
    def _curseur(self) -> Iterator:
        # Une connexion partagée, protégée par un verrou : largement assez pour le hackathon.
        with self._verrou:
            c = self._cx.cursor()
            try:
                yield c
            finally:
                c.close()

    def _sql(self, sql: str) -> str:
        return sql.replace("?", "%s") if self._pg else sql

    def _executer(self, sql: str, params: tuple = ()) -> list[tuple]:
        try:
            return self._une_fois(sql, params)
        except Exception as e:
            if not self._pg:
                raise
            import psycopg

            if not isinstance(e, psycopg.OperationalError):  # AdminShutdown, connexion fermée…
                raise
            # Connexion perdue (la base a redémarré) : on se reconnecte et on réessaie une fois
            with self._verrou:
                self._cx = psycopg.connect(self._url, autocommit=True)
            return self._une_fois(sql, params)

    def _une_fois(self, sql: str, params: tuple) -> list[tuple]:
        with self._curseur() as c:
            c.execute(self._sql(sql), params)
            return c.fetchall() if c.description else []

    # ------------------------------------------------------------------ réponses

    def enregistrer(self, rep: AskResponse, req: AskRequest | None = None, confirme_depuis: str | None = None) -> None:
        r = rep.reponse
        self._executer(
            "INSERT INTO reponses (id, cree_le, contenu) VALUES (?, ?, ?)",
            (r.id, r.cree_le.isoformat(), rep.model_dump_json()),
        )
        indicateur = r.requete.indicateur if r.requete else None
        canal, source, conversation = "web", "texte", None
        if req:
            canal, source = req.canal, req.source
            conversation = self.hacher(req.conversation_id) if req.conversation_id else None
        elif confirme_depuis:  # un choix confirmé reste dans le canal et la conversation d'origine
            origine = self._executer("SELECT canal, source, conversation FROM journal WHERE reponse_id = ?",
                                     (confirme_depuis,))
            if origine:
                canal, source, conversation = origine[0]
        self._executer(
            f"INSERT INTO journal ({', '.join(COLONNES_JOURNAL)}) VALUES ({', '.join('?' * len(COLONNES_JOURNAL))})",
            (
                # millisecondes : ordonne les échanges rapides d'une même conversation (suivi, 0021)
                datetime.now(UTC).isoformat(timespec="milliseconds"),
                canal,
                source,
                r.langue,
                r.question,
                req.transcription_brute if req else None,
                r.issue,
                indicateur,
                r.latence_ms,
                r.version_socle,
                conversation,
                confirme_depuis,
                r.id,
            ),
        )

    def lire(self, rid: str) -> AskResponse | None:
        lignes = self._executer("SELECT contenu FROM reponses WHERE id = ?", (rid,))
        return AskResponse.model_validate_json(lignes[0][0]) if lignes else None

    def contexte(self, conversation_id: str, maintenant: datetime | None = None) -> list[RequeteStructuree | None]:
        """Requêtes des 3 derniers échanges de la conversation, du plus ancien au plus récent, pour
        « et Kaolack ? » (EF-09, décision 0021). Rien si le dernier échange date de plus de 30 min.
        Une réponse approchée confirmée compte pour son choix confirmé (la réponse approchée elle-même
        est écartée) ; une incompréhension donne None. Lu dans le journal : aucune table de plus."""
        lignes = self._executer(
            """SELECT j.recu_le, r.contenu FROM journal j JOIN reponses r ON r.id = j.reponse_id
               WHERE j.conversation = ? AND j.reponse_id NOT IN
                     (SELECT c.confirme_depuis FROM journal c WHERE c.confirme_depuis IS NOT NULL)
               ORDER BY j.recu_le DESC LIMIT ?""",
            (self.hacher(conversation_id), ECHANGES_SUIVI),
        )
        if not lignes:
            return []
        maintenant = maintenant or datetime.now(UTC)
        if maintenant - datetime.fromisoformat(lignes[0][0]) > EXPIRATION_SUIVI:
            return []
        return [AskResponse.model_validate_json(contenu).reponse.requete for _, contenu in reversed(lignes)]

    def derniere(self, conversation_id: str) -> AskResponse | None:
        """Dernière réponse d'une conversation (un « 1 » sur WhatsApp confirme le choix qu'elle propose)."""
        lignes = self._executer(
            "SELECT reponse_id FROM journal WHERE conversation = ? ORDER BY recu_le DESC LIMIT 1",
            (self.hacher(conversation_id),))
        return self.lire(lignes[0][0]) if lignes else None

    def premier_passage(self, canal: str, message_id: str, maintenant: datetime | None = None) -> bool:
        """Vrai la première fois qu'un message arrive, faux s'il a déjà été reçu (Meta et Telegram
        renvoient un message tant qu'il n'est pas acquitté). Purge au passage ce qui a plus de 48 h."""
        maintenant = maintenant or datetime.now(UTC)
        self._executer("DELETE FROM messages_recus WHERE recu_le < ?",
                       ((maintenant - CONSERVATION_MESSAGES).isoformat(timespec="seconds"),))
        return bool(self._executer(
            "INSERT INTO messages_recus (canal, message_id, recu_le) VALUES (?, ?, ?) "
            "ON CONFLICT DO NOTHING RETURNING message_id",
            (canal, message_id, maintenant.isoformat(timespec="seconds"))))

    def hacher(self, conversation_id: str) -> str:
        return hashlib.sha256(f"{self._sel}:{conversation_id}".encode()).hexdigest()[:16]

    # ------------------------------------------------------------------ retours

    def retour(self, req: FeedbackRequest) -> None:
        self._executer(
            "INSERT INTO retours (reponse_id, recu_le, type, vote, motif, commentaire) VALUES (?, ?, ?, ?, ?, ?)",
            (req.reponse_id, datetime.now(UTC).isoformat(timespec="seconds"), req.type, req.vote, req.motif,
             req.commentaire),
        )

    # ------------------------------------------------------------------ journal

    def journal(self, f: FiltreJournal) -> tuple[int, list[dict]]:
        """(nombre total filtré, page de lignes, plus récentes d'abord), avec le vote et le
        signalement éventuels de chaque réponse."""
        conditions, params = [], []
        for colonne in ("issue", "canal", "langue"):
            if valeur := getattr(f, colonne):
                conditions.append(f"j.{colonne} = ?")
                params.append(valeur)
        if f.texte:
            conditions.append("LOWER(j.question) LIKE ?")
            params.append(f"%{f.texte.lower()}%")
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        total = self._executer(f"SELECT COUNT(*) FROM journal j {where}", tuple(params))[0][0]
        lignes = self._executer(
            f"""SELECT {', '.join('j.' + c for c in COLONNES_JOURNAL)},
                       (SELECT r.vote FROM retours r WHERE r.reponse_id = j.reponse_id AND r.type = 'vote'
                        ORDER BY r.recu_le DESC LIMIT 1),
                       (SELECT r.motif FROM retours r WHERE r.reponse_id = j.reponse_id
                        AND r.type = 'signalement' ORDER BY r.recu_le DESC LIMIT 1),
                       (SELECT COUNT(*) FROM retours r WHERE r.reponse_id = j.reponse_id
                        AND r.type = 'suggestion_indicateur')
                FROM journal j {where} ORDER BY j.recu_le DESC, j.reponse_id LIMIT ? OFFSET ?""",
            (*params, f.limite, f.decalage),
        )
        return total, [dict(zip([*COLONNES_JOURNAL, "vote", "signalement", "suggestions"], ligne, strict=True)) for ligne in lignes]

    # ------------------------------------------------------------------ tableau de bord

    def tableau(self, jours: int = 30, canal: str | None = None, langue: str | None = None,
                maintenant: datetime | None = None) -> dict:
        """Indicateurs de qualité du back-office (US-28, maquette BO-Tableau), calculés sur le journal.
        Une confirmation de choix n'est pas une question de plus : seules les questions posées comptent.
        L'exactitude et les refus pertinents viennent du benchmark (mesure/), pas d'ici."""
        maintenant = maintenant or datetime.now(UTC)
        debut, avant = maintenant - timedelta(days=jours), maintenant - timedelta(days=2 * jours)
        lignes = self._executer(
            "SELECT recu_le, canal, langue, issue, latence_ms, question, reponse_id FROM journal "
            "WHERE recu_le >= ? AND confirme_depuis IS NULL", (avant.isoformat(timespec="milliseconds"),))
        garder = [lg for lg in lignes if (not canal or lg[1] == canal) and (not langue or lg[2] == langue)]
        courantes = [lg for lg in garder if datetime.fromisoformat(lg[0]) >= debut]
        precedentes = len(garder) - len(courantes)
        total = len(courantes)

        latences = sorted(lg[4] for lg in courantes if lg[4] is not None)
        p95 = latences[min(len(latences) - 1, int(0.95 * len(latences)))] if latences else None
        issues = Counter(lg[3] for lg in courantes)

        ids = {lg[6] for lg in courantes}
        votes: dict[str, tuple[str, str]] = {}  # dernier vote de chaque réponse
        signalements = 0
        for rid, recu, type_, vote in self._executer(
                "SELECT reponse_id, recu_le, type, vote FROM retours WHERE recu_le >= ?",
                (debut.isoformat(timespec="seconds"),)):
            if rid not in ids:
                continue
            if type_ == "vote" and vote and (rid not in votes or recu >= votes[rid][0]):
                votes[rid] = (recu, vote)
            signalements += type_ == "signalement"
        utiles = sum(v == "utile" for _, v in votes.values())

        par_jour = Counter(datetime.fromisoformat(lg[0]).date().isoformat() for lg in courantes)
        jours_liste = [(debut + timedelta(days=i + 1)).date().isoformat() for i in range(jours)]

        # Questions non résolues (refus), regroupées par question normalisée, les plus fréquentes d'abord
        refus = [lg for lg in courantes if lg[3] == "aucune"]
        motifs: dict[str, str] = {}
        for rid in {lg[6] for lg in refus}:
            contenu = self._executer("SELECT contenu FROM reponses WHERE id = ?", (rid,))
            if contenu:
                motifs[rid] = json.loads(contenu[0][0])["reponse"].get("motif", "")
        groupes: dict[str, dict] = {}
        for lg in refus:
            cle = " ".join(lg[5].lower().split())
            g = groupes.setdefault(cle, {"question": lg[5], "langue": lg[2], "motif": motifs.get(lg[6], ""),
                                         "occurrences": 0})
            g["occurrences"] += 1

        return {
            "jours": jours,
            "questions": total,
            "questions_periode_precedente": precedentes,
            "issues": {k: issues.get(k, 0) for k in ("exacte", "approchee", "aucune")},
            "latence_mediane_ms": round(statistics.median(latences)) if latences else None,
            "latence_p95_ms": p95,
            "part_wolof": round(sum(lg[2] == "wo" for lg in courantes) / total, 3) if total else None,
            "votes": len(votes),
            "satisfaction": round(utiles / len(votes), 3) if votes else None,
            "signalements": signalements,
            "par_jour": [{"jour": j, "questions": par_jour.get(j, 0)} for j in jours_liste],
            "non_resolues": sorted(groupes.values(), key=lambda g: (-g["occurrences"], g["question"]))[:10],
        }

    # ------------------------------------------------------------------ jeu de test

    def creer_execution(self, mode: str) -> str:
        eid = secrets.token_hex(6)
        self._executer("INSERT INTO executions_benchmark (id, mode, lancee_le, statut) VALUES (?, ?, ?, 'en_cours')",
                       (eid, mode, datetime.now(UTC).isoformat(timespec="seconds")))
        return eid

    def terminer_execution(self, eid: str, resultat: dict | None, erreur: str | None = None) -> None:
        self._executer("UPDATE executions_benchmark SET statut = ?, resultat = ?, erreur = ? WHERE id = ?",
                       ("terminee" if resultat is not None else "echec",
                        json.dumps(resultat, ensure_ascii=False) if resultat is not None else None, erreur, eid))

    def executions(self) -> list[dict]:
        """Les exécutions, plus récentes d'abord, avec leur résultat complet (None si en cours ou en échec)."""
        lignes = self._executer(
            "SELECT id, mode, lancee_le, statut, erreur, resultat FROM executions_benchmark ORDER BY lancee_le DESC, id")
        return [{"id": i, "mode": m, "lancee_le": d, "statut": st, "erreur": e,
                 "resultat": json.loads(r) if r else None} for i, m, d, st, e, r in lignes]
