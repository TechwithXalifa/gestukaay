# Compréhension — évaluation (llm-google-gemini-2.5-flash-lite)

103 questions du jeu de test (#10). Une question est juste si l'intention, l'indicateur, les zones et la période le sont.

| | Score |
|---|---|
| **Tout juste** | **73/103 (71 %)** |
| Français | 54/72 (75 %) |
| Wolof | 19/31 (61 %) |
| Intention | 101/103 (98 %) |
| Indicateur | 80/103 (78 %) |
| Zones | 103/103 (100 %) |
| Période | 97/103 (94 %) |
| Latence médiane / max | 870 ms / 1995 ms |
| Secours par règles | 5 |
| Coût total | 0.0176 $ |

## Questions fausses

| Id | Question | Faux | Obtenu | Attendu |
|---|---|---|---|---|
| FR-007 | Quel est le taux de mortalité des enfants de moins de 5 ans au Sénégal ? | indicateur | valeur · fxwvzqc.taux-de-mortalite-infanto-juvenile-0-5-ans · SN · dernière | valeur · smcofug.quotient-de-mortalite-infanto-juvenile |
| FR-012 | Quel est le niveau de l'indice harmonisé des prix à la consommation ? | periode | valeur · tsghpfc.indice-global · — · 2023 | valeur · tsghpfc.indice-global |
| FR-015 | Quelle quantité de produits la pêche artisanale a-t-elle débarquée en 2024 ? | indicateur | valeur · zxtmqqg · — · 2024 | valeur · wrqfsxb.quantite |
| FR-020 | Quel pourcentage d'enfants souffrent d'un retard de croissance au Sénégal ? | indicateur | valeur · pagfmnc.prevalence-du-retard-de-croissance · SN · dernière | valeur · xsitdae.enfants-souffrant-dun-retard-de-croissance |
| FR-028 | Quel est le pourcentage de filles parmi les élèves du secondaire au Sénégal ? | indicateur | valeur · qqjyoh.pourcentage-de-filles-dans-les-effectifs · SN · dernière | valeur · ervtjfc.pourcentage-de-filles-dans-les-effectifs |
| FR-030 | Chômage à Dakar et à Thiès en 2024 | indicateur | comparaison · muhgux.taux-de-chomage · SN-DK,SN-TH · 2024 | comparaison · dwibrlf |
| FR-033 | Accès à l'électricité : Kédougou comparé à Dakar | indicateur | comparaison · ahjjzgc.taux-dacces-des-menages-a-lelectricite · SN-KE,SN-DK · dernière | comparaison · asongtc |
| FR-034 | Taux brut de scolarisation à l'élémentaire : académies de Kolda et de Ziguinchor | indicateur | comparaison · qzvvpic.taux-brut-de-scolarisation-a-lelementaire · SN-IA-KOLDA,SN-IA-ZIGUINCHOR · dernière | comparaison · ervtjfc.taux-brut-de-scolarisation |
| FR-035 | Mortalité des moins de 5 ans à Kolda comparée à la moyenne nationale | indicateur | comparaison · fxwvzqc.taux-de-mortalite-infanto-juvenile-0-5-ans · SN-KD,SN · dernière | comparaison · smcofug.quotient-de-mortalite-infanto-juvenile |
| FR-039 | Le chômage a-t-il augmenté au Sénégal entre 2015 et 2025 ? | indicateur | comparaison · muhgux.taux-de-chomage · SN · 2015 | comparaison · dwibrlf |
| FR-044 | Quelle région a le moins accès à l'électricité ? | indicateur | classement · ahjjzgc.taux-dacces-des-menages-a-lelectricite · — · dernière | classement · asongtc |
| FR-048 | Quel est le taux de scolarisation à Dakar ? | indicateur | valeur · kchmjhc.taux-de-scolarisation · SN-DK · dernière | valeur · ervtjfc.taux-brut-de-scolarisation |
| FR-049 | Combien coûte le riz à Thiès ? | indicateur | valeur · feujxob.riz-long-grains-vendu-au-detail · SN-TH · dernière | valeur · feujxob.riz-brise-ordinaire-au-detail |
| FR-053 | Quel pourcentage des ménages ont l'électricité à Pikine ? | indicateur | valeur · ahjjzgc.taux-dacces-des-menages-a-lelectricite · SN-DK-PIKINE · dernière | valeur · asongtc |
| FR-054 | Nombre de voitures à Kolda | indicateur | valeur · zvhduse · SN-KD · dernière | valeur · qbvttzc |
| FR-060 | Quel temps fera-t-il demain à Dakar ? | intention | valeur · fxwvzqc.temps-de-doublement · SN-DK · dernière | hors_perimetre · — |
| WO-001 | Ñaata nit ñoo dëkk Tiés ? | periode | valeur · pvswjnd · SN-TH · 2023 | valeur · pvswjnd |
| WO-002 | Ñi amul ligéey ci Senegaal ? | indicateur | valeur · muhgux.population-au-chomage · SN · dernière | valeur · dwibrlf |
| WO-013 | Limu askanu Ndakaaru ak Kaolack | indicateur, periode | comparaison · uzptmtd · SN-DK,SN-KL · 2023 | comparaison · pvswjnd |
| WO-015 | Chomage dakar ak ziguinchor en 2025 | indicateur | comparaison · muhgux.taux-de-chomage · SN-DK,SN-ZG · 2025 | comparaison · dwibrlf |
| WO-016 | Acces electricite louga ak matam | indicateur | comparaison · ahjjzgc.taux-dacces-des-menages-a-lelectricite · SN-LG,SN-MT · dernière | comparaison · asongtc |
| WO-017 | Ban diiwaan moo ëpp nit ? | periode | classement · pvswjnd · — · 2023 | classement · pvswjnd |
| WO-019 | Ban diiwaan moo ëpp kër yu am kouran ? | indicateur | classement · ahjjzgc.taux-dacces-des-menages-a-lelectricite · — · dernière | classement · asongtc |
| WO-021 | Ñata lay diar thieb kaolack ? | indicateur | valeur · sbsryhc · SN-KL · dernière | valeur · feujxob.riz-brise-ordinaire-au-detail |
| WO-024 | Ñata voitures nio nek ziguinchor ? | indicateur | valeur · zvhduse · SN-ZG · dernière | valeur · qbvttzc |
| WO-031 | niaata nit ñooy lakk sereer fatik | intention | valeur · pvswjnd · SN-FK · 2023 | hors_perimetre · — |
| FR-068 | Et pour Kaolack ? | periode | valeur · pvswjnd · SN-KL · 2023 | valeur · pvswjnd |
| FR-069 | Et en 2025 ? | indicateur | valeur · muhgux.taux-de-chomage · SN-DK,SN-TH · 2025 | valeur · dwibrlf |
| WO-029 | Kaolack nak ? | periode | valeur · pvswjnd · SN-KL · 2023 | valeur · pvswjnd |
| WO-030 | Dugub ji nak ? | indicateur | valeur · feujxob.riz-brise-ordinaire-au-detail · — · dernière | valeur · feujxob.mil-en-grain-vendu-au-detail |
