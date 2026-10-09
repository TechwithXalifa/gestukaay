import { redirect } from "next/navigation";

/**
 * Entrée du back-office : /admin mène au tableau de bord, qui affiche la connexion tant qu'on n'est pas
 * connecté (une 404 ici laissait croire que le back-office n'existait pas).
 */
export default function Admin() {
  redirect("/admin/tableau");
}
