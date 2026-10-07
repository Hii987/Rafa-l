# Cadrage

## Problématique

> Peut-on détecter et localiser automatiquement, de façon fiable, les artéfacts de mouvement dans une acquisition 4DCT, afin d'accélérer et de fiabiliser le contrôle qualité fait par le physicien médical ?

## Utilisateur cible et usage

- **Utilisateur** : physicien médical (et, secondairement, radiothérapeute / manipulateur).
- **Moment d'usage** : juste après l'acquisition 4DCT, avant la délinéation et la planification.
- **Décision soutenue** : accepter l'acquisition, demander une acquisition complémentaire, ou intégrer l'incertitude (par exemple dans les marges ou l'ITV).
- **Principe** : l'outil signale et localise. La décision reste au physicien.

## Périmètre

### Dans le périmètre
- Images 4DCT (phases respiratoires reconstruites, éventuellement MIP / AveIP) exportées du PACS en DICOM.
- Artéfacts liés au mouvement : respiration irrégulière, mouvement du patient, problèmes de tri des phases.
- Détection au niveau acquisition / phase, et localisation (coupes, régions).

### Hors périmètre (à confirmer)
- Correction ou réduction des artéfacts (on détecte, on ne corrige pas).
- Artéfacts non liés au mouvement : métal, beam hardening, bruit…
- Marquage CE / dispositif médical (un prototype de recherche n'est pas un DM certifié).

## Hypothèses de travail (à valider)

- H1 : l'Institut peut fournir un volume suffisant d'examens 4DCT exportables et anonymisables.
- H2 : des physiciens sont disponibles pour annoter ou valider un sous-ensemble des cas.
- H3 : la plupart des artéfacts visibles sont des discontinuités entre coupes adjacentes, repérables dans les vues sagittale et coronale.
- H4 : le signal respiratoire (courbe du dispositif de gating) est peut-être disponible. C'est une source d'information précieuse si c'est le cas.

## Questions ouvertes pour l'Institut Rafaël

### Données
- [ ] Combien d'examens 4DCT sont disponibles ? Sur quelle période ?
- [ ] Quel scanner (constructeur, modèle) et quel système de suivi respiratoire (RPM, Anzai, ceinture, surface…) ?
- [ ] Quel mode d'acquisition : hélicoïdal ou axial / ciné ? Tri des phases en phase ou en amplitude ?
- [ ] Combien de phases par examen (en général 10) ? Les MIP / AveIP sont-ils exportés ?
- [ ] Le signal respiratoire brut est-il exportable ?
- [ ] Existe-t-il des examens déjà jugés « mauvais » ou ré-acquis ? Peut-on en retrouver la trace (comptes rendus, refaits) ?
- [ ] Quelles localisations tumorales sont représentées : poumon, foie, pancréas… ?

### Clinique / annotation
- [ ] Quelle typologie d'artéfacts les physiciens utilisent-ils au quotidien ?
- [ ] À partir de quand un artéfact devient-il « gênant » ? Existe-t-il une grille de cotation ?
- [ ] Combien de temps les physiciens peuvent-ils consacrer à l'annotation ? Combien d'annotateurs ?
- [ ] Quelle granularité attendre : examen OK / KO, phase, coupe, région ?

### Technique / intégration
- [ ] Quel PACS et quel TPS sont utilisés ? Les nœuds DICOM sont-ils accessibles (C-STORE / C-FIND) ?
- [ ] Où le calcul peut-il tourner (serveur interne, GPU disponible) ?
- [ ] Quel format de restitution est souhaité : DICOM SEG, DICOM SR, Secondary Capture, rapport PDF ?

### Réglementaire / organisation
- [ ] Quel cadre réglementaire pour la réutilisation des données (recherche n'impliquant pas la personne humaine, MR-004, entrepôt…) ? Y a-t-il un DPO ?
- [ ] Où sont stockées les données côté étudiants (poste de l'Institut, hébergement HDS, VPN…) ?
- [ ] Quel rythme de points avec le chef de projet ?

## Risques identifiés

| Risque | Impact | Mitigation |
|---|---|---|
| Peu de données ou accès tardif | Bloquant | Commencer avec des données publiques 4DCT (voir état de l'art) et générer des artéfacts synthétiques |
| Peu d'exemples d'artéfacts (classes déséquilibrées) | Fort | Simulation d'artéfacts, approches non supervisées / détection d'anomalies, métriques adaptées |
| Annotation coûteuse et subjective | Fort | Protocole clair, annotation à granularité grossière d'abord, mesure de l'accord inter-annotateurs |
| Contraintes RGPD / sécurité | Fort | Anonymisation dès l'import, aucun export hors périmètre autorisé |
| Intégration PACS difficile | Moyen | Prototype autonome d'abord (Orthanc local), intégration PACS ensuite |
| Généralisation à d'autres scanners | Moyen | Évaluation par sous-groupes, documenter les limites |
