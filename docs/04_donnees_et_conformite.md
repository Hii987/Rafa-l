# Données et conformité

## Règles non négociables

1. **Aucune donnée patient dans Git**, même anonymisée, même un seul fichier pour un test. Le `.gitignore` bloque les formats d'imagerie courants, mais c'est un filet de sécurité, pas une garantie.
2. **Anonymisation au plus tôt** : les données brutes ne quittent pas l'environnement autorisé par l'Institut.
3. **Aucun envoi vers un service externe** (API cloud, LLM, outil en ligne) de données patient ou de captures d'écran contenant des données identifiantes.
4. **Traçabilité** : tenir un registre de qui accède à quoi, quand, dans quel but (à définir avec l'Institut / le DPO).

## Cadre réglementaire (à préciser avec l'Institut)

- RGPD : les données de santé sont des données sensibles (art. 9).
- Cadre de réutilisation des données en France (CNIL, méthodologies de référence, information des patients).
- Hébergement : si des données de santé identifiantes sont hébergées hors de l'établissement, l'hébergeur doit être certifié **HDS**.
- Statut de l'outil : prototype de recherche, sans usage clinique décisionnel autonome.

## Pipeline de données prévu (livrable L2)

```
PACS ──export DICOM──▶ data/raw/          (accès restreint, jamais copié ailleurs)
                         │
                         ▼  anonymisation (profil DICOM PS3.15 annexe E + revue des tags privés)
                       data/interim/      (DICOM anonymisés + table de correspondance stockée À PART)
                         │
                         ▼  contrôle qualité, tri des phases, conversion (NIfTI / tableaux)
                       data/processed/    (volumes 4D + métadonnées + splits par patient)
                         │
                         ▼
                       data/annotations/  (labels, versionnés hors Git)
```

### Points d'attention pour l'anonymisation
- Tags d'identité : nom, ID, date de naissance, numéros d'accession, établissements, opérateurs.
- **UIDs** : à remapper de façon cohérente pour conserver le lien entre séries et phases.
- **Dates** : décalage cohérent par patient plutôt que suppression, pour garder les intervalles.
- **Tags privés constructeur** : ils peuvent contenir des infos identifiantes, mais aussi le numéro de phase ou le signal respiratoire. Revue au cas par cas.
- Informations incrustées dans les pixels (rare en CT, à vérifier sur les captures secondaires).
- La table de correspondance pseudonyme ↔ patient reste à l'Institut.

## Description du jeu de données (à remplir, livrable L4)

| Champ | Valeur |
|---|---|
| Nombre de patients / examens | |
| Période | |
| Scanner(s) / système respiratoire | |
| Nombre de phases | |
| Résolution / épaisseur de coupe | |
| Localisations | |
| Répartition des artéfacts | |
| Splits (train / val / test) | par patient |
| Version | v0 |
