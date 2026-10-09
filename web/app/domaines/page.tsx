import { redirect } from "next/navigation";

/**
 * L'ancienne page Domaines est fusionnée dans le catalogue : les 32 domaines y sont des filtres rapides,
 * avec leur nombre d'indicateurs. L'adresse reste valable et mène au catalogue (liens déjà partagés).
 */
export default function Domaines() {
  redirect("/indicateurs");
}
