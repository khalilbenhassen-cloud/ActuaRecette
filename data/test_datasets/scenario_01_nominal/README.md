# Scénario 1 : Cas nominal (Sans écart)

## Objectif
Valider que la plateforme de réconciliation déclare une conformité parfaite lorsque les calculs de la DSI correspondent en tout point à la référence actuarielle.

## Contexte
- Périmètre : Automobile Particuliers
- Volume : 100 assurés
- Données saines sans écarts de tarification ni erreurs d'ingestion.

## Comportement attendu dans ActuaRecette
1. L'import des deux fichiers se fait sans erreur.
2. La réconciliation calcule un taux de conformité de **100 %**.
3. Aucun écart n'est mis en évidence dans le tableau d'analyse.
4. La campagne obtient le statut initial "CONFORME" et peut être certifiée immédiatement sans réserve.
