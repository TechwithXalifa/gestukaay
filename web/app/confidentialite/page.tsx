"use client";

import { PageTexte, Section } from "@/components/PageTexte";
import { useLangue } from "@/i18n/langue";

/** Ce que le service garde vraiment : à tenir à jour avec backend/stockage.py et la décision 0004. */
export default function Confidentialite() {
  const { t } = useLangue();
  return (
    <PageTexte titre="confid.titre">
      <p className="explication">{t("confid.intro")}</p>
      <Section titre="confid.questions" textes={["confid.questions.texte", "confid.ia", "confid.whatsapp"]} />
      <Section titre="confid.voix" textes={["confid.voix.texte", "confid.voix.repli"]} />
      <Section titre="confid.situer" textes={["confid.situer.texte"]} />
      <Section titre="confid.retours" textes={["confid.retours.texte"]} />
      <Section titre="confid.appareil" textes={["confid.appareil.texte"]} />
    </PageTexte>
  );
}
