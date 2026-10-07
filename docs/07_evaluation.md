# Stratégie d'évaluation (livrable L6)

## Principes
- Découpage **par patient** : aucun patient ne se retrouve à la fois en train et en test.
- Jeu de test **figé** avant la modélisation et consulté le moins possible.
- Référence : annotations consensuelles des physiciens. Le désaccord inter-annotateurs donne un plafond réaliste de performance.

## Métriques

### Détection (examen / phase / coupe)
- Sensibilité, spécificité, VPP, VPN.
- AUC-ROC et **AUC-PR** (classes déséquilibrées).
- Choix du seuil orienté usage : on privilégie la **sensibilité** (ne pas rater d'artéfact gênant), avec un taux de fausses alertes acceptable pour le physicien.

### Localisation
- Plages de coupes : recouvrement (IoU 1D), détection à tolérance de ±k coupes.
- Boîtes / masques (si utilisés) : IoU / Dice, FROC (sensibilité selon le nombre de faux positifs par examen).

### Robustesse
- Résultats par sous-groupe : scanner, localisation, amplitude ou irrégularité respiratoire, type et sévérité d'artéfact.
- Sensibilité aux paramètres d'acquisition (épaisseur de coupe, nombre de phases).
- Intervalles de confiance par bootstrap.

### Utilité clinique (si le temps le permet)
- Temps de revue avec et sans l'outil.
- Retours qualitatifs des physiciens (utilisabilité, confiance).

## Baselines de comparaison
- Score de discontinuité inter-coupes non appris.
- Accord inter-annotateurs (référence « humaine »).

## Rapport
Les résultats sont produits dans `reports/`, avec la version du jeu de données, la config et le commit utilisés.
