"use client";

import { useSyncExternalStore } from "react";

function abonner(rappel: () => void) {
  window.addEventListener("online", rappel);
  window.addEventListener("offline", rappel);
  return () => {
    window.removeEventListener("online", rappel);
    window.removeEventListener("offline", rappel);
  };
}

/** Vrai tant que le navigateur se dit connecté ; se met à jour tout seul. */
export const useEnLigne = () =>
  useSyncExternalStore(abonner, () => navigator.onLine, () => true);
