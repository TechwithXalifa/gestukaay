# 0039 — « Où je me situe » v2 : milieu, seuil de pauvreté, groupes de bien-être, carte

**Date** : 2026-10-08 · **Statut** : proposé (KBD), à valider par SAN (contrat 1.6.0, site) · **Issue** : #59 ·
**Complète** : 0004 §2, 0012, 0022

## Contexte

La page comparait la dépense par personne du ménage à deux moyennes (région, Sénégal) et donnait trois
repères. Le socle 2026.10.0 permet plus, sans jamais fabriquer de chiffre :

- consommation moyenne par tête par milieu (`jcvcajc.total`, 2019 et 2022) : **niveau national
  seulement**, ni par région ni par département. Urbain : 697 989 FCFA ; rural : 402 240 FCFA (2022) ;
- seuil de pauvreté officiel (`ahjjzgc.seuil-de-pauvrete`, EHCVM 2018) : 333 441 FCFA par personne et
  par an ;
- part de la population de chaque région dans les cinq groupes de bien-être (`sfxudug`, jusqu'en 2023) ;
- consommation moyenne par tête des 14 régions (`jcvcajc.total`, 2022).

## Décisions (KBD)

1. **Milieu** : nouvelle question **facultative** (« ville », « campagne », « je préfère ne pas
   répondre »). Elle revient sur le « on ne demande pas le milieu » de la 0022 : la comparaison à la seule
   moyenne régionale classait mal les ménages ruraux (Kolda : 387 934 FCFA pour la région, 402 240 pour
   les ménages ruraux du pays, 697 989 pour les ménages urbains). Le milieu n'étant publié qu'au niveau
   national, la comparaison s'ajoute à celle de la région, elle ne la remplace pas.
2. **Seuil de pauvreté** (#59) : même règle de position que les moyennes ; l'explication dit l'année de
   l'enquête (2018).
3. **Groupes de bien-être** : la répartition de la région est montrée, **sans y placer le ménage** :
   les seuils des groupes ne sont pas publiés (0004 §2). Cinq groupes de la même enquête, ou rien.
4. **Site** : graphique « vous, votre région, le Sénégal » avec la fourchette du ménage ; carte des 14
   régions (consommation moyenne) ; « Et si… » (taille, dépenses) et « une autre région » rappellent
   `/v1/situate` : **aucun calcul côté site** ; impression ou PDF par le navigateur. Rien n'est envoyé
   ailleurs ni conservé (EF-40).
5. **Unité du seuil** : déclarée dans `indicateurs.csv` (`unite_affichee` « FCFA par personne et par
   an », domaine Pauvreté), le portail ne la donne pas.

## Conséquences

- Contrat **1.6.0**, additif : `SituateRequest.milieu` ; `SituateResponse.moyenne_milieu`,
  `position_milieu`, `seuil_pauvrete`, `position_seuil`, `repartition_bien_etre`, `moyennes_regions`.
  Exemple `situer_milieu.json`, que le faux moteur sert désormais.
- Écarté pour l'instant : cadre de vie (eau, toilettes, logement, pièces), sexe et situation
  matrimoniale du chef (national, 2018), insécurité alimentaire par département.
