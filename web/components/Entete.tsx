"use client";

import Link from "next/link";
import { useState } from "react";
import { Baobab } from "./icones";

/** En-tête commun : logo, navigation, bascule FR/WO toujours visible (9.7). */
export function Entete() {
  const [langue, setLangue] = useState<"fr" | "wo">("fr");
  return (
    <header className="entete">
      <div className="entete-int">
        <Link href="/" className="logo">
          <Baobab /> <span>Gëstukaay</span>
        </Link>
        <nav aria-label="Navigation principale" className="nav">
          <Link href="/" aria-current="page">Poser une question</Link>
        </nav>
        <div role="group" aria-label="Langue de l'interface" className="bascule">
          {(["fr", "wo"] as const).map((l) => (
            <button key={l} type="button" aria-pressed={langue === l} onClick={() => setLangue(l)}>
              {l.toUpperCase()}
            </button>
          ))}
        </div>
      </div>
    </header>
  );
}

export function PiedDePage({ adresse }: { adresse?: string }) {
  return (
    <footer className="pied">
      <div className="pied-int">
        <p>{adresse ? `${adresse.replace(/^https?:\/\//, "")} · adresse stable et partageable` : "Gëstukaay"}</p>
        <nav aria-label="Pied de page">
          <a href="#">Méthode et transparence</a>
          <a href="#">À propos</a>
          <a href="#">Confidentialité</a>
        </nav>
      </div>
    </footer>
  );
}
