"use client";

import { useEffect } from "react";

/** Active le service worker (public/sw.js) en production : application lisible hors ligne. */
export function EnregistrerSW() {
  useEffect(() => {
    if (process.env.NODE_ENV === "production" && "serviceWorker" in navigator) {
      navigator.serviceWorker.register("/sw.js").catch(() => {});
    }
  }, []);
  return null;
}
