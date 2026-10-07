# Protocole d'annotation (livrable L3) : brouillon v0

> Brouillon à **co-construire et valider avec les physiciens médicaux** de l'Institut Rafaël. Les catégories et l'échelle ci-dessous sont des propositions de départ.

## 1. Objectif
Produire des annotations homogènes et reproductibles des artéfacts de mouvement en 4DCT, utilisables pour entraîner et évaluer un modèle de détection et de localisation.

## 2. Unité d'annotation (à trancher)

| Niveau | Coût | Usage |
|---|---|---|
| Examen : acceptable / limite / inacceptable | Faible | Détection globale, triage |
| Phase : présence d'artéfact oui / non + type | Moyen | Détection par phase |
| Coupe ou plage de coupes (axe cranio-caudal) | Moyen | Localisation 1D, souvent suffisante en pratique |
| Boîte englobante ou masque 3D | Élevé | Localisation fine |

**Proposition** : commencer par examen + phase + plage de coupes. Passer aux boîtes ou masques seulement sur un sous-ensemble si c'est nécessaire.

## 3. Catégories d'artéfacts (proposition)
- `duplication` : structure dédoublée
- `incomplete` : structure tronquée / données manquantes
- `overlap` : chevauchement
- `blurring` : flou de mouvement
- `discontinuity` : discontinuité / décalage entre coupes adjacentes
- `other_motion` : autre artéfact lié au mouvement (à décrire en commentaire)

## 4. Sévérité (proposition)
- 0 : absent
- 1 : visible, sans impact clinique attendu
- 2 : impact possible (vigilance pour la délinéation et les marges)
- 3 : impact important (ré-acquisition envisagée)

Il faut aussi noter si l'artéfact **touche la zone cible ou un organe à risque**.

## 5. Procédure
1. Ouvrir l'examen anonymisé dans l'outil retenu (3D Slicer / MONAI Label ou autre).
2. Parcourir chaque phase en vues **sagittale et coronale** (là où les discontinuités se voient le mieux), puis en axial.
3. Pour chaque artéfact : phase(s), plage de coupes, catégorie, sévérité, région anatomique, commentaire libre.
4. Donner un verdict global sur l'examen.
5. Indiquer le temps passé (utile pour mesurer le gain de l'outil).

## 6. Contrôle qualité des annotations
- Phase pilote : 5 à 10 examens annotés par tous les annotateurs, puis discussion des désaccords et révision du protocole.
- Accord inter-annotateurs mesuré (kappa de Cohen / Fleiss pour les catégories, recouvrement pour les plages de coupes).
- Une fraction des examens est ré-annotée pour mesurer l'accord intra-annotateur.

## 7. Format de sortie (proposition)
Un enregistrement par artéfact (CSV / JSON), sans aucune donnée identifiante :

```
exam_id, phase, slice_start, slice_end, category, severity, region, affects_target, annotator_id, comment
```

## 8. Historique des versions

| Version | Date | Changements | Validé par |
|---|---|---|---|
| v0 | | Brouillon initial | |
