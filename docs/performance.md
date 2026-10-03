# Performance du site (cahier 7.6, « Bas débit et appareils modestes »)

Mesure du 03/10/2026, build de production, faux moteur. Lighthouse 12, profil du cahier :
**3G rapide simulée** (150 ms de latence, 1,6 Mb/s), **processeur ralenti ×4**, écran 360 × 640.
Valeurs médianes sur 3 essais pour l'accueil.

| Budget 7.6 | Cible | Accueil | Réponse | Où je me situe |
|---|---|---|---|---|
| Affichage du contenu principal (LCP) | ≤ 2,5 s | **2,2 s** | **2,1 s** | **1,9 s** |
| Décalage de mise en page (CLS) | ≤ 0,1 (Web Vitals) | 0,001 | 0,003 | 0,03 |
| Temps de blocage (TBT, indice de l'INP) | INP ≤ 200 ms | 220 à 270 ms | 440 ms | 270 ms |
| JavaScript initial | ≤ 150 Ko | 118 Ko | 122 Ko | 115 Ko |
| Poids total | ≤ 400 Ko (accueil) | 186 Ko | 213 Ko | 182 Ko |
| Accessibilité (Lighthouse) | | 100 | 100 | 100 |

## Ce qui a été corrigé pour y arriver

- **Page réponse rendue côté serveur** (`web/app/r/[id]/page.tsx`) : le chiffre est dans le HTML
  dès le premier octet. Avant, le navigateur chargeait le JavaScript, puis appelait l'API : LCP
  3,5 s et CLS 0,133 (le pied de page sautait quand la réponse arrivait). Dans Docker, le serveur
  web joint l'API par `API_INTERNE` (réseau interne) ; si l'API ne répond pas en 1,5 s, la page
  reprend le chargement côté navigateur, comme avant.
- **Favicon** (`web/app/icon.svg`) : sa 404 apparaissait comme une erreur dans la console.
- Polices auto-hébergées et budget JavaScript vérifié en CI (#78).

## Ce qui reste à surveiller

- **TBT de la page réponse (440 ms)** : c'est le temps d'hydratation de React sur un processeur
  ralenti ×4. L'INP réel (temps de réponse à un clic) se mesure sur le terrain : à vérifier en
  préproduction sur l'appareil de référence (Android 10, 2 Go de RAM).
- Ces mesures sont faites en local (latence serveur quasi nulle). À refaire en préproduction.

## Refaire la mesure

```bash
cd web && npm run build && npm start          # et l'API sur le port 8000
npx -y lighthouse@12 http://localhost:3000/ --only-categories=performance \
  --form-factor=mobile --screenEmulation.width=360 --screenEmulation.height=640 \
  --throttling-method=simulate --throttling.rttMs=150 --throttling.throughputKbps=1638.4 \
  --throttling.cpuSlowdownMultiplier=4 --view
```

Sous Windows, si le Chromium de Playwright est bloqué, passer `CHROME_PATH` vers Chrome :
Lighthouse le lance avec un profil temporaire vide.
