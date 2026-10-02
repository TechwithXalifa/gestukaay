# 0009 — Validation du wolof par un seul locuteur natif (V1.0)

**Date** : 2026-10-02 · **Statut** : accepté (KBD) · **Issue** : #26 · **Écart au cahier** : 7.4

## Contexte

Le cahier (7.4) exige que toutes les chaînes wolof (noms d'indicateurs et de zones, interface, messages
WhatsApp, gabarits audio) soient validées par **au moins deux locuteurs natifs, dont un linguiste**
(partenariat universitaire prévu). À cinq jours du hackathon, aucun relecteur extérieur n'est disponible.

## Décision

1. **V1.0 : validation par un locuteur natif, KBD**, qui écrit aussi le wolof. `statut_wo = valide`
   signifie « relu par KBD » ; Gëstukaay ne prétend jamais à une validation par un linguiste.
2. **Limiter le biais de l'auteur** : relecture à voix haute, à un autre moment que l'écriture ; chaque
   phrase confrontée à l'usage réel (écriture `usage` du jeu de test, tournures WhatsApp).
3. **Voix pour l'évaluation de la transcription (#27)** : ce n'est pas une relecture. On enregistre des
   voix variées (proches qui lisent une dizaine de phrases) ; à défaut, la voix de KBD seule, et le
   rapport de mesure le dit.
4. **V1.1** : validation à deux locuteurs dont un linguiste, et choix documenté de l'orthographe de
   référence, comme prévu par le cahier (7.4, 13.2).

## Conséquences

- Écart au cahier 7.4 à présenter tel quel au jury : wolof relu par un locuteur natif en V1.0,
  partenariat linguistique en V1.1.
- Points à trancher par KBD en tant que relecteur : orthographe de référence de la démo (officielle
  « ñaata » ou usage « niaata ») et le mot *ñakk* (chômage, pauvreté, vaccin) pour le lexique (#23).
