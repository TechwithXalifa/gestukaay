"""Évaluer la transcription des notes vocales wolof et choisir (issue #27, décision 0026).

    uv run --with "torch" --with "transformers<5" --with "peft" --with "soundfile" --with "scipy" \
        --with "jiwer" python mesure/scripts/evaluer_transcription.py \
        [--voix ../voix_test] [--candidats whisper-small-wolof,whosper-large] [--llm --oui]

Corpus (hors Git, ce sont des voix) : ../voix_test/<ID>_<voix>.opus|.ogg|.wav, où <ID> est une question
du jeu de test (référence = son texte, ou `ecarts.csv` si autre chose a été dit), et libre-NN_<voix>.*
avec leur texte dans `libres.csv`. Voir ../voix_test/LISEZMOI.md.

Pour chaque candidat et chaque note :
  - taux d'erreur par mot (WER) et par caractère (CER), après normalisation légère (minuscules, sans
    ponctuation) : exigé par le cahier (§12.1), mais le wolof s'écrit de plusieurs façons ;
  - **bonne réponse** (critère principal, 3a) : la transcription passe dans le moteur réel, la réponse
    est jugée comme dans le benchmark (0020). Comparée à la même chose sur le texte de référence :
    l'écart mesure ce que la transcription coûte, pas les limites de la compréhension ;
  - latence de la transcription (cible du cahier : < 2 s), sur la machine qui lance le script.
Compréhension : règles locales par défaut (gratuit) ; --llm = la chaîne du .env (PAYANT, accord KBD).
Aucun audio n'est copié ni écrit : lu, transcrit, oublié.
"""

from __future__ import annotations

import argparse
import csv
import re
import statistics
import sys
import time
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
JEU = RACINE / "mesure" / "jeu_de_test" / "questions.csv"
RAPPORT = RACINE / "mesure" / "rapports" / "transcription.md"
AUDIO = (".opus", ".ogg", ".oga", ".wav", ".mp3", ".m4a")
TAUX = 16_000  # Whisper attend du 16 kHz mono
# Décodage glouton et court : une question dure quelques secondes. Sans ces réglages, la génération
# va jusqu'à 448 jetons : 16 s au lieu de 1 s pour le même texte (mesuré sur M3 Pro). Au-delà de 30 s
# (une note vocale peut durer 60 s, EF-11), Whisper découpe : horodatage obligatoire (return_timestamps).
GENERATION = {"max_new_tokens": 64, "num_beams": 1}

# --------------------------------------------------------------------------------------------
# Corpus
# --------------------------------------------------------------------------------------------


@dataclass
class Note:
    fichier: Path
    ident: str  # WO-001 ou libre-01
    voix: str
    reference: str


def corpus(dossier: Path, questions: dict[str, dict]) -> list[Note]:
    def table(nom: str) -> dict[str, str]:
        f = dossier / nom
        if not f.exists():
            return {}
        with f.open(encoding="utf-8-sig", newline="") as h:
            return {r["fichier"]: next(v for k, v in r.items() if k != "fichier") for r in csv.DictReader(h, delimiter=";")}

    libres, ecarts = table("libres.csv"), table("ecarts.csv")
    notes = []
    for f in sorted(p for p in dossier.iterdir() if p.suffix.lower() in AUDIO):
        ident, _, voix = f.stem.rpartition("_")
        reference = ecarts.get(f.name) or libres.get(f.name) or questions.get(ident, {}).get("question", "")
        if not ident or not reference:
            print(f"ignoré (référence inconnue) : {f.name}", file=sys.stderr)
            continue
        notes.append(Note(f, ident, voix, reference))
    return notes


def decoder(fichier: Path):
    """Audio -> numpy float32 mono 16 kHz, en mémoire (soundfile lit OGG/Opus et WAV)."""
    import numpy as np
    import soundfile as sf
    from scipy.signal import resample_poly

    signal, taux = sf.read(str(fichier), dtype="float32", always_2d=True)
    signal = signal.mean(axis=1)
    if taux != TAUX:
        pgcd = np.gcd(taux, TAUX)
        signal = resample_poly(signal, TAUX // pgcd, taux // pgcd).astype("float32")
    return signal


# --------------------------------------------------------------------------------------------
# Candidats : nom -> fabrique qui charge le modèle une fois et rend audio -> texte
# --------------------------------------------------------------------------------------------


def _appareil() -> str:
    import torch

    return "mps" if torch.backends.mps.is_available() else "cpu"


def _pipeline(modele: str) -> Callable:
    """Pipeline de transcription ; demi-précision sur la puce graphique du Mac (M-Kiriku : 2,3 s ->
    1,9 s, même transcription, mesuré sur M3 Pro)."""
    import torch
    from transformers import pipeline

    appareil = _appareil()
    asr = pipeline("automatic-speech-recognition", model=modele, device=appareil,
                   torch_dtype=torch.float16 if appareil == "mps" else torch.float32)
    return lambda audio: asr({"raw": audio, "sampling_rate": TAUX}, generate_kwargs=GENERATION,
                             return_timestamps=len(audio) > 30 * TAUX)["text"]


def whisper_small_wolof() -> Callable:
    """M9and2M/whisper-small-wolof (MIT) : Whisper-small affiné sur 57 h de wolof (audios < 6 s)."""
    return _pipeline("M9and2M/whisper-small-wolof")


def whosper_large() -> Callable:
    """CAYTU/whosper-large (Apache-2.0) : adaptateur LoRA sur Whisper-large-v2, wolof + français."""
    import torch
    from peft import PeftModel
    from transformers import WhisperForConditionalGeneration, WhisperProcessor

    appareil = _appareil()
    base = WhisperForConditionalGeneration.from_pretrained("openai/whisper-large-v2", torch_dtype=torch.float16
                                                           if appareil == "mps" else torch.float32)
    modele = PeftModel.from_pretrained(base, "CAYTU/whosper-large").merge_and_unload().to(appareil).eval()
    processeur = WhisperProcessor.from_pretrained("CAYTU/whosper-large")

    def transcrire(audio) -> str:
        entree = processeur(audio, sampling_rate=TAUX, return_tensors="pt").input_features
        entree = entree.to(appareil, dtype=modele.dtype)
        with torch.no_grad():
            ids = modele.generate(entree, **GENERATION)
        return processeur.batch_decode(ids, skip_special_tokens=True)[0]

    return transcrire


def whisper_turbo() -> Callable:
    """openai/whisper-large-v3-turbo (MIT) : le Whisper standard, référence pour le français ; il ne
    connaît pas le wolof. Sert à juger un aiguillage par langue (wolof -> modèle wolof, français -> lui)."""
    return _pipeline("openai/whisper-large-v3-turbo")


def kiriku_wolof() -> Callable:
    """AIHubSN/Kiriku-Wolof-ASR (IA Hub Sénégal, Apache-2.0) : Whisper-large-v2 affiné sur 88 h de wolof
    vérifié, vocabulaire wolof ajouté (ñ, ë, ŋ…), transcription libre sans jeton de langue forcé.
    Accès restreint sur Hugging Face : conditions acceptées et jeton (HF_TOKEN) nécessaires."""
    return _pipeline("AIHubSN/Kiriku-Wolof-ASR")


def m_kiriku() -> Callable:
    """AIHubSN/M-Kiriku-ASR (IA Hub Sénégal) : multilingue wolof, pulaar, sérère (34,9 h de wolof,
    radio et conversations) ; ne couvre pas le français."""
    return _pipeline("AIHubSN/M-Kiriku-ASR")


COUT_ADIA_FCFA = [0.0]  # cumul des en-têtes X-Adia-Cost-Fcfa, affiché en fin de mesure


def adia() -> Callable:
    """ADIA ASR (Concree, API payante : 22 FCFA la minute ; https://adia.concree.com). Clé ADIA_API_KEY
    dans .env, jamais affichée. L'audio part chez un tiers : seulement des voix dont le locuteur a
    accepté l'envoi (--seulement). Envoi en WAV 16 kHz, recommandé par leur documentation."""
    import io
    import os

    import httpx
    import soundfile as sf

    sys.path.insert(0, str(RACINE / "engine" / "scripts"))
    from essai_llm import charger_env

    charger_env(RACINE / ".env")
    cle = os.environ.get("ADIA_API_KEY", "")
    if not cle:
        raise RuntimeError("ADIA_API_KEY absente de .env")
    client = httpx.Client(base_url="https://adia.concree.com/api/v1", timeout=300,
                          headers={"Authorization": f"Bearer {cle}"})

    def transcrire(audio) -> str:
        wav = io.BytesIO()
        sf.write(wav, audio, TAUX, format="WAV", subtype="PCM_16")
        r = client.post("/asr", files={"audio": ("note.wav", wav.getvalue(), "audio/wav")},
                        data={"language": "wolof"})
        r.raise_for_status()
        COUT_ADIA_FCFA[0] += float(r.headers.get("X-Adia-Cost-Fcfa", 0) or 0)
        return r.json().get("text", "")

    return transcrire


CANDIDATS: dict[str, Callable[[], Callable]] = {
    "whisper-small-wolof": whisper_small_wolof,
    "whosper-large": whosper_large,
    "whisper-turbo": whisper_turbo,
    "kiriku-wolof": kiriku_wolof,
    "m-kiriku": m_kiriku,
    "adia": adia,
}

# --------------------------------------------------------------------------------------------
# Mesures
# --------------------------------------------------------------------------------------------


def normaliser(texte: str) -> str:
    t = unicodedata.normalize("NFC", texte.lower())
    t = re.sub(r"[^\w\s']", " ", t).replace("'", " ")
    return re.sub(r"\s+", " ", t).strip()


@dataclass
class Ligne:
    note: Note
    texte: str
    latence_s: float
    wer: float
    cer: float
    juste: bool | None  # None : pas de réponse attendue (question libre)


@dataclass
class Resultat:
    candidat: str
    lignes: list[Ligne] = field(default_factory=list)
    erreur: str = ""


def juge(moteur, questions: dict[str, dict], s) -> Callable[[str, str], bool | None]:
    """(identifiant, texte) -> la réponse du moteur est-elle juste ? Mêmes critères que le benchmark."""
    sys.path.insert(0, str(RACINE / "mesure" / "scripts"))
    import benchmark as b
    from gestukaay_contracts.models import AskRequest

    def juste(ident: str, texte: str) -> bool | None:
        q = questions.get(ident)
        if q is None or len(texte.strip()) < 3:
            return None if q is None else False
        rep = moteur.repondre(AskRequest(question=texte[:300]))
        if q["issue_attendue"] == "exacte":
            return b.verifier_exactitude_reponse(q, rep, s)[0]
        if q["issue_attendue"] == "approchee":
            return b.verifier_approchee_reponse(q, rep, moteur)[0]
        return b.verifier_refus_reponse(q, rep)[0]

    return juste


def evaluer(nom: str, notes: list[Note], juste: Callable) -> Resultat:
    import jiwer

    res = Resultat(nom)
    try:
        transcrire = CANDIDATS[nom]()
        transcrire(decoder(notes[0].fichier))  # chauffe : le premier appel ne compte pas
    except Exception as e:  # noqa: BLE001 — un candidat qui ne se charge pas est noté, pas fatal
        res.erreur = " ".join(f"{type(e).__name__} : {e}".split())[:200]
        return res
    for n in notes:
        audio = decoder(n.fichier)
        t0 = time.perf_counter()
        try:
            texte = transcrire(audio).strip()
        except Exception as e:  # noqa: BLE001 — une note en erreur est notée, la mesure continue
            texte = f"[erreur : {type(e).__name__}]"
        latence = time.perf_counter() - t0
        ref, hyp = normaliser(n.reference), normaliser(texte) or "∅"
        res.lignes.append(Ligne(n, texte, latence, jiwer.wer(ref, hyp), jiwer.cer(ref, hyp), juste(n.ident, texte)))
        del audio
    return res


# --------------------------------------------------------------------------------------------
# Rapport
# --------------------------------------------------------------------------------------------


def _pc(x: float) -> str:
    return f"{100 * x:.1f} %"


def rapport(resultats: list[Resultat], notes: list[Note], plafond: dict[str, bool | None], mode: str) -> str:
    jugees = [n for n in notes if plafond.get(n.fichier.name) is not None]
    ok_ref = sum(1 for n in jugees if plafond[n.fichier.name])
    L = [f"# Transcription des notes vocales wolof (#27, {mode})", "",
         (f"Mesure du {datetime.now(UTC):%d/%m/%Y} : {len(notes)} notes vocales "
          f"({', '.join(sorted({n.voix for n in notes}))}), dont {len(jugees)} questions du jeu de test."), "",
         (f"**Plafond** (texte de référence tapé, sans transcription) : bonne réponse pour {ok_ref}/{len(jugees)} "
          f"({_pc(ok_ref / len(jugees)) if jugees else '—'}). Une transcription parfaite ne ferait pas mieux."), "",
         "| Candidat | Bonne réponse | WER médian | CER médian | Latence médiane | Latence max |",
         "|---|---|---|---|---|---|"]
    for r in resultats:
        if r.erreur:
            L.append(f"| {r.candidat} | non chargé : {r.erreur} | | | | |")
            continue
        j = [x for x in r.lignes if x.juste is not None]
        bons = sum(1 for x in j if x.juste)
        lat = [x.latence_s for x in r.lignes]
        L.append(f"| {r.candidat} | **{bons}/{len(j)}** ({_pc(bons / len(j)) if j else '—'}) | "
                 f"{_pc(statistics.median(x.wer for x in r.lignes))} | {_pc(statistics.median(x.cer for x in r.lignes))} | "
                 f"{statistics.median(lat):.2f} s | {max(lat):.2f} s |")
    L += ["", "Latences mesurées sur la machine du test (Mac M3 Pro), pas sur le serveur de démonstration.", ""]
    for r in resultats:
        if r.erreur:
            continue
        L += [f"## {r.candidat}", "", "| Note | Référence | Transcription | WER | Réponse |", "|---|---|---|---|---|"]
        for x in r.lignes:
            rep = "—" if x.juste is None else ("juste" if x.juste else "**fausse**")
            L.append(f"| {x.note.fichier.name} | {x.note.reference} | {x.texte or '∅'} | {_pc(x.wer)} | {rep} |")
        L.append("")
    return "\n".join(L) + "\n"


def main() -> int:
    p = argparse.ArgumentParser(description="Évaluer la transcription des notes vocales wolof (#27).")
    p.add_argument("--voix", type=Path, default=RACINE.parent / "voix_test")
    p.add_argument("--candidats", default=",".join(CANDIDATS))
    p.add_argument("--llm", action="store_true", help="compréhension par la chaîne du .env (PAYANT)")
    p.add_argument("--oui", action="store_true", help="confirme la dépense LLM")
    p.add_argument("--rapport", type=Path, default=RAPPORT)
    p.add_argument("--jetons", type=int, default=GENERATION["max_new_tokens"],
                   help="jetons générés au plus (64 pour une question ; ~440 pour des extraits longs)")
    p.add_argument("--seulement", default="", help="voix à garder, ex. kbd (envoi à un tiers : accord du locuteur)")
    args = p.parse_args()

    with JEU.open(encoding="utf-8-sig", newline="") as f:
        questions = {q["id"]: q for q in csv.DictReader(f, delimiter=";")}
    GENERATION["max_new_tokens"] = args.jetons
    notes = corpus(args.voix, questions)
    if args.seulement:
        notes = [n for n in notes if n.voix in args.seulement.split(",")]
    if not notes:
        print(f"Aucune note vocale dans {args.voix} (voir LISEZMOI.md).", file=sys.stderr)
        return 1
    noms = [n for n in args.candidats.split(",") if n]
    if inconnus := [n for n in noms if n not in CANDIDATS]:
        print(f"Candidats inconnus : {inconnus} (connus : {list(CANDIDATS)})", file=sys.stderr)
        return 1

    from gestukaay_engine.comprehension import Comprehension
    from gestukaay_engine.moteur import MoteurReel
    from gestukaay_engine.socle import socle

    if args.llm:
        if not args.oui:
            print("Mode LLM payant : relancer avec --oui après l'accord de KBD.", file=sys.stderr)
            return 1
        sys.path.insert(0, str(RACINE / "engine" / "scripts"))
        from essai_llm import charger_env
        from gestukaay_engine.llm import charger_client

        charger_env(RACINE / ".env")
        comprehension, mode = Comprehension(charger_client()), "compréhension LLM"
    else:
        comprehension, mode = Comprehension(None), "compréhension par règles"
    s = socle()
    moteur = MoteurReel(s, comprehension)
    juste = juge(moteur, questions, s)
    plafond = {n.fichier.name: juste(n.ident, n.reference) for n in notes}
    resultats = []
    for nom in noms:
        print(f"{nom} : {len(notes)} notes…", file=sys.stderr)
        resultats.append(evaluer(nom, notes, juste))
    args.rapport.write_text(rapport(resultats, notes, plafond, mode), encoding="utf-8")
    if "adia" in noms:
        print(f"Coût ADIA : {COUT_ADIA_FCFA[0]:.2f} FCFA")
    print(f"Rapport : {args.rapport}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
