"use client";

import { type Actif, Entete, PiedDePage } from "@/components/Entete";
import { useLangue } from "@/i18n/langue";
import type { Cle } from "@/i18n/fr";

/** Pages d'information du pied de page : même cadre, textes dans i18n. */
export function PageTexte({ titre, actif = null, children }: { titre: Cle; actif?: Actif; children: React.ReactNode }) {
  const { t } = useLangue();
  return (
    <div className="site">
      <Entete actif={actif} />
      <main id="contenu" tabIndex={-1} className="page-texte">
        <h1 className="titre-situer">{t(titre)}</h1>
        {children}
      </main>
      <PiedDePage />
    </div>
  );
}

/** Une section : titre de niveau 2 et paragraphes. */
export function Section({ titre, textes }: { titre: Cle; textes: Cle[] }) {
  const { t } = useLangue();
  return (
    <section>
      <h2 className="sous-titre">{t(titre)}</h2>
      {textes.map((c) => <p key={c}>{t(c)}</p>)}
    </section>
  );
}
