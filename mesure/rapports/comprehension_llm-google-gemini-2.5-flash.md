# Compréhension — évaluation (llm-google-gemini-2.5-flash)

103 questions du jeu de test (#10). Une question est juste si l'intention, l'indicateur, les zones et la période le sont.

| | Score |
|---|---|
| **Tout juste** | **84/103 (82 %)** |
| Français | 62/72 (86 %) |
| Wolof | 22/31 (71 %) |
| Intention | 95/103 (92 %) |
| Indicateur | 93/103 (90 %) |
| Zones | 103/103 (100 %) |
| Période | 99/103 (96 %) |
| Latence médiane / max | 1227 ms / 1862 ms |
| Secours par règles | 11 |
| Coût total | 0.0611 $ |

## Questions fausses

| Id | Question | Faux | Obtenu | Attendu |
|---|---|---|---|---|
| FR-001 | Combien d'habitants à Thiès ? | periode | valeur · pvswjnd · SN-TH · 2023 | valeur · pvswjnd |
| FR-015 | Quelle quantité de produits la pêche artisanale a-t-elle débarquée en 2024 ? | indicateur | valeur · zxtmqqg · — · 2024 | valeur · wrqfsxb.quantite |
| FR-018 | Quelle est la production de riz du Sénégal ? | intention, indicateur | hors_perimetre · None · SN · dernière | valeur · ovothxc.production |
| FR-027 | Quelle sera l'espérance de vie au Sénégal en 2035 ? | intention, indicateur | hors_perimetre · None · SN · 2035 | valeur · pexioke.esperance-de-vie-a-la-naissance |
| FR-033 | Accès à l'électricité : Kédougou comparé à Dakar | indicateur | comparaison · ahjjzgc.taux-dacces-des-menages-a-lelectricite · SN-KE,SN-DK · dernière | comparaison · asongtc |
| FR-044 | Quelle région a le moins accès à l'électricité ? | indicateur | classement · ahjjzgc.taux-dacces-des-menages-a-lelectricite · — · dernière | classement · asongtc |
| FR-056 | Quel sera le taux de chômage en 2030 ? | intention | hors_perimetre · None · — · 2030 | valeur · — |
| FR-057 | Quelle sera l'inflation en 2027 ? | intention | hors_perimetre · None · — · 2027 | valeur · — |
| WO-001 | Ñaata nit ñoo dëkk Tiés ? | periode | valeur · pvswjnd · SN-TH · 2023 | valeur · pvswjnd |
| WO-002 | Ñi amul ligéey ci Senegaal ? | indicateur | valeur · muhgux.population-au-chomage · SN · dernière | valeur · dwibrlf |
| WO-006 | Ban tolluwaayu ñàkk lañu am Matam ? | indicateur | valeur · dwibrlf · SN-MT · dernière | valeur · jcvcajc.taux-de-pauvrete |
| WO-017 | Ban diiwaan moo ëpp nit ? | indicateur | classement · ioxbglg.nombre-de-personnes-emprisonnees · — · dernière | classement · pvswjnd |
| WO-021 | Ñata lay diar thieb kaolack ? | intention, indicateur | hors_perimetre · None · SN-KL · dernière | valeur · feujxob.riz-brise-ordinaire-au-detail |
| WO-027 | Taux chomage en 2030 | intention | hors_perimetre · None · — · 2030 | valeur · — |
| WO-031 | niaata nit ñooy lakk sereer fatik | intention | valeur · ioxbglg.nombre-de-personnes-emprisonnees · SN-FK · dernière | hors_perimetre · — |
| FR-068 | Et pour Kaolack ? | periode | valeur · pvswjnd · SN-KL · 2023 | valeur · pvswjnd |
| FR-069 | Et en 2025 ? | intention | comparaison · dwibrlf · SN-DK,SN-TH · 2025 | valeur · dwibrlf |
| WO-029 | Kaolack nak ? | periode | valeur · pvswjnd · SN-KL · 2023 | valeur · pvswjnd |
| WO-030 | Dugub ji nak ? | indicateur | valeur · feujxob.riz-brise-ordinaire-au-detail · — · dernière | valeur · feujxob.mil-en-grain-vendu-au-detail |
