# Scénario 7C : Volumétrie - 50000 lignes

## Objectif
Tester la robustesse technique de l'application, l'impact sur la mémoire du serveur, et la fluidité d'affichage graphique Plotly sur un grand nombre d'assurés.

## Contexte
- Volume : 50000 lignes
- Proportion d'anomalies : ~2%

## Comportement attendu dans ActuaRecette
- La jointure DuckDB s'exécute en moins de 2 secondes.
- La pagination des tables d'anomalies de l'application s'affiche de manière fluide.
- Les graphiques Plotly affichent correctement les densités et la distribution de dérive.
