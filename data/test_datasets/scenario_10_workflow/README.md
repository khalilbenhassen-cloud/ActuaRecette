# Scénario 10 : Workflow complet (Maker → Checker → Approver)

## Objectif
Parcourir le workflow métier complet et réglementaire imposé par la gouvernance Pilier 2.

## Contexte
- Portefeuille : Automobile Particuliers
- Contient exactement **2 anomalies critiques** d'oubli de seuil plancher.

## Guide de test pas-à-pas
1. Connectez-vous en tant que **Maker** (Actuaire MOA).
2. Créez une nouvelle campagne de réconciliation dans l'Espace de travail.
3. Importez les fichiers `source_actuariat.xlsx` et `source_dsi.xlsx` de ce dossier.
4. Exécutez l'analyse. Notez les 2 anomalies.
5. Saisissez des commentaires de justification pour chaque anomalie (ex: "Écart de paramétrage de la DSI sur l'arrondi, validé temporairement pour clôture").
6. Soumettez la campagne pour validation.
7. Connectez-vous en tant que **Checker** (Validateur).
8. Ouvrez la campagne, vérifiez la checklist de conformité réglementaire, saisissez votre commentaire de validation et approuvez.
9. Connectez-vous en tant que **Approver** (Responsable MOA).
10. Certifiez la campagne de réconciliation et téléchargez le rapport d'audit PDF.
