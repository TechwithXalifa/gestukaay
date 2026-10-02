// Service worker minimal : garde les pages et fichiers déjà visités pour que
// l'application s'ouvre hors ligne (7.3). Réseau d'abord, cache en secours.
// Les appels à l'API ne sont jamais mis en cache ici : les réponses
// consultées sont gardées par la page elle-même (lib/historique.ts).
const CACHE = "gestukaay-v1";

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));

self.addEventListener("fetch", (e) => {
  const req = e.request;
  const url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== self.location.origin) return;
  e.respondWith(
    fetch(req)
      .then((rep) => {
        if (rep.ok) {
          const copie = rep.clone();
          caches.open(CACHE).then((c) => c.put(req, copie));
        }
        return rep;
      })
      .catch(async () => {
        const enCache = await caches.match(req);
        if (enCache) return enCache;
        // Une adresse de réponse jamais visitée : on sert l'accueil, qui affiche l'état hors ligne
        if (req.mode === "navigate") return (await caches.match("/")) ?? Response.error();
        return Response.error();
      }),
  );
});
