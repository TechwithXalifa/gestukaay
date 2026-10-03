# 0017 — Refus, motifs et suggestions d'indicateurs proches (Chantier 2.5)

**Date** : 2026-10-03 · **Statut** : accepté (KBD) · **Issue** : #13

## Contexte

Quand une demande ne peut pas être servie de manière exacte ni approchée (cahier §7.4, [EF-05]),
Gëstukaay renvoie une `ReponseAucune` avec l'un des trois motifs autorisés par le contrat :
`hors_socle`, `projection` ou `incomprehension`.

Le cahier impose des messages précis (§7.4), l'absence totale de chiffre inventé (toute suggestion
doit pointer vers une donnée vérifiée du socle), et l'interdiction absolue de faire des prévisions
non publiées par l'ANSD.

## Décisions

1. **Français seulement (V1.0)** :
   Conformément à la règle 6 et à la décision 0009, aucun wolof n'est généré par le moteur ou les gabarits
   en V1.0. Le wolof sera entièrement rédigé et validé par KBD dans l'issue #25. Les chaînes wolof
   provisoires ont été retirées du moteur.
2. **Règle générique de projection (sans marqueurs ni valeurs en dur)** :
   Une demande est refusée avec `motif="projection"` si et seulement si :
   - un indicateur est identifié ;
   - une année numérique est demandée ;
   - `année demandée > année en cours (2026)` **ET** `année demandée > dernière période publiée de l'indicateur`.
   Les projections futures publiées par l'ANSD (ex. démographie jusqu'en 2038 pour `pvswjnd`) sont servies
   en `ReponseExacte` avec `nature="projection"` (décision 0002).
   Une année passée non publiée relève de la réponse approchée (#12, `periode_absente`).
   Les questions sans année (ex. « demain » dans FR-060) ne deviennent jamais des projections et sont
   refusées en `hors_socle`.
3. **Suggestions vérifiées à l'avance (zéro chiffre inventé)** :
   - Ajout d'un champ `proches: list[int]` à `SortieLLM` dans `comprehension.py` (au plus 3 numéros de
     candidats pertinents de la liste, dans le même appel LLM).
   - En mode règles locales : sélection des candidats dont le score BM25 $\ge 6.0$, sinon repli sur les
     3 indicateurs phares P1 (`pvswjnd` Population, `dwibrlf` Chômage, `jcvcajc.taux-de-pauvrete` Pauvreté).
   - Chaque suggestion est obligatoirement testée et validée par `resolution.resoudre(socle, req)` à
     l'avance (au niveau de la zone demandée ou au national `SN`).
   - Contre-exemple garanti : « personnes parlent sérère » ne suggère jamais « personnes emprisonnées »,
     car les tokens vides et génériques (« personne », « personnes », « temps ») ont été ajoutés à `_VIDES`
     et ne biaisent plus la recherche lexicale.
4. **Message `hors_socle` mot pour mot du cahier §7.4** :
   « Cette donnée n'existe pas dans les publications de l'ANSD que nous couvrons. », suivi de
   « Voici des indicateurs proches : » quand des suggestions sont formulées.
5. **Incompréhension** :
   - Drapeau interne `incomprehensible: bool` dans `SortieLLM` (sans modification du contrat d'échange).
   - En mode règles : détecté dès qu'aucun mot connu (`aucun_mot_connu`) n'est identifié dans la question.
   - Restitution conforme au contrat : `requete = None`, `suggestions = []`, et message d'exemple
     « Je n'ai pas bien compris. Essayez par exemple : « Combien d'habitants à Thiès ? » ».
6. **Lieux non administratifs** :
   - Un lieu déclaré dans `socle/referentiels/rattachements.csv` (Touba, villes de Thiès et Kaolack) relève
     de la réponse approchée (#12).
   - Un lieu étranger ou non déclaré (ex. Paris, FR-061) bascule immédiatement en refus `hors_socle`.

## Conséquences

- Nouveau module `engine/src/gestukaay_engine/refus.py` implémentant `refuser` et `construire_reponse_aucune`.
- Évolution de `comprehension.py` (`SortieLLM.proches`, `SortieLLM.incomprehensible`, `Comprise.proches`, `Comprise.incomprehensible`).
- Nettoyage des chaînes wolof dans `approchee.py` en conformité avec la décision 0009.
- Suite de tests complète dans `engine/tests/test_refus.py` (11 tests unitaires, socle synthétique sans dépendance réseau/fichiers volumineux).
- Tâche 2.5 cochée dans `docs/suivi-kbd.md`.
