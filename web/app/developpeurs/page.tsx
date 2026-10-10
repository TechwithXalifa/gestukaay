"use client";

import { PageTexte, Section } from "@/components/PageTexte";
import { Externe } from "@/components/icones";
import { useLangue } from "@/i18n/langue";
import { API_URL } from "@/lib/api";

/** Routes publiques documentées (les mêmes que le site) : méthode, chemin, ce qu'elles renvoient (clé i18n). */
const ROUTES = [
  ["GET", "/v1/indicators?q=pauvreté&domaine=&niveau=region", "dev.r.catalogue"],
  ["GET", "/v1/indicators/{code}", "dev.r.fiche"],
  ["GET", "/v1/series?indicateur={code}&zones=SN,SN-DK&debut=2011&fin=2022", "dev.r.series"],
  ["GET", "/v1/series.csv?indicateur={code}&zones=SN", "dev.r.csv"],
  ["POST", "/v1/ask", "dev.r.ask"],
  ["GET", "/v1/answers/{id}", "dev.r.answers"],
  ["GET", "/v1/answers/{id}/export.pdf", "dev.r.exports"],
] as const;

/**
 * API publique (développeurs, médias, administrations) : les mêmes données que le site, en JSON, gratuites et
 * sans compte. Les clés (back-office, /admin/cles) ne servent qu'à des limites plus larges.
 */
export default function Developpeurs() {
  const { t } = useLangue();
  const exempleSeries = `curl "${API_URL}/v1/series?indicateur=jcvcajc.taux-de-pauvrete&zones=SN,SN-KD"`;
  const exempleQuestion = [
    `const r = await fetch("${API_URL}/v1/ask", {`,
    `  method: "POST",`,
    `  headers: { "Content-Type": "application/json" },`,
    `  body: JSON.stringify({ question: "Quel est le taux de pauvreté à Kolda ?" }),`,
    `});`,
    `const { reponse } = await r.json();`,
    `// reponse.issue : "exacte", "approchee" ou "aucune"`,
    `// reponse.resultats[0].valeur_affichee, .unite, .source.libelle ; reponse.citation`,
  ].join("\n");
  const exempleCle = `curl -H "X-Gestukaay-Cle: gk_…" "${API_URL}/v1/indicators?q=chômage"`;

  return (
    <PageTexte titre="dev.titre" actif="methode">
      <p className="explication">{t("dev.intro")}</p>

      <section>
        <h2 className="sous-titre">{t("dev.adresse")}</h2>
        <p><code className="dev-code-ligne">{API_URL}</code></p>
        <p>
          <a href={`${API_URL}/docs`} className="lien" target="_blank" rel="noreferrer">
            {t("dev.documentation")} <Externe taille={16} />
          </a>
        </p>
      </section>

      <section>
        <h2 className="sous-titre">{t("dev.routes")}</h2>
        <div className="tableau-defile" role="region" aria-label={t("dev.routes")} tabIndex={0}>
          <table className="tableau dev-routes">
            <thead>
              <tr><th scope="col">{t("dev.methode")}</th><th scope="col">{t("dev.chemin")}</th><th scope="col">{t("dev.renvoie")}</th></tr>
            </thead>
            <tbody>
              {ROUTES.map(([methode, chemin, cle]) => (
                <tr key={chemin}>
                  <td><code>{methode}</code></td>
                  <th scope="row"><code>{chemin}</code></th>
                  <td>{t(cle)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="note">{t("dev.zones")}</p>
      </section>

      <section>
        <h2 className="sous-titre">{t("dev.exemples")}</h2>
        <p>{t("dev.exempleSeries")}</p>
        <pre className="dev-code" tabIndex={0}><code>{exempleSeries}</code></pre>
        <p>{t("dev.exempleQuestion")}</p>
        <pre className="dev-code" tabIndex={0}><code>{exempleQuestion}</code></pre>
      </section>

      <section>
        <h2 className="sous-titre">{t("dev.limites")}</h2>
        <p>{t("dev.limitesTexte")}</p>
        <pre className="dev-code" tabIndex={0}><code>{exempleCle}</code></pre>
        <p>{t("dev.cles")}</p>
      </section>

      <Section titre="dev.regles" textes={["dev.regle1", "dev.regle2", "dev.regle3", "dev.erreurs"]} />
    </PageTexte>
  );
}
