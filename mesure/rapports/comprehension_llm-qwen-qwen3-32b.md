# Compréhension — évaluation (llm-qwen-qwen3-32b)

103 questions du jeu de test (#10). Une question est juste si l'intention, l'indicateur, les zones et la période le sont.

| | Score |
|---|---|
| **Tout juste** | **85/103 (83 %)** |
| Français | 61/72 (85 %) |
| Wolof | 24/31 (77 %) |
| Intention | 94/103 (91 %) |
| Indicateur | 94/103 (91 %) |
| Zones | 103/103 (100 %) |
| Période | 103/103 (100 %) |

## Questions fausses

| Id | Question | Faux | Obtenu | Attendu |
|---|---|---|---|---|
| FR-018 | Quelle est la production de riz du Sénégal ? | indicateur | valeur · feujxob.riz-brise-ordinaire-au-detail · SN · dernière | valeur · ovothxc.production |
| FR-021 | Quel est le coefficient de Gini du Sénégal ? | indicateur | valeur · bdubwzf.coefficient-de-gini · SN · dernière | valeur · qjyrtof.gini |
| FR-025 | Combien y a-t-il de jeunes de moins de 15 ans au Sénégal ? | indicateur | valeur · yrzztrb.pourcentage-de-jeunes-femmes-de-20-a-24-ans-en · SN · dernière | valeur · pvswjnd |
| FR-060 | Quel temps fera-t-il demain à Dakar ? | intention | valeur · fxwvzqc.temps-de-doublement · SN-DK · dernière | hors_perimetre · — |
| FR-061 | Combien d'habitants à Paris ? | intention | valeur · pvswjnd · — · dernière | hors_perimetre · — |
| FR-062 | Combien gagne un chauffeur de taxi à Dakar ? | intention | valeur · feujxob.transport-collectif-en-taxi-7-places-dakar-thies · SN-DK · dernière | hors_perimetre · — |
| FR-065 | euh bon voilà quoi | intention | valeur · xfgtfjb.etat-bon-moyen~% · — · dernière | hors_perimetre · — |
| FR-066 | Combien de vaches a mon voisin ? | intention | valeur · rtekraf.robinet-du-voisin · — · dernière | hors_perimetre · — |
| FR-071 | Combien de personnes parlent sérère au Sénégal ? | intention | valeur · ioxbglg.nombre-de-personnes-emprisonnees · SN · dernière | hors_perimetre · — |
| FR-072 | Combien de Sénégalais sont partis en pèlerinage à La Mecque en 2024 ? | intention | valeur · fuccbbg.senegalais · — · 2024 | hors_perimetre · — |
| WO-001 | Ñaata nit ñoo dëkk Tiés ? | indicateur | valeur · rfegvpb.taux-durbanisation · SN-TH · dernière | valeur · pvswjnd |
| WO-005 | Taux scolarisation primaire filles academie louga | indicateur | valeur · ervtjfc.pourcentage-de-filles-dans-les-effectifs · SN-IA-LOUGA · dernière | valeur · ervtjfc.taux-brut-de-scolarisation |
| WO-017 | Ban diiwaan moo ëpp nit ? | indicateur | classement · ioxbglg.nombre-de-personnes-emprisonnees · — · dernière | classement · pvswjnd |
| WO-028 | waa man tay dama xiif trop lii mbaa diamm la tamit | intention | valeur · ewnjbnf.menages-rencontrant-des-contraintes-pouvant-empecher-le-developpement-de-lexploitation-liees · — · dernière | hors_perimetre · — |
| WO-031 | niaata nit ñooy lakk sereer fatik | intention | valeur · ioxbglg.nombre-de-personnes-emprisonnees · SN-FK · dernière | hors_perimetre · — |
| FR-070 | Et le mil ? | indicateur | valeur · feujxob.riz-brise-ordinaire-au-detail · — · dernière | valeur · feujxob.mil-en-grain-vendu-au-detail |
| WO-029 | Kaolack nak ? | indicateur | valeur · rfegvpb.taux-durbanisation · SN-KL · dernière | valeur · pvswjnd |
| WO-030 | Dugub ji nak ? | indicateur | valeur · feujxob.riz-brise-ordinaire-au-detail · — · dernière | valeur · feujxob.mil-en-grain-vendu-au-detail |
