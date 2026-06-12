# Scénario 11 : Gouvernance & Registre d'Audit

## Objectif
Valider la traçabilité Solvabilité II (Pilier 2) à chaque action utilisateur.

## Contexte
Ce jeu de données comporte 1 anomalie majeure de tarification.

## Comportement attendu dans ActuaRecette
1. Créez et importez cette campagne.
2. À chaque étape franchie (Brouillon -> Analyse -> Soumission), ouvrez la page **Registre d'Audit**.
3. Vérifiez qu'une ligne d'audit est générée, contenant :
   - L'horodatage précis.
   - L'identifiant SSO de l'utilisateur actif.
   - L'action effectuée.
   - La signature cryptographique (SHA-256) garantissant l'intégrité de la trace.
4. Les résultats agrégés doivent remonter dans la page **Gouvernance ACPR**.
