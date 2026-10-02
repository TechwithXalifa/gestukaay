"use client";

import { Cadenas, MicroBarre } from "./icones";

/** État « Micro refusé » (7.3, maquette M-MicroRefuse) : 2 étapes + la saisie texte reste possible. */
export function MicroRefuse({ onReessayer }: { onReessayer: () => void }) {
  const site = typeof window !== "undefined" ? window.location.host : "ce site";
  return (
    <section className="carte micro-refuse" role="alert">
      <span className="pastille-icone"><MicroBarre taille={24} /></span>
      <h1 className="titre-etat">Le micro est bloqué pour {site}</h1>
      <p className="explication">Pour parler à Gëstukaay, autorisez le micro en deux étapes :</p>
      <ol className="etapes-numerotees">
        <li><span aria-hidden="true">1</span><span>Touchez le <strong>cadenas</strong> à gauche de l'adresse, en haut de l'écran.</span></li>
        <li><span aria-hidden="true">2</span><span>Ouvrez <strong>Autorisations</strong>, puis réglez <strong>Micro</strong> sur « Autoriser ».</span></li>
      </ol>
      <button type="button" className="primaire" onClick={onReessayer}>J'ai autorisé, réessayer</button>
      <p className="note"><Cadenas taille={16} />Vous pouvez aussi écrire votre question dans le champ ci-dessus. Gëstukaay n'écoute que lorsque vous appuyez sur le micro.</p>
    </section>
  );
}
