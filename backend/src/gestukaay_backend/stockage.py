"""Persistance du backend : réponses, journal des requêtes, retours, comptes du back-office.

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
import logging
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
    # Back-office (comptes.py, décision 0037) : comptes nominatifs, mots de passe hachés par scrypt
    """CREATE TABLE IF NOT EXISTS comptes_admin (
        identifiant TEXT PRIMARY KEY,
        hachage TEXT NOT NULL,
        cree_le TEXT NOT NULL,
        actif INTEGER NOT NULL DEFAULT 1,
        echecs INTEGER NOT NULL DEFAULT 0,
        bloque_jusqu_a TEXT
    )""",
    # Sessions : seul le hachage du jeton est gardé (une base copiée n'ouvre aucune session)
    # Réglages de la base : le sel du hachage des conversations, s'il n'est pas donné par GESTUKAAY_SEL
    """CREATE TABLE IF NOT EXISTS parametres (
        cle TEXT PRIMARY KEY,
        valeur TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS sessions_admin (
        jeton TEXT PRIMARY KEY,
        identifiant TEXT NOT NULL,
        ouverte_le TEXT NOT NULL,
        vue_le TEXT NOT NULL
    )""",
    # Clés de l'API publique (développeurs) : seule l'empreinte est gardée, la clé n'est montrée qu'une fois
    """CREATE TABLE IF NOT EXISTS cles_api (
        id TEXT PRIMARY KEY,
        nom TEXT NOT NULL,
        empreinte TEXT NOT NULL UNIQUE,
        creee_le TEXT NOT NULL,
        creee_par TEXT NOT NULL,
        active INTEGER NOT NULL DEFAULT 1,
        vue_le TEXT,
        appels INTEGER NOT NULL DEFAULT 0
    )""",
    # Relecture des signalements et des suggestions d'indicateur (back-office) : un retour se repère par
    # (réponse, date, type), la table des retours n'ayant pas d'identifiant propre
    """CREATE TABLE IF NOT EXISTS suivi_retours (
        reponse_id TEXT NOT NULL,
        recu_le TEXT NOT NULL,
        type TEXT NOT NULL,
        statut TEXT NOT NULL,
        note TEXT,
        par TEXT NOT NULL,
        le TEXT NOT NULL,
        PRIMARY KEY (reponse_id, recu_le, type)
    )""",
]

# Relecture d'un signalement : à traiter (par défaut), en cours, corrigé (le défaut est réglé) ou rejeté
STATUTS_RETOUR = ("a_traiter", "en_cours", "corrige", "rejete")
TYPES_A_RELIRE = ("signalement", "suggestion_indicateur")

# Suivi de conversation (décision 0021) : 3 derniers échanges, oubliés après 30 min sans échange
ECHANGES_SUIVI = 3
EXPIRATION_SUIVI = timedelta(minutes=30)
# Unicité des messages des webhooks : Meta renvoie un message non acquitté pendant 24 h au plus
CONSERVATION_MESSAGES = timedelta(hours=48)

COLONNES_JOURNAL = ["recu_le", "canal", "source", "langue", "question", "transcription_brute", "issue",
                    "indicateur", "latence_ms", "version_socle", "conversation", "confirme_depuis", "reponse_id"]
# Retours joints à chaque ligne du journal (écran Journal et export CSV)
COLONNES_RETOURS = ["vote", "signalement", "commentaire", "suggestions", "suggestion"]
# Filtre « Retour » du journal : condition sur les retours de la réponse
FILTRES_RETOUR = {
    "signale": "r.type = 'signalement'",
    "pas_utile": "r.type = 'vote' AND r.vote = 'pas_utile'",
    "utile": "r.type = 'vote' AND r.vote = 'utile'",
    "suggere": "r.type = 'suggestion_indicateur'",
}


@dataclass(frozen=True)
class FiltreJournal:
    issue: str | None = None
    canal: str | None = None
    langue: str | None = None
    texte: str | None = None
    retour: str | None = None  # clé de FILTRES_RETOUR
    limite: int = 50
    decalage: int = 0


class Stockage:
    def __init__(self, url: str | None = None):
        url = url if url is not None else os.environ.get("GESTUKAAY_BASE", "")
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
            if chemin == ":memory:":
                # Liens « Cette réponse n'existe plus » (09/10) : sans base, tout disparaît au redémarrage,
                # y compris un compte créé par « comptes creer », qui ne vit que le temps de la commande.
                # Une valeur non reconnue (« sqlite://g.db », deux barres) tombe aussi en mémoire : on le dit,
                # sans afficher la valeur (une adresse PostgreSQL porte le mot de passe).
                cause = "vide" if not url or url == "sqlite:///:memory:" else "non reconnue (ni sqlite:///…, ni postgresql://…)"
                logging.getLogger("gestukaay.stockage").warning(
                    "GESTUKAAY_BASE %s : base SQLite en mémoire. Réponses, journal et comptes du back-office "
                    "sont perdus au redémarrage, et les liens /r/… déjà envoyés afficheront « Cette réponse "
                    "n'existe plus ». Pour les garder : GESTUKAAY_BASE=sqlite:///gestukaay.db, ou PostgreSQL "
                    "(Docker Compose).", cause)
        with self._curseur() as c:
            for sql in _TABLES:
                c.execute(sql)
        self._migrer()
        # Sel du hachage des conversations (audit du 09/10) : GESTUKAAY_SEL s'il est donné, sinon un sel tiré
        # une fois et gardé dans la base. Avant, un sel neuf à chaque démarrage : « et pour Kaolack ? » et le
        # « 1 » de WhatsApp perdaient la conversation après un redémarrage.
        self._sel = os.environ.get("GESTUKAAY_SEL") or self._sel_de_la_base()
        if not os.environ.get("GESTUKAAY_SEL") and url:
            # Revue de KBD sur #200 : sel et hachages dans la même base, une copie de la base suffit à
            # retrouver les numéros par force brute. Bon pour le développement, pas pour la production.
            logging.getLogger("gestukaay.stockage").warning(
                "GESTUKAAY_SEL absent : le sel des conversations est gardé dans la base. "
                "En production, le donner hors de la base (DEPLOIEMENT.md).")

    def _migrer(self) -> None:
        """Colonnes ajoutées après coup à une base existante (une base neuve les reçoit aussi)."""
        # Rôles du back-office (comptes.py) : un compte d'avant les rôles reste administrateur
        if self._pg:
            self._executer("ALTER TABLE comptes_admin ADD COLUMN IF NOT EXISTS role TEXT NOT NULL DEFAULT 'admin'")
        elif "role" not in {r[1] for r in self._executer("PRAGMA table_info(comptes_admin)")}:
            self._executer("ALTER TABLE comptes_admin ADD COLUMN role TEXT NOT NULL DEFAULT 'admin'")

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

    def _sel_de_la_base(self) -> str:
        self._executer("INSERT INTO parametres (cle, valeur) VALUES ('sel', ?) ON CONFLICT DO NOTHING",
                       (secrets.token_hex(16),))
        return self._executer("SELECT valeur FROM parametres WHERE cle = 'sel'")[0][0]

    def hacher(self, conversation_id: str) -> str:
        return hashlib.sha256(f"{self._sel}:{conversation_id}".encode()).hexdigest()[:16]

    # ------------------------------------------------------------------ retours

    def retour(self, req: FeedbackRequest) -> None:
        self._executer(
            "INSERT INTO retours (reponse_id, recu_le, type, vote, motif, commentaire) VALUES (?, ?, ?, ?, ?, ?)",
            (req.reponse_id, datetime.now(UTC).isoformat(timespec="seconds"), req.type, req.vote, req.motif,
             req.commentaire),
        )

    # ------------------------------------------------------------------ relecture des signalements

    def signalements(self, jours: int = 90, statut: str | None = None, type_: str | None = None,
                     maintenant: datetime | None = None) -> dict:
        """Signalements et suggestions d'indicateur de la période, avec leur question et leur suivi ; les plus
        anciens à traiter d'abord. Comptes par statut et arrivées par semaine (tendance, 8 semaines)."""
        maintenant = maintenant or datetime.now(UTC)
        debut = maintenant - timedelta(days=jours)
        lignes = self._executer(
            "SELECT r.reponse_id, r.recu_le, r.type, r.motif, r.commentaire, j.question, j.issue, j.indicateur, "
            "j.langue, j.canal, s.statut, s.note, s.par, s.le FROM retours r "
            "LEFT JOIN journal j ON j.reponse_id = r.reponse_id "
            "LEFT JOIN suivi_retours s ON s.reponse_id = r.reponse_id AND s.recu_le = r.recu_le AND s.type = r.type "
            "WHERE r.type IN (?, ?) AND r.recu_le >= ? ORDER BY r.recu_le",
            (*TYPES_A_RELIRE, debut.isoformat(timespec="seconds")))
        colonnes = ("reponse_id", "recu_le", "type", "motif", "commentaire", "question", "issue", "indicateur",
                    "langue", "canal", "statut", "note", "par", "le")
        tous = [{**dict(zip(colonnes, lg, strict=True)), "statut": lg[10] or "a_traiter"} for lg in lignes]
        if type_:
            tous = [x for x in tous if x["type"] == type_]
        semaines = Counter((maintenant - datetime.fromisoformat(x["recu_le"])).days // 7 for x in tous)
        return {
            "comptes": {s: sum(x["statut"] == s for x in tous) for s in STATUTS_RETOUR},
            "par_semaine": [{"il_y_a": k, "recus": semaines.get(k, 0)} for k in range(7, -1, -1)],
            "lignes": [x for x in tous if not statut or x["statut"] == statut],
        }

    def suivre_retour(self, reponse_id: str, recu_le: str, type_: str, statut: str, note: str | None,
                      par: str) -> bool:
        """Change le suivi d'un signalement ; False s'il n'existe pas."""
        if not self._executer("SELECT 1 FROM retours WHERE reponse_id = ? AND recu_le = ? AND type = ?",
                              (reponse_id, recu_le, type_)):
            return False
        self._executer(
            "INSERT INTO suivi_retours (reponse_id, recu_le, type, statut, note, par, le) VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT (reponse_id, recu_le, type) DO UPDATE SET statut = excluded.statut, note = excluded.note, "
            "par = excluded.par, le = excluded.le",
            (reponse_id, recu_le, type_, statut, note, par, datetime.now(UTC).isoformat(timespec="seconds")))
        return True

    # ------------------------------------------------------------------ journal

    def journal(self, f: FiltreJournal) -> tuple[int, list[dict]]:
        """(nombre total filtré, page de lignes, plus récentes d'abord), avec le vote, le signalement
        et la suggestion éventuels de chaque réponse, et le commentaire laissé par l'usager."""
        conditions, params = [], []
        for colonne in ("issue", "canal", "langue"):
            if valeur := getattr(f, colonne):
                conditions.append(f"j.{colonne} = ?")
                params.append(valeur)
        if f.texte:
            conditions.append("LOWER(j.question) LIKE ?")
            params.append(f"%{f.texte.lower()}%")
        if f.retour in FILTRES_RETOUR:
            conditions.append("EXISTS (SELECT 1 FROM retours r WHERE r.reponse_id = j.reponse_id"
                              f" AND {FILTRES_RETOUR[f.retour]})")
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        total = self._executer(f"SELECT COUNT(*) FROM journal j {where}", tuple(params))[0][0]
        lignes = self._executer(
            f"""SELECT {', '.join('j.' + c for c in COLONNES_JOURNAL)},
                       (SELECT r.vote FROM retours r WHERE r.reponse_id = j.reponse_id AND r.type = 'vote'
                        ORDER BY r.recu_le DESC LIMIT 1),
                       (SELECT r.motif FROM retours r WHERE r.reponse_id = j.reponse_id
                        AND r.type = 'signalement' ORDER BY r.recu_le DESC LIMIT 1),
                       (SELECT r.commentaire FROM retours r WHERE r.reponse_id = j.reponse_id
                        AND r.type = 'signalement' AND r.commentaire <> '' ORDER BY r.recu_le DESC LIMIT 1),
                       (SELECT COUNT(*) FROM retours r WHERE r.reponse_id = j.reponse_id
                        AND r.type = 'suggestion_indicateur'),
                       (SELECT r.commentaire FROM retours r WHERE r.reponse_id = j.reponse_id
                        AND r.type = 'suggestion_indicateur' AND r.commentaire <> ''
                        ORDER BY r.recu_le DESC LIMIT 1)
                FROM journal j {where} ORDER BY j.recu_le DESC, j.reponse_id LIMIT ? OFFSET ?""",
            (*params, f.limite, f.decalage),
        )
        return total, [dict(zip([*COLONNES_JOURNAL, *COLONNES_RETOURS], ligne, strict=True)) for ligne in lignes]

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

        # Motif de chaque « aucune » : une salutation ou un merci (0033) n'est ni un refus ni une
        # question non résolue, on les compte à part.
        motifs: dict[str, str] = {}
        for rid in {lg[6] for lg in courantes if lg[3] == "aucune"}:
            contenu = self._executer("SELECT contenu FROM reponses WHERE id = ?", (rid,))
            if contenu:
                motifs[rid] = json.loads(contenu[0][0])["reponse"].get("motif", "")
        conversations = [lg for lg in courantes if lg[3] == "aucune" and motifs.get(lg[6]) == "conversation"]
        issues = Counter(lg[3] for lg in courantes if not (lg[3] == "aucune" and motifs.get(lg[6]) == "conversation"))

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
        refus = [lg for lg in courantes if lg[3] == "aucune" and motifs.get(lg[6]) != "conversation"]
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
            "conversations": len(conversations),
            "latence_mediane_ms": round(statistics.median(latences)) if latences else None,
            "latence_p95_ms": p95,
            "part_wolof": round(sum(lg[2] == "wo" for lg in courantes) / total, 3) if total else None,
            "votes": len(votes),
            "satisfaction": round(utiles / len(votes), 3) if votes else None,
            "signalements": signalements,
            "par_jour": [{"jour": j, "questions": par_jour.get(j, 0)} for j in jours_liste],
            "non_resolues": sorted(groupes.values(), key=lambda g: (-g["occurrences"], g["question"]))[:10],
        }

    def non_resolues(self, jours: int = 30, canal: str | None = None, langue: str | None = None,
                     issue: str = "aucune", maintenant: datetime | None = None) -> list[dict]:
        """Les questions refusées (ou approchées) de la période, avec le motif du refus, pour les regrouper par
        thème (regroupement.py). Une salutation ou un merci (motif « conversation », 0033) n'en est pas une."""
        debut = (maintenant or datetime.now(UTC)) - timedelta(days=jours)
        lignes = self._executer(
            "SELECT j.question, j.langue, j.recu_le, j.reponse_id, j.canal, r.contenu FROM journal j "
            "JOIN reponses r ON r.id = j.reponse_id "
            "WHERE j.recu_le >= ? AND j.issue = ? AND j.confirme_depuis IS NULL ORDER BY j.recu_le",
            (debut.isoformat(timespec="milliseconds"), issue))
        sortie = []
        for question, lg, recu, rid, cnl, contenu in lignes:
            if (canal and cnl != canal) or (langue and lg != langue):
                continue
            motif = json.loads(contenu)["reponse"].get("motif") or ""
            if motif != "conversation":
                sortie.append({"question": question, "langue": lg, "motif": motif, "recu_le": recu, "reponse_id": rid})
        return sortie

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

    # ------------------------------------------------------------------ comptes du back-office

    def compte(self, identifiant: str) -> dict | None:
        """Le compte, l'identifiant comparé sans la casse (« san » ouvre SAN)."""
        lignes = self._executer(
            "SELECT identifiant, hachage, cree_le, actif, echecs, bloque_jusqu_a, role FROM comptes_admin "
            "WHERE LOWER(identifiant) = LOWER(?)", (identifiant.strip(),))
        if not lignes:
            return None
        return dict(zip(("identifiant", "hachage", "cree_le", "actif", "echecs", "bloque_jusqu_a", "role"),
                        lignes[0], strict=True))

    def comptes(self) -> list[dict]:
        return [{"identifiant": i, "actif": bool(a), "cree_le": c, "role": r} for i, a, c, r in self._executer(
            "SELECT identifiant, actif, cree_le, role FROM comptes_admin ORDER BY identifiant")]

    def changer_role(self, identifiant: str, role: str) -> None:
        self._executer("UPDATE comptes_admin SET role = ? WHERE identifiant = ?", (role, identifiant))

    def back_office_ouvert(self) -> bool:
        """Sans compte actif, le back-office n'existe pas (404), comme avant sans jeton."""
        return bool(self._executer("SELECT 1 FROM comptes_admin WHERE actif = 1 LIMIT 1"))

    def creer_compte(self, identifiant: str, hachage: str, role: str = "admin") -> None:
        self._executer("INSERT INTO comptes_admin (identifiant, hachage, cree_le, role) VALUES (?, ?, ?, ?)",
                       (identifiant, hachage, datetime.now(UTC).isoformat(timespec="seconds"), role))

    def changer_mot_de_passe(self, identifiant: str, hachage: str) -> None:
        """Nouveau mot de passe : le compte est réactivé et débloqué, ses sessions sont fermées."""
        self._executer("UPDATE comptes_admin SET hachage = ?, actif = 1, echecs = 0, bloque_jusqu_a = NULL "
                       "WHERE identifiant = ?", (hachage, identifiant))
        self._executer("DELETE FROM sessions_admin WHERE identifiant = ?", (identifiant,))

    def desactiver_compte(self, identifiant: str) -> None:
        self._executer("UPDATE comptes_admin SET actif = 0 WHERE identifiant = ?", (identifiant,))
        self._executer("DELETE FROM sessions_admin WHERE identifiant = ?", (identifiant,))

    def noter_echec(self, identifiant: str, essais_max: int, bloque_jusqu_a: datetime) -> None:
        """Un essai manqué de plus ; au dernier permis, le compte est bloqué et le compteur repart à 0."""
        self._executer(
            "UPDATE comptes_admin SET echecs = CASE WHEN echecs + 1 >= ? THEN 0 ELSE echecs + 1 END, "
            "bloque_jusqu_a = CASE WHEN echecs + 1 >= ? THEN ? ELSE bloque_jusqu_a END WHERE identifiant = ?",
            (essais_max, essais_max, bloque_jusqu_a.isoformat(timespec="seconds"), identifiant))

    def remettre_echecs(self, identifiant: str) -> None:
        self._executer("UPDATE comptes_admin SET echecs = 0, bloque_jusqu_a = NULL WHERE identifiant = ?",
                       (identifiant,))

    def ouvrir_session(self, identifiant: str, maintenant: datetime) -> str:
        jeton = secrets.token_urlsafe(32)
        quand = maintenant.isoformat(timespec="seconds")
        self._executer("INSERT INTO sessions_admin (jeton, identifiant, ouverte_le, vue_le) VALUES (?, ?, ?, ?)",
                       (_empreinte(jeton), identifiant, quand, quand))
        return jeton

    def session(self, jeton: str, maintenant: datetime, inactivite: timedelta, duree_max: timedelta) -> str | None:
        """L'identifiant de la session si elle vit encore (activité récente, durée maximale non
        atteinte, compte actif) ; elle est alors prolongée. Les sessions expirées sont purgées."""
        self._executer("DELETE FROM sessions_admin WHERE vue_le < ? OR ouverte_le < ?",
                       ((maintenant - inactivite).isoformat(timespec="seconds"),
                        (maintenant - duree_max).isoformat(timespec="seconds")))
        lignes = self._executer(
            "SELECT s.identifiant FROM sessions_admin s JOIN comptes_admin c ON c.identifiant = s.identifiant "
            "WHERE s.jeton = ? AND c.actif = 1", (_empreinte(jeton),))
        if not lignes:
            return None
        self._executer("UPDATE sessions_admin SET vue_le = ? WHERE jeton = ?",
                       (maintenant.isoformat(timespec="seconds"), _empreinte(jeton)))
        return lignes[0][0]

    def fermer_session(self, jeton: str) -> None:
        self._executer("DELETE FROM sessions_admin WHERE jeton = ?", (_empreinte(jeton),))

    # ------------------------------------------------------------------ clés de l'API publique

    def creer_cle(self, nom: str, par: str) -> tuple[str, str]:
        """(identifiant, clé en clair) : la clé n'est rendue qu'ici, la base n'en garde que l'empreinte."""
        cid, cle = secrets.token_hex(4), f"gk_{secrets.token_urlsafe(24)}"
        self._executer("INSERT INTO cles_api (id, nom, empreinte, creee_le, creee_par) VALUES (?, ?, ?, ?, ?)",
                       (cid, nom, _empreinte(cle), datetime.now(UTC).isoformat(timespec="seconds"), par))
        return cid, cle

    def cles(self) -> list[dict]:
        colonnes = ("id", "nom", "creee_le", "creee_par", "active", "vue_le", "appels")
        return [{**dict(zip(colonnes, ligne, strict=True)), "active": bool(ligne[4])} for ligne in self._executer(
            f"SELECT {', '.join(colonnes)} FROM cles_api ORDER BY creee_le DESC")]

    def revoquer_cle(self, cid: str) -> bool:
        if not self._executer("SELECT 1 FROM cles_api WHERE id = ?", (cid,)):
            return False
        self._executer("UPDATE cles_api SET active = 0 WHERE id = ?", (cid,))
        return True

    def verifier_cle(self, cle: str, maintenant: datetime | None = None) -> str | None:
        """L'identifiant d'une clé active (son appel est compté), None si elle est inconnue ou révoquée."""
        lignes = self._executer("SELECT id FROM cles_api WHERE empreinte = ? AND active = 1", (_empreinte(cle),))
        if not lignes:
            return None
        quand = (maintenant or datetime.now(UTC)).isoformat(timespec="seconds")
        self._executer("UPDATE cles_api SET appels = appels + 1, vue_le = ? WHERE id = ?", (quand, lignes[0][0]))
        return lignes[0][0]


def _empreinte(jeton: str) -> str:
    return hashlib.sha256(jeton.encode()).hexdigest()
