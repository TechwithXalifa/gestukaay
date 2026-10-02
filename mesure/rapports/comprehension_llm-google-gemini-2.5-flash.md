# Compréhension — évaluation (llm-google-gemini-2.5-flash)

103 questions du jeu de test (#10). Une question est juste si l'intention, l'indicateur, les zones et la période le sont.

| | Score |
|---|---|
| **Tout juste** | **95/103 (92 %)** |
| Français | 66/72 (92 %) |
| Wolof | 29/31 (94 %) |
| Intention | 99/103 (96 %) |
| Indicateur | 97/103 (94 %) |
| Zones | 103/103 (100 %) |
| Période | 103/103 (100 %) |
| Latence médiane / max | 1160 ms / 1925 ms |
| Secours par règles | 5 |
| Coût total | 0.0697 $ |

## Questions fausses

| Id | Question | Faux | Obtenu | Attendu |
|---|---|---|---|---|
| FR-015 | Quelle quantité de produits la pêche artisanale a-t-elle débarquée en 2024 ? | indicateur | valeur · zxtmqqg · — · 2024 | valeur · wrqfsxb.quantite |
| FR-018 | Quelle est la production de riz du Sénégal ? | intention, indicateur | hors_perimetre · None · SN · dernière | valeur · ovothxc.production |
| FR-049 | Combien coûte le riz à Thiès ? | indicateur | valeur · sbsryhc · SN-TH · dernière | valeur · feujxob.riz-brise-ordinaire-au-detail |
| FR-056 | Quel sera le taux de chômage en 2030 ? | intention | hors_perimetre · None · — · 2030 | valeur · — |
| FR-067 | Quel est le taux de criminalité à Kaolack ? | intention, indicateur | hors_perimetre · None · SN-KL · dernière | valeur · iocwzud |
| WO-002 | Ñi amul ligéey ci Senegaal ? | indicateur | valeur · muhgux.population-au-chomage · SN · dernière | valeur · dwibrlf |
| WO-021 | Ñata lay diar thieb kaolack ? | indicateur | valeur · sbsryhc · SN-KL · dernière | valeur · feujxob.riz-brise-ordinaire-au-detail |
| FR-069 | Et en 2025 ? | intention | comparaison · dwibrlf · SN-DK,SN-TH · 2025 | valeur · dwibrlf |
