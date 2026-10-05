# Transcription des notes vocales wolof (#27, compréhension LLM)

Mesure du 05/10/2026 : 62 notes vocales (aziz, kbd), dont 62 questions du jeu de test.

**Plafond** (texte de référence tapé, sans transcription) : bonne réponse pour 51/62 (82.3 %). Une transcription parfaite ne ferait pas mieux.

| Candidat | Bonne réponse | WER médian | CER médian | Latence médiane | Latence max |
|---|---|---|---|---|---|
| m-kiriku | **35/62** (56.5 %) | 37.4 % | 14.1 % | 1.90 s | 2.35 s |
| kiriku-wolof | **35/62** (56.5 %) | 50.0 % | 16.7 % | 1.84 s | 2.34 s |

Latences mesurées sur la machine du test (Mac M3 Pro), pas sur le serveur de démonstration.

## m-kiriku

| Note | Référence | Transcription | WER | Réponse |
|---|---|---|---|---|
| WO-001_aziz.ogg | Ñaata nit ñoo dëkk Tiés ? | ñaata nit ñoo dëkk thiès | 20.0 % | juste |
| WO-001_kbd.opus | Ñaata nit ñoo dëkk Tiés ? | ñaata nit ñoo dëkk thiès | 20.0 % | juste |
| WO-002_aziz.ogg | Ñi amul ligéey ci Senegaal ? | ñi amul liggéey ci sénégal | 40.0 % | **fausse** |
| WO-002_kbd.opus | Ñi amul ligéey ci Senegaal ? | ñi amul liggéey ci sénégal | 40.0 % | **fausse** |
| WO-003_aziz.ogg | Ñata la kilo thieb bou dagg détail di diar ? | ñaata la kilo ceeb bu dagg détaillé di jar | 55.6 % | juste |
| WO-003_kbd.opus | Ñata la kilo thieb bou dagg détail di diar ? | ñaata la kilo ceeb bu dagg détaillé bi jër | 66.7 % | juste |
| WO-004_aziz.ogg | Ban pourcentage keur kaffrine nio am courant ? | ban pourcentage kër kaffrine ñoo am courant | 28.6 % | juste |
| WO-004_kbd.opus | Ban pourcentage keur kaffrine nio am courant ? | ban pourcentage kër kaffrine ñooy am courant | 28.6 % | juste |
| WO-005_aziz.ogg | Taux scolarisation primaire filles academie louga | taux scolaire fi académie louga | 66.7 % | **fausse** |
| WO-005_kbd.opus | Taux scolarisation primaire filles academie louga | taux scolaire fi académie louga | 66.7 % | **fausse** |
| WO-006_aziz.ogg | Ban tolluwaayu ñàkk lañu am Matam ? | ban tolluwaayu ñakk lañu ame maatam | 50.0 % | **fausse** |
| WO-006_kbd.opus | Ban tolluwaayu ñàkk lañu am Matam ? | ban tolluwaayu ñakk lañu ame matam | 33.3 % | juste |
| WO-007_aziz.ogg | Ñata jigeen nio deuk sedhiou ? | ñaata jigéen ñoo dëkk seajo | 100.0 % | **fausse** |
| WO-007_kbd.opus | Ñata jigeen nio deuk sedhiou ? | ñaata jigéen ñoo dëkk seju | 100.0 % | **fausse** |
| WO-008_aziz.ogg | Ñata nitt nio nek kaso senegal ? | ñaata nit ñoo nekk kaso senegaal | 83.3 % | juste |
| WO-008_kbd.opus | Ñata nitt nio nek kaso senegal ? | ñaata nit ñoo nekk kaso sénégal | 83.3 % | juste |
| WO-009_aziz.ogg | Ban natt ci yàpp géej la nappkat yu ndaw yi indi ci 2024 ? | bannaat si yàpp géej la nappkat yu ndaw yi indi ci 2024 24 | 30.8 % | **fausse** |
| WO-009_kbd.opus | Ban natt ci yàpp géej la nappkat yu ndaw yi indi ci 2024 ? | ban nat ci yàpp géej la napkat yu ndaw yi indi ci 2024 nga def ko ci kanam | 53.8 % | **fausse** |
| WO-010_aziz.ogg | Ñata xale moins de 5 ans nioy de senegal (sur 1000) ? | ñaata xale moins de 5 ans ñooy dee sénégal | 54.5 % | juste |
| WO-010_kbd.opus | Ñata xale moins de 5 ans nioy de senegal (sur 1000) ? | ñaata xale moins de 5 ans ñooy dee sénégal | 54.5 % | juste |
| WO-011_aziz.ogg | Proportion xale yi am vaccins yeup tamba | proportion xale yi am vaccin yëpp tamba | 28.6 % | juste |
| WO-011_kbd.opus | Proportion xale yi am vaccins yeup tamba | proportion xale yi am vaccin yëpp tamba | 28.6 % | juste |
| WO-012_aziz.ogg | Taux chomage jeunes 15 a 24 ans dakar | taux chomage jeunes 15 à 24 ans dakar | 12.5 % | juste |
| WO-012_kbd.opus | Taux chomage jeunes 15 a 24 ans dakar | taux de chomage jeunes 15 à 24 ans dakar | 25.0 % | juste |
| WO-013_aziz.ogg | Limu askanu Ndakaaru ak Kaolack | liimu askanu ndakaaru ak kaolack | 20.0 % | juste |
| WO-013_kbd.opus | Limu askanu Ndakaaru ak Kaolack | limu askanu ndakaaru ak kawlak | 20.0 % | **fausse** |
| WO-014_aziz.ogg | Ndax prix thieb detail bi yok na entre mars 2025 ak mars 2026 ? | ndax prix ceeb détaay bi yokku na entre mars 2025 ak mars 2026 | 23.1 % | juste |
| WO-014_kbd.opus | Ndax prix thieb detail bi yok na entre mars 2025 ak mars 2026 ? | ndax prix ceeb détaillé bi yokku na entre mars 25 ak mars 26 | 38.5 % | **fausse** |
| WO-015_aziz.ogg | Chomage dakar ak ziguinchor en 2025 | chomage dakar ak ziguinchor en 2025éne | 16.7 % | juste |
| WO-015_kbd.opus | Chomage dakar ak ziguinchor en 2025 | chumage dakar ak ziguinchor en 2025éne | 33.3 % | **fausse** |
| WO-016_aziz.ogg | Acces electricite louga ak matam | accès électricité louga ak matam | 40.0 % | juste |
| WO-016_kbd.opus | Acces electricite louga ak matam | accès électricité louga ak matam | 40.0 % | juste |
| WO-017_aziz.ogg | Ban diiwaan moo ëpp nit ? | ban diwaan moo ëpp nit | 20.0 % | juste |
| WO-017_kbd.opus | Ban diiwaan moo ëpp nit ? | ban diwaan moo ëpp nit | 20.0 % | juste |
| WO-018_aziz.ogg | Ban region mo geuna pauvre ? | ban région mooy gëna poore | 80.0 % | **fausse** |
| WO-018_kbd.opus | Ban region mo geuna pauvre ? | ban région moom gëna poivre | 80.0 % | **fausse** |
| WO-019_aziz.ogg | Ban diiwaan moo ëpp kër yu am kouran ? | ban diwaan moo ëpp kër yu am courant | 25.0 % | juste |
| WO-019_kbd.opus | Ban diiwaan moo ëpp kër yu am kouran ? | ban diwaan moo ëpp kër yu am courant | 25.0 % | juste |
| WO-020_aziz.ogg | Ñata nitt nio deuk ville kaolack ? | ñaata nit ñoo dëkk ville kaolack | 66.7 % | **fausse** |
| WO-020_kbd.opus | Ñata nitt nio deuk ville kaolack ? | ñaata nit ñoo dëkk ville kaolack | 66.7 % | **fausse** |
| WO-021_aziz.ogg | Ñata lay diar thieb kaolack ? | ñaata lay jar ceeb kaolack | 60.0 % | juste |
| WO-021_kbd.opus | Ñata lay diar thieb kaolack ? | ñaata laay jëm ceeb kaolack | 80.0 % | **fausse** |
| WO-022_aziz.ogg | Taux scolarisation dakar | taux scolaire dakaar | 66.7 % | **fausse** |
| WO-022_kbd.opus | Taux scolarisation dakar | taux scolaire dakaar | 66.7 % | **fausse** |
| WO-023_aziz.ogg | Limu askanu Senegaal ci atum 2040 | limu askanu senegaal ci atum 2040 | 0.0 % | juste |
| WO-023_kbd.opus | Limu askanu Senegaal ci atum 2040 | ly mo askanu sénégal ci atum 2040 | 50.0 % | juste |
| WO-024_aziz.ogg | Ñata voitures nio nek ziguinchor ? | ñaata voiture ñoo nekk ziguinchor | 80.0 % | **fausse** |
| WO-024_kbd.opus | Ñata voitures nio nek ziguinchor ? | ñaata voiture ñoo nekk ziguinchor | 80.0 % | **fausse** |
| WO-025_aziz.ogg | Kan mooy njiitu réewum Senegaal ? | kan mooy njiitu réewum senegaal | 0.0 % | juste |
| WO-025_kbd.opus | Kan mooy njiitu réewum Senegaal ? | kan maa njiitu réewum senegaal | 20.0 % | **fausse** |
| WO-026_aziz.ogg | Naka météo bi di mel euleuk ? | naka météo bi di mel ëllëg | 16.7 % | juste |
| WO-026_kbd.opus | Naka météo bi di mel euleuk ? | naka météo di mel ëlëg | 33.3 % | **fausse** |
| WO-027_aziz.ogg | Taux chomage en 2030 | taux chomage en 2030 | 0.0 % | juste |
| WO-027_kbd.opus | Taux chomage en 2030 | taux de chomage en 2030 | 25.0 % | juste |
| WO-028_aziz.ogg | waa man tay dama xiif trop lii mbaa diamm la tamit | waa man tey dama xiif torop libaa jàmm la tamit | 45.5 % | juste |
| WO-028_kbd.opus | waa man tay dama xiif trop lii mbaa diamm la tamit | waa man de dama xëftoroq lii mbaa jàmm la tamit | 36.4 % | juste |
| WO-029_aziz.ogg | Kaolack nak ? | kaolack nag | 50.0 % | **fausse** |
| WO-029_kbd.opus | Kaolack nak ? | kaolack nak | 0.0 % | **fausse** |
| WO-030_aziz.ogg | Dugub ji nak ? | dugub ji nag | 33.3 % | **fausse** |
| WO-030_kbd.opus | Dugub ji nak ? | dugub ji nag | 33.3 % | **fausse** |
| WO-031_aziz.ogg | niaata nit ñooy lakk sereer fatik | ñaata nit ñooy lakk séeréer fatik | 33.3 % | juste |
| WO-031_kbd.opus | niaata nit ñooy lakk sereer fatik | ñaata nit ñooy làkk séeréer fatick | 66.7 % | juste |

## kiriku-wolof

| Note | Référence | Transcription | WER | Réponse |
|---|---|---|---|---|
| WO-001_aziz.ogg | Ñaata nit ñoo dëkk Tiés ? | ñaata nit ñoo dëkk thiès | 20.0 % | juste |
| WO-001_kbd.opus | Ñaata nit ñoo dëkk Tiés ? | ñaata nit ñoo dëkk thiès | 20.0 % | juste |
| WO-002_aziz.ogg | Ñi amul ligéey ci Senegaal ? | ñi amul liggéey ci senegaal | 20.0 % | **fausse** |
| WO-002_kbd.opus | Ñi amul ligéey ci Senegaal ? | ñi amul liggéey ci senegal | 40.0 % | **fausse** |
| WO-003_aziz.ogg | Ñata la kilo thieb bou dagg détail di diar ? | ñaata la kilo ceeb bu dakk detaay di jar | 66.7 % | juste |
| WO-003_kbd.opus | Ñata la kilo thieb bou dagg détail di diar ? | ñaata la kilo ceeb bu dagg detaay di jar | 55.6 % | juste |
| WO-004_aziz.ogg | Ban pourcentage keur kaffrine nio am courant ? | ban pourcentage kër kaffrine ñoo am kuréel | 42.9 % | juste |
| WO-004_kbd.opus | Ban pourcentage keur kaffrine nio am courant ? | ban pourcentage kër kaffrine ñoo am courant | 28.6 % | juste |
| WO-005_aziz.ogg | Taux scolarisation primaire filles academie louga | teau scolaarisation primaire fii académia louga | 66.7 % | **fausse** |
| WO-005_kbd.opus | Taux scolarisation primaire filles academie louga | toutes scolarisation primaire fii académia louga | 50.0 % | **fausse** |
| WO-006_aziz.ogg | Ban tolluwaayu ñàkk lañu am Matam ? | ban tolluwaayu ñaq lañ ame maatam | 66.7 % | **fausse** |
| WO-006_kbd.opus | Ban tolluwaayu ñàkk lañu am Matam ? | ban tolluwaayu ñakk lañu am matam? | 16.7 % | **fausse** |
| WO-007_aziz.ogg | Ñata jigeen nio deuk sedhiou ? | ñaata jigéen ñoo dëkk seju | 100.0 % | **fausse** |
| WO-007_kbd.opus | Ñata jigeen nio deuk sedhiou ? | ñaata jigéen ñoo dëkk seju | 100.0 % | **fausse** |
| WO-008_aziz.ogg | Ñata nitt nio nek kaso senegal ? | ñaata nit ñoo nekk kaso senegal | 66.7 % | juste |
| WO-008_kbd.opus | Ñata nitt nio nek kaso senegal ? | ñaata nit ñoo nekk kaso senegaal | 83.3 % | juste |
| WO-009_aziz.ogg | Ban natt ci yàpp géej la nappkat yu ndaw yi indi ci 2024 ? | ban at ci yàpp géej la nappkat yu ndaw yi indi ci 2024 | 7.7 % | **fausse** |
| WO-009_kbd.opus | Ban natt ci yàpp géej la nappkat yu ndaw yi indi ci 2024 ? | ban natt ci yàpp géej la nappkat yu ndaw yi indi ci 2024 | 0.0 % | **fausse** |
| WO-010_aziz.ogg | Ñata xale moins de 5 ans nioy de senegal (sur 1000) ? | ñaata xale moo fañu def ci kan ñooy dee senegaal | 90.9 % | juste |
| WO-010_kbd.opus | Ñata xale moins de 5 ans nioy de senegal (sur 1000) ? | ñaata xale moo yaa daceen taw ñooy dee senegaal | 90.9 % | juste |
| WO-011_aziz.ogg | Proportion xale yi am vaccins yeup tamba | proportion xale yi am vaccin yépp tamba | 28.6 % | juste |
| WO-011_kbd.opus | Proportion xale yi am vaccins yeup tamba | proportion xale yi am vaccin yépp tamba | 28.6 % | juste |
| WO-012_aziz.ogg | Taux chomage jeunes 15 a 24 ans dakar | déwet soma jonne kër jeune 15 à 24 ans dakar | 75.0 % | **fausse** |
| WO-012_kbd.opus | Taux chomage jeunes 15 a 24 ans dakar | taw de chomage jeune 15 à 24 ans dakar | 50.0 % | juste |
| WO-013_aziz.ogg | Limu askanu Ndakaaru ak Kaolack | ly-mo-askanu ndakaaru ak kaolack | 40.0 % | juste |
| WO-013_kbd.opus | Limu askanu Ndakaaru ak Kaolack | limu askanu ndakaaru ak kaolack | 0.0 % | juste |
| WO-014_aziz.ogg | Ndax prix thieb detail bi yok na entre mars 2025 ak mars 2026 ? | ndax prix ceeb detail bi yokku na entre mars 2025 ak mars 2026 | 15.4 % | juste |
| WO-014_kbd.opus | Ndax prix thieb detail bi yok na entre mars 2025 ak mars 2026 ? | ndax piri ceeb detaille bi yokku na entre mars 2025 ak mars 2026 | 30.8 % | juste |
| WO-015_aziz.ogg | Chomage dakar ak ziguinchor en 2025 | chomage dakar ak ziguinchor en deux mille vingt cinq | 66.7 % | juste |
| WO-015_kbd.opus | Chomage dakar ak ziguinchor en 2025 | chomage dakar ak ziguinchor en 2025 | 0.0 % | juste |
| WO-016_aziz.ogg | Acces electricite louga ak matam | accès électricité louga ak matam | 40.0 % | juste |
| WO-016_kbd.opus | Acces electricite louga ak matam | accès électricité louga ak matam | 40.0 % | juste |
| WO-017_aziz.ogg | Ban diiwaan moo ëpp nit ? | ban diwaan moo ëpp nit | 20.0 % | juste |
| WO-017_kbd.opus | Ban diiwaan moo ëpp nit ? | ban diwaan moo ëpp nit | 20.0 % | juste |
| WO-018_aziz.ogg | Ban region mo geuna pauvre ? | ban région moo gëna pauvre | 60.0 % | juste |
| WO-018_kbd.opus | Ban region mo geuna pauvre ? | ban région moo gëna pauvre | 60.0 % | juste |
| WO-019_aziz.ogg | Ban diiwaan moo ëpp kër yu am kouran ? | ban diwaan moo ëpp kër yu am kuran | 25.0 % | juste |
| WO-019_kbd.opus | Ban diiwaan moo ëpp kër yu am kouran ? | ban diwaan moo ëpp kër yu am courant | 25.0 % | juste |
| WO-020_aziz.ogg | Ñata nitt nio deuk ville kaolack ? | ñaata nit ñoo dëkk ville kaolack | 66.7 % | **fausse** |
| WO-020_kbd.opus | Ñata nitt nio deuk ville kaolack ? | ñaata nit ñoo dëkk ville kaolack | 66.7 % | **fausse** |
| WO-021_aziz.ogg | Ñata lay diar thieb kaolack ? | ñaata lay jar ceeb kawlak | 80.0 % | **fausse** |
| WO-021_kbd.opus | Ñata lay diar thieb kaolack ? | ñaata lay jàd ceeb kaolack | 60.0 % | **fausse** |
| WO-022_aziz.ogg | Taux scolarisation dakar | teau scolaireisation dakar | 66.7 % | **fausse** |
| WO-022_kbd.opus | Taux scolarisation dakar | téewoo scolaarisation dakar | 66.7 % | **fausse** |
| WO-023_aziz.ogg | Limu askanu Senegaal ci atum 2040 | limu askanu senegaal ci atum 2040 | 0.0 % | juste |
| WO-023_kbd.opus | Limu askanu Senegaal ci atum 2040 | lymo askanu senegaal ci atum deux mille quarante | 66.7 % | juste |
| WO-024_aziz.ogg | Ñata voitures nio nek ziguinchor ? | ñaata vootuur ñoo nekk ziguinchor | 80.0 % | **fausse** |
| WO-024_kbd.opus | Ñata voitures nio nek ziguinchor ? | ñaata vootuur ñoo nekk ziguinchor | 80.0 % | **fausse** |
| WO-025_aziz.ogg | Kan mooy njiitu réewum Senegaal ? | kan mooy njiitu réewum senegal | 20.0 % | juste |
| WO-025_kbd.opus | Kan mooy njiitu réewum Senegaal ? | can ma njiitu réewum senegal | 60.0 % | **fausse** |
| WO-026_aziz.ogg | Naka météo bi di mel euleuk ? | naka météo bi di mel ëllëg | 16.7 % | juste |
| WO-026_kbd.opus | Naka météo bi di mel euleuk ? | naka météo di mel ëllëg | 33.3 % | **fausse** |
| WO-027_aziz.ogg | Taux chomage en 2030 | taw chomage en deux mille trente | 100.0 % | **fausse** |
| WO-027_kbd.opus | Taux chomage en 2030 | taux chomage en deux mille trente | 75.0 % | **fausse** |
| WO-028_aziz.ogg | waa man tay dama xiif trop lii mbaa diamm la tamit | waa man tey dama xiif torop lii mbaa jàmm la tamit | 27.3 % | juste |
| WO-028_kbd.opus | waa man tay dama xiif trop lii mbaa diamm la tamit | waaw man tey damaa xif torop di baaj jàmm la tamit | 72.7 % | juste |
| WO-029_aziz.ogg | Kaolack nak ? | kawlak nak | 50.0 % | **fausse** |
| WO-029_kbd.opus | Kaolack nak ? | taolag nak | 50.0 % | **fausse** |
| WO-030_aziz.ogg | Dugub ji nak ? | dugub ji nag | 33.3 % | **fausse** |
| WO-030_kbd.opus | Dugub ji nak ? | dugub ji nag | 33.3 % | **fausse** |
| WO-031_aziz.ogg | niaata nit ñooy lakk sereer fatik | ñaata nit ñooy làkk séeréer fatick? | 66.7 % | juste |
| WO-031_kbd.opus | niaata nit ñooy lakk sereer fatik | ñaata nit ñooy làkk séeréer fatick | 66.7 % | juste |


## Compléments (5 octobre 2026)

Mesures complémentaires, compréhension par règles sauf mention ; détail dans l'historique de
`mesure/scripts/evaluer_transcription.py`.

| Banc d'essai | M-Kiriku | Autres |
|---|---|---|
| 62 notes WhatsApp (KBD, Aziz), règles | **32/62** | Kiriku-Wolof 31, Whosper 21, Wolof-HuBERT-CTC 15, whisper-small-wolof 11, Whisper standard 10, dofbi/wolof-asr 8 |
| 31 notes de KBD (API payante ADIA, accord du locuteur) | **15/31**, WER 36 % | ADIA 13/31, WER 67 %, 0,9 s réseau compris, 49 FCFA |
| WaxalNLP (Google, réaligné par GalsenAI), 27 extraits bien alignés, 6 locuteurs inconnus des modèles | **WER moyen 47 %**, meilleur sur 21/27 | Kiriku-Wolof 56 %, Wolof-HuBERT-CTC 53 %, Whosper 63 %, dofbi 187 % ; 13 extraits écartés (texte encore décalé de l'audio) |
| 5 questions en français (voix de KBD) | **3/5** | Kiriku-Wolof 3/5 ; échecs : « Thiès » mal entendu, « deux mille vingt quatre » en lettres |
| Latence, processeur seul (Mac M3, 4 ou 8 cœurs) | **30 s** par note | inutilisable sans carte graphique |

Whisper standard traduit le wolof en phrases françaises inventées ; dofbi et whisper-small-wolof
partent en boucle sur de vraies voix. Les WER annoncés par les fiches des modèles (12 % à 24 %) ont
été mesurés sur leur propre type d'audio : sur des notes WhatsApp, l'écart est grand.
