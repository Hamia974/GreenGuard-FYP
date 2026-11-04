import { redirect } from "next/navigation";

/** Disease Check is now part of the Leaf test. */
export default function DiseaseCheckPage() {
  redirect("/quick-scan");
}
