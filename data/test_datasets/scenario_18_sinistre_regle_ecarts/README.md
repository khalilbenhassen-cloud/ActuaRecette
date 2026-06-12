# Scénario 18 : Domaine Sinistre - Mécanisme A (Règle dynamique - Écarts majeurs)

## Objectif
Valider la détection d'anomalies de somme dynamique (Mécanisme A) lorsqu'il y a des déviations entre la somme des composants et le total déclaré par la DSI.

## Contexte
- Portefeuille : Automobile Particuliers (`LOB_AUTO_PART`)
- Domaine : Sinistre
- Contient **5 anomalies de somme critiques** (déviations supérieures au seuil).
- Règle dynamique à configurer : `SINISTRE_DSI == PAIEMENTS_DSI + PSAP_DSI` (Tolérance = 0.00).

## Comportement attendu dans ActuaRecette
- Taux de conformité = **95.0 %**.
- 5 anomalies critiques identifiées pour les sinistres `SIN-00005`, `SIN-00018`, `SIN-00039`, `SIN-00057`, et `SIN-00074`.
- Statut final : **NON CONFORME**.
