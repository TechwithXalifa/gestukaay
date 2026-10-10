"""Comptes du back-office : un compte nominatif par membre de l'équipe (décision 0037).

Connexion par identifiant et mot de passe, puis session côté serveur portée par un cookie
HttpOnly : aucun jeton à copier, ni dans le navigateur ni dans .env. Les comptes se créent
en ligne de commande seulement, sur la machine qui porte la base (GESTUKAAY_BASE) :

    uv run python -m gestukaay_backend.comptes creer SAN                  # administrateur
    uv run python -m gestukaay_backend.comptes creer Awa --role linguiste
    uv run python -m gestukaay_backend.comptes role Awa lecteur
    uv run python -m gestukaay_backend.comptes changer KBD      # nouveau mot de passe, réactive
    uv run python -m gestukaay_backend.comptes desactiver KBD
    uv run python -m gestukaay_backend.comptes lister

Rôles (V1.1) : un administrateur fait tout, y compris gérer les comptes (aussi depuis /admin/comptes) et lancer
le jeu de test ; un linguiste et un lecteur consultent. Le linguiste recevra le lexique quand il arrivera.

Le mot de passe est demandé au clavier ; sans terminal (tests de bout en bout), il est lu dans
GESTUKAAY_MOT_DE_PASSE, sinon sur l'entrée standard. Il n'apparaît jamais dans la commande. Mots de passe hachés par scrypt (bibliothèque
standard), sel propre à chaque compte ; la base ne garde que le hachage des jetons de session.
"""

from __future__ import annotations

import argparse
import getpass
import hashlib
import hmac
import os
import re
import secrets
import sys
from datetime import UTC, datetime, timedelta

from .stockage import Stockage

IDENTIFIANT = re.compile(r"[A-Za-z0-9._-]{2,32}")
ROLES = {
    "admin": "Administrateur : tout, y compris les comptes et le lancement du jeu de test",
    "linguiste": "Linguiste : consulte le journal et les questions ; le lexique quand il arrivera",
    "lecteur": "Lecteur : consultation seule (tableau de bord, journal, jeu de test)",
}
LONGUEUR_MIN = 12
# Après 5 essais manqués, le compte est bloqué 15 minutes (en plus de la limite par adresse)
ESSAIS_MAX = 5
BLOCAGE = timedelta(minutes=15)
# Session : 8 h sans activité, 12 h au plus (une journée de travail)
INACTIVITE = timedelta(hours=8)
DUREE_MAX = timedelta(hours=12)

_N, _R, _P = 2**14, 8, 1  # scrypt : environ 16 Mo et quelques dizaines de ms par essai


def hacher(mot_de_passe: str) -> str:
    sel = secrets.token_bytes(16)
    h = hashlib.scrypt(mot_de_passe.encode(), salt=sel, n=_N, r=_R, p=_P, dklen=32)
    return f"scrypt${_N}${_R}${_P}${sel.hex()}${h.hex()}"


def verifier(mot_de_passe: str, hachage: str) -> bool:
    _, n, r, p, sel, attendu = hachage.split("$")
    h = hashlib.scrypt(mot_de_passe.encode(), salt=bytes.fromhex(sel), n=int(n), r=int(r), p=int(p), dklen=32)
    return hmac.compare_digest(h.hex(), attendu)


# Identifiant inconnu : on vérifie quand même contre ce hachage, pour un temps de réponse identique
_LEURRE = hacher(secrets.token_hex(16))


def connecter(st: Stockage, identifiant: str, mot_de_passe: str, maintenant: datetime | None = None) -> str | None:
    """Le jeton d'une nouvelle session, ou None. Même réponse pour un identifiant inconnu, un mot de
    passe faux, un compte désactivé ou bloqué : rien n'indique lequel."""
    maintenant = maintenant or datetime.now(UTC)
    compte = st.compte(identifiant)
    bon = verifier(mot_de_passe, compte["hachage"] if compte else _LEURRE)
    if not compte or not compte["actif"]:
        return None
    bloque = compte["bloque_jusqu_a"] and datetime.fromisoformat(compte["bloque_jusqu_a"]) > maintenant
    if bloque:
        return None
    if not bon:
        st.noter_echec(compte["identifiant"], ESSAIS_MAX, maintenant + BLOCAGE)
        return None
    st.remettre_echecs(compte["identifiant"])
    return st.ouvrir_session(compte["identifiant"], maintenant)


def identifier(st: Stockage, jeton: str | None, maintenant: datetime | None = None) -> str | None:
    """L'identifiant de la session en cours, ou None (absente, expirée, compte désactivé)."""
    if not jeton:
        return None
    return st.session(jeton, maintenant or datetime.now(UTC), INACTIVITE, DUREE_MAX)


# ---------------------------------------------------------------------------- ligne de commande


def _lire_mot_de_passe() -> str:
    # Sans terminal (tests de bout en bout, scripts) : la variable d'environnement, même commande sous Linux et
    # sous Windows, sans tube ni « $VAR » propre à un shell
    if mdp := os.environ.get("GESTUKAAY_MOT_DE_PASSE"):
        return mdp
    if not sys.stdin.isatty():  # « … | python -m … »
        # un fichier en CRLF passé par un tube sous Linux ou macOS : le \r ne fait pas partie du mot de passe
        return sys.stdin.readline().rstrip("\r\n")
    mdp = getpass.getpass("Mot de passe : ")
    if getpass.getpass("Le même, encore une fois : ") != mdp:
        sys.exit("Les deux saisies diffèrent.")
    return mdp


def _nouveau_mot_de_passe() -> str:
    mdp = _lire_mot_de_passe()
    if len(mdp) < LONGUEUR_MIN:
        sys.exit(f"Mot de passe trop court : {LONGUEUR_MIN} caractères au moins.")
    return mdp


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="python -m gestukaay_backend.comptes", description="Comptes du back-office")
    actions = p.add_subparsers(dest="action", required=True)
    for nom, aide in (("creer", "crée un compte"), ("changer", "change le mot de passe"),
                      ("desactiver", "ferme le compte et ses sessions")):
        actions.add_parser(nom, help=aide).add_argument("identifiant")
    actions.choices["creer"].add_argument("--role", choices=ROLES, default="admin")
    role = actions.add_parser("role", help="change le rôle")
    role.add_argument("identifiant")
    role.add_argument("role", choices=ROLES)
    actions.add_parser("lister", help="liste les comptes")
    args = p.parse_args(argv)
    st = Stockage()

    if args.action == "lister":
        for c in st.comptes():
            print(f"{c['identifiant']}\t{c['role']}\t{'actif' if c['actif'] else 'désactivé'}\tcréé le {c['cree_le']}")
        return
    if args.action == "creer":
        if not IDENTIFIANT.fullmatch(args.identifiant):
            sys.exit("Identifiant : 2 à 32 caractères, lettres, chiffres, point, tiret ou souligné.")
        if st.compte(args.identifiant):
            sys.exit(f"Le compte {args.identifiant} existe déjà (« changer » pour un nouveau mot de passe).")
        st.creer_compte(args.identifiant, hacher(_nouveau_mot_de_passe()), args.role)
        print(f"Compte {args.identifiant} créé ({args.role}).")
        return
    compte = st.compte(args.identifiant)
    if not compte:
        sys.exit(f"Aucun compte {args.identifiant}.")
    if args.action == "role":
        st.changer_role(compte["identifiant"], args.role)
        print(f"{compte['identifiant']} est maintenant {args.role}.")
    elif args.action == "changer":
        st.changer_mot_de_passe(compte["identifiant"], hacher(_nouveau_mot_de_passe()))
        print(f"Mot de passe de {compte['identifiant']} changé (compte actif) ; ses sessions sont fermées.")
    else:
        st.desactiver_compte(compte["identifiant"])
        print(f"Compte {compte['identifiant']} désactivé ; ses sessions sont fermées.")


if __name__ == "__main__":
    main()
