# Compréhension — évaluation (llm-google-gemini-2.5-flash-lite)

103 questions du jeu de test (#10). Une question est juste si l'intention, l'indicateur, les zones et la période le sont.

| | Score |
|---|---|
| **Tout juste** | **84/103 (82 %)** |
| Français | 59/72 (82 %) |
| Wolof | 25/31 (81 %) |
| Intention | 99/103 (96 %) |
| Indicateur | 87/103 (84 %) |
| Zones | 103/103 (100 %) |
| Période | 103/103 (100 %) |
| Latence médiane / max | 778 ms / 1483 ms |
| Secours par règles | 3 |
| Coût total | 0.0198 $ |

## Questions fausses

| Id | Question | Faux | Obtenu | Attendu |
|---|---|---|---|---|
| FR-001 | Combien d'habitants à Thiès ? | indicateur | valeur · rfegvpb.population-residente-par-zone · SN-TH · dernière | valeur · pvswjnd |
| FR-010 | Quel est le PIB du Sénégal en 2024 ? | indicateur | valeur · dguabcd · SN · 2024 | valeur · rgohtcc |
| FR-015 | Quelle quantité de produits la pêche artisanale a-t-elle débarquée en 2024 ? | indicateur | valeur · zxtmqqg · — · 2024 | valeur · wrqfsxb.quantite |
| FR-018 | Quelle est la production de riz du Sénégal ? | indicateur | valeur · dwehszb.production-hivernale-nette-en-cereales-entieres · SN · dernière | valeur · ovothxc.production |
| FR-020 | Quel pourcentage d'enfants souffrent d'un retard de croissance au Sénégal ? | indicateur | valeur · pagfmnc.prevalence-du-retard-de-croissance · SN · dernière | valeur · xsitdae.enfants-souffrant-dun-retard-de-croissance |
| FR-023 | Combien de femmes vivent dans la région de Matam ? | indicateur | valeur · uzptmtd · SN-MT · dernière | valeur · pvswjnd |
| FR-028 | Quel est le pourcentage de filles parmi les élèves du secondaire au Sénégal ? | indicateur | valeur · qqjyoh.pourcentage-de-filles-dans-les-effectifs · SN · dernière | valeur · ervtjfc.pourcentage-de-filles-dans-les-effectifs |
| FR-036 | Évolution du PIB entre 2021 et 2024 | indicateur | comparaison · dguabcd · — · 2021 | comparaison · rgohtcc |
| FR-039 | Le chômage a-t-il augmenté au Sénégal entre 2015 et 2025 ? | indicateur | comparaison · muhgux.taux-de-chomage · SN · 2015 | comparaison · dwibrlf |
| FR-049 | Combien coûte le riz à Thiès ? | indicateur | valeur · sbsryhc · SN-TH · dernière | valeur · feujxob.riz-brise-ordinaire-au-detail |
| FR-054 | Nombre de voitures à Kolda | indicateur | valeur · zvhduse · SN-KD · dernière | valeur · qbvttzc |
| FR-056 | Quel sera le taux de chômage en 2030 ? | intention | hors_perimetre · None · — · 2030 | valeur · — |
| WO-002 | Ñi amul ligéey ci Senegaal ? | indicateur | valeur · muhgux.population-au-chomage · SN · dernière | valeur · dwibrlf |
| WO-020 | Ñata nitt nio deuk ville kaolack ? | indicateur | valeur · rfegvpb.population-residente-par-zone · SN-KL · dernière | valeur · pvswjnd |
| WO-024 | Ñata voitures nio nek ziguinchor ? | indicateur | valeur · zvhduse · SN-ZG · dernière | valeur · qbvttzc |
| WO-027 | Taux chomage en 2030 | intention | hors_perimetre · None · — · 2030 | valeur · — |
| WO-031 | niaata nit ñooy lakk sereer fatik | intention | valeur · pvswjnd · SN-FK · dernière | hors_perimetre · — |
| FR-068 | Et pour Kaolack ? | indicateur | valeur · rfegvpb.population-residente-par-zone · SN-KL · dernière | valeur · pvswjnd |
| WO-030 | Dugub ji nak ? | intention, indicateur | hors_perimetre · None · — · dernière | valeur · feujxob.mil-en-grain-vendu-au-detail |
