## Quoi

<!-- En une ou deux phrases. -->

## Pourquoi

<!-- Exigence ou récit concerné : EF-xx / US-xx / issue #nn -->

## Comment tester

<!-- Commandes ou étapes pour vérifier soi-même. -->

## Vérifications

- [ ] `uv run pytest` vert en local
- [ ] Aucune valeur affichée sans source (engagement 01)
- [ ] Si le contrat change : `./scripts/generer_contrat.sh` lancé, étiquette `contrat`, les deux approuvent
- [ ] Pas de secret dans le diff
