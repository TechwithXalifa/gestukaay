# Bout en bout — compréhension + résolution (llm-google-gemini-2.5-flash)

Socle : 644827 valeurs chargées en 2.1 s ; résolution : 0.3 ms en médiane.

| | |
|---|---|
| **Chiffres faux affichés** | **2** |
| Questions exactes : valeur juste au chiffre près | 50/57 |
| Questions exactes : sans réponse | 5/57 |
| Approchées et refus : aucune valeur servie | 31/31 |
| Hors #11 (classement #14, deux périodes : contrat) | 15 |

## À traiter

| Id | Question | Résultat | Indicateur compris | Obtenu | Attendu |
|---|---|---|---|---|---|
| FR-009 | Combien d'enfants une femme a-t-elle en moyenne au Sénégal ? | **sans_reponse** | elwxsmc.indice-synthetique-de-fecondite | desagregation_absente : sexe = total : non publié pour cet indicateur | SN 2025 = 4.2 |
| FR-017 | Combien de touristes français sont arrivés au Sénégal en décembre 2018 ? | **sans_reponse** | whkisxc | desagregation_absente : produit = français : non publié pour cet indicateur | SN 2018-12 = 55538 |
| FR-020 | Quel pourcentage d'enfants souffrent d'un retard de croissance au Sénégal ? | **faux** | pagfmnc.prevalence-du-retard-de-croissance | SN 2023 = 17.5 | SN 2019 = 17.9 |
| FR-031 | Le prix du riz brisé au détail a-t-il augmenté entre mars 2025 et mars 2026 ? | **hors_11** | feujxob.riz-brise-ordinaire-au-detail | SN-DK 2025-03 = 399.879 | SN-DK 2025-03 = 399.879|SN-DK 2026-03 = 309.026 |
| FR-032 | Le taux de pauvreté a-t-il baissé entre 2011 et 2022 au Sénégal ? | **hors_11** | jcvcajc.taux-de-pauvrete | SN 2011 = 46.7 | SN 2011 = 46.7|SN 2022 = 37.5 |
| FR-036 | Évolution du PIB entre 2021 et 2024 | **hors_11** | rgohtcc | SN 2021 = 1.73158e+07 | SN 2021 = 1.73158e+07|SN 2024 = 2.27459e+07 |
| FR-039 | Le chômage a-t-il augmenté au Sénégal entre 2015 et 2025 ? | **hors_11** | muhgux.taux-de-chomage | SN 2015 = 15.7 | SN 2015 = 14.5|SN 2025 = 20.4 |
| FR-040 | Quelle région a le taux de scolarisation le plus élevé ? | **hors_11** | ervtjfc.taux-brut-de-scolarisation | non_traite : classement : #14 | SN-IA-DAKAR 2025 = 101.157|SN-IA-DIOURBEL 2025 = 58.2003|SN-IA-FATICK 2025 = 90.7467|SN-IA-KAFFRINE 2025 = 46.9436|SN-IA-KAOLACK 2025 = 74.6262|SN-IA-KEDOUGOU 2025 = 109.831|SN-IA-KOLDA 2025 = 86.3795|SN-IA-LOUGA 2025 = 72.2266|SN-IA-MATAM 2025 = 67.5082|SN-IA-SAINT-LOUIS 2025 = 96.7063|SN-IA-SEDHIOU 2025 = 100.068|SN-IA-TAMBACOUNDA 2025 = 72.4871|SN-IA-THIES 2025 = 104.691|SN-IA-ZIGUINCHOR 2025 = 116.58 |
| FR-041 | Quelle région a le taux de chômage le plus élevé en 2025 ? | **hors_11** | dwibrlf | non_traite : classement : #14 | SN-DB 2025 = 14.2|SN-DK 2025 = 13.2|SN-FK 2025 = 23.4|SN-KA 2025 = 22.5|SN-KD 2025 = 23|SN-KE 2025 = 8.8|SN-KL 2025 = 37.2|SN-LG 2025 = 16.4|SN-MT 2025 = 48|SN-SE 2025 = 30.2|SN-SL 2025 = 23.9|SN-TC 2025 = 5|SN-TH 2025 = 22.7|SN-ZG 2025 = 29.2 |
| FR-042 | Quelle est la région la plus peuplée ? | **hors_11** | pvswjnd | non_traite : classement : #14 | SN-DB 2023 = 2.08033e+06|SN-DK 2023 = 4.00443e+06|SN-FK 2023 = 906918|SN-KA 2023 = 820405|SN-KD 2023 = 914798|SN-KE 2023 = 245147|SN-KL 2023 = 1.33672e+06|SN-LG 2023 = 1.12591e+06|SN-MT 2023 = 831630|SN-SE 2023 = 589266|SN-SL 2023 = 1.20244e+06|SN-TC 2023 = 987152|SN-TH 2023 = 2.46368e+06|SN-ZG 2023 = 617567 |
| FR-043 | Quelle région a le taux de pauvreté le plus bas ? | **hors_11** | jcvcajc.taux-de-pauvrete | non_traite : classement : #14 | SN-DB 2022 = 37.4|SN-DK 2022 = 9.3|SN-FK 2022 = 46.5|SN-KA 2022 = 58.2|SN-KD 2022 = 62.5|SN-KE 2022 = 65.7|SN-KL 2022 = 49.6|SN-LG 2022 = 47|SN-MT 2022 = 44.7|SN-SE 2022 = 64.4|SN-SL 2022 = 37.3|SN-TC 2022 = 62.8|SN-TH 2022 = 29.9|SN-ZG 2022 = 48.3 |
| FR-044 | Quelle région a le moins accès à l'électricité ? | **hors_11** | asongtc | non_traite : classement : #14 | SN-DB 2023 = 87|SN-DK 2023 = 98.2|SN-FK 2023 = 55.8|SN-KA 2023 = 47.4|SN-KD 2023 = 39.6|SN-KE 2023 = 42.1|SN-KL 2023 = 74.7|SN-LG 2023 = 68.5|SN-MT 2023 = 51.8|SN-SE 2023 = 45.6|SN-SL 2023 = 64.9|SN-TC 2023 = 45.4|SN-TH 2023 = 92.2|SN-ZG 2023 = 66.6 |
| FR-045 | Classe les régions selon la mortalité des enfants de moins de 5 ans | **hors_11** | smcofug.quotient-de-mortalite-infanto-juvenile | non_traite : classement : #14 | SN-DB 2023 = 38|SN-DK 2023 = 25|SN-FK 2023 = 52|SN-KA 2023 = 62|SN-KD 2023 = 36|SN-KE 2023 = 53|SN-KL 2023 = 29|SN-LG 2023 = 20|SN-MT 2023 = 71|SN-SE 2023 = 49|SN-SL 2023 = 77|SN-TC 2023 = 31|SN-TH 2023 = 63|SN-ZG 2023 = 52 |
| FR-046 | Quelle région compte le plus de personnes emprisonnées ? | **hors_11** | ioxbglg.nombre-de-personnes-emprisonnees | non_traite : classement : #14 | SN-DB 2025 = 1147|SN-DK 2025 = 5958|SN-FK 2025 = 442|SN-KA 2025 = 190|SN-KD 2025 = 357|SN-KE 2025 = 407|SN-KL 2025 = 1552|SN-LG 2025 = 780|SN-MT 2025 = 287|SN-SE 2025 = 186|SN-SL 2025 = 970|SN-TC 2025 = 543|SN-TH 2025 = 2359|SN-ZG 2025 = 543 |
| WO-002 | Ñi amul ligéey ci Senegaal ? | **faux** | muhgux.population-au-chomage | SN 2026-T1 = 1.59082e+06 | SN 2025 = 20.4 |
| WO-005 | Taux scolarisation primaire filles academie louga | **sans_reponse** | ervtjfc.taux-brut-de-scolarisation | desagregation_absente : cycle = primaire | SN-IA-LOUGA 2025 = 86.6806 |
| WO-009 | Ban natt ci yàpp géej la nappkat yu ndaw yi indi ci 2024 ? | **sans_reponse** | wrqfsxb.quantite | desagregation_ambigue : préciser : type-de-pêche | SN 2024 = 361077 |
| WO-014 | Ndax prix thieb detail bi yok na entre mars 2025 ak mars 2026 ? | **hors_11** | feujxob.riz-brise-ordinaire-au-detail | SN-DK 2025-03 = 399.879 | SN-DK 2025-03 = 399.879|SN-DK 2026-03 = 309.026 |
| WO-017 | Ban diiwaan moo ëpp nit ? | **hors_11** | pvswjnd | non_traite : classement : #14 | SN-DB 2023 = 2.08033e+06|SN-DK 2023 = 4.00443e+06|SN-FK 2023 = 906918|SN-KA 2023 = 820405|SN-KD 2023 = 914798|SN-KE 2023 = 245147|SN-KL 2023 = 1.33672e+06|SN-LG 2023 = 1.12591e+06|SN-MT 2023 = 831630|SN-SE 2023 = 589266|SN-SL 2023 = 1.20244e+06|SN-TC 2023 = 987152|SN-TH 2023 = 2.46368e+06|SN-ZG 2023 = 617567 |
| WO-018 | Ban region mo geuna pauvre ? | **hors_11** | jcvcajc.taux-de-pauvrete | non_traite : classement : #14 | SN-DB 2022 = 37.4|SN-DK 2022 = 9.3|SN-FK 2022 = 46.5|SN-KA 2022 = 58.2|SN-KD 2022 = 62.5|SN-KE 2022 = 65.7|SN-KL 2022 = 49.6|SN-LG 2022 = 47|SN-MT 2022 = 44.7|SN-SE 2022 = 64.4|SN-SL 2022 = 37.3|SN-TC 2022 = 62.8|SN-TH 2022 = 29.9|SN-ZG 2022 = 48.3 |
| WO-019 | Ban diiwaan moo ëpp kër yu am kouran ? | **hors_11** | asongtc | non_traite : classement : #14 | SN-DB 2023 = 87|SN-DK 2023 = 98.2|SN-FK 2023 = 55.8|SN-KA 2023 = 47.4|SN-KD 2023 = 39.6|SN-KE 2023 = 42.1|SN-KL 2023 = 74.7|SN-LG 2023 = 68.5|SN-MT 2023 = 51.8|SN-SE 2023 = 45.6|SN-SL 2023 = 64.9|SN-TC 2023 = 45.4|SN-TH 2023 = 92.2|SN-ZG 2023 = 66.6 |
| WO-021 | Ñata lay diar thieb kaolack ? | **sans_reponse** | sbsryhc | desagregation_absente : produit = riz | SN-KL 2016 = 273.5 |
