// Relie le texte surligné et les fiches de signalement.
//
// Tout le câblage existe déjà côté serveur : surligner() pose sur chaque <mark>
// un data-findings="0,3" — les rangs des signalements qui couvrent ce segment —
// et le template donne à chaque fiche un id="signalement-3". Ce fichier ne fait
// que suivre ces rangs dans les deux sens.

const marques = document.querySelectorAll("mark.signalement");
const fiches = document.querySelectorAll(".fiche");

function rangs(marque) {
  return marque.dataset.findings.split(",").map(Number);
}

function eclairer(actifs) {
  fiches.forEach((fiche, rang) => fiche.classList.toggle("active", actifs.includes(rang)));
  marques.forEach((marque) =>
    marque.classList.toggle("active", rangs(marque).some((rang) => actifs.includes(rang)))
  );
}

// Du texte vers la fiche.
marques.forEach((marque) => {
  marque.addEventListener("click", () => {
    const actifs = rangs(marque);
    eclairer(actifs);
    fiches[actifs[0]].scrollIntoView({ behavior: "smooth", block: "center" });
  });
});

// De la fiche vers le texte. Un signalement peut être coupé en plusieurs <mark>
// — le découpage se fait aux frontières de tous les signalements — donc on vise
// le premier segment rencontré.
fiches.forEach((fiche, rang) => {
  fiche.addEventListener("click", () => {
    eclairer([rang]);
    const premier = [...marques].find((marque) => rangs(marque).includes(rang));
    if (premier) premier.scrollIntoView({ behavior: "smooth", block: "center" });
  });
});
