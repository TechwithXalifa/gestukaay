"use client";

import Link from "next/link";
import { useEffect, useId, useState } from "react";
import type { ReponseExacte } from "@contracts/ask_response";
import type { FicheIndicateur } from "@contracts/fiche_indicateur";
import { useLangue } from "@/i18n/langue";
import { fiche } from "@/lib/api";
import { motsUtiles } from "@/lib/glossaire";
import { Chevron, Livre } from "./icones";

/**
 * « Explique-moi simplement » : sous une réponse exacte, ce que mesure l'indicateur (définition publiée par le
 * portail, citée telle quelle, lue à l'ouverture dans la fiche indicateur) et les mots utiles du glossaire en
 * langage simple. Aucun chiffre ni calcul nouveau : seulement des explications.
 */
export function Comprendre({ r }: { r: ReponseExacte }) {
  const { t } = useLangue();
  const id = useId();
  const v = r.resultats.find((x) => x.mise_en_evidence) ?? r.resultats[0];
  const [ouvert, setOuvert] = useState(false);
  const [f, setF] = useState<FicheIndicateur | "erreur" | null>(null);

  useEffect(() => {
    if (!ouvert || f !== null) return;
    fiche(v.indicateur.code).then(setF).catch(() => setF("erreur"));
  }, [ouvert, f, v.indicateur.code]);

  const mots = motsUtiles([v.indicateur.libelle, v.unite, r.explication, v.source.libelle, v.nature ?? ""].join(" "));
  const definition = f && f !== "erreur" ? f.definition : null;

  return (
    <section className="comprendre">
      <button type="button" className="comprendre-bouton" aria-expanded={ouvert} aria-controls={id} onClick={() => setOuvert(!ouvert)}>
        <Livre />{t("comprendre.bouton")}<Chevron taille={16} />
      </button>
      <div id={id} className="comprendre-corps" hidden={!ouvert}>
        <h2 className="comprendre-titre">{t("comprendre.mesure", { indicateur: v.indicateur.libelle })}</h2>
        {f === null ? (
          <p className="note" role="status">{t("comprendre.chargement")}</p>
        ) : definition ? (
          <>
            <blockquote className="comprendre-definition">{definition}</blockquote>
            <p className="note">{t("comprendre.cite", { producteur: v.source.producteur })}</p>
          </>
        ) : (
          <p>{t("fiche.sansDefinition")}</p>
        )}
        {mots.length > 0 && (
          <>
            <h3 className="comprendre-sous-titre">{t("comprendre.mots")}</h3>
            <dl className="comprendre-mots">
              {mots.map((m) => (
                <div key={m.id}>
                  <dt><Link href={`/glossaire#${m.id}`}>{m.mot}</Link></dt>
                  <dd>{m.definition}</dd>
                </div>
              ))}
            </dl>
          </>
        )}
        <p className="comprendre-liens">
          <Link href="/glossaire" className="lien">{t("comprendre.glossaire")}</Link>
          <Link href={`/indicateurs/${encodeURIComponent(v.indicateur.code)}`} className="lien">{t("comprendre.fiche")}</Link>
        </p>
      </div>
    </section>
  );
}
