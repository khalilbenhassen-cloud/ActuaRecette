# Scénario 5 : Doublons (Clé non unique)

## Objectif
Tester le comportement du pivot de réconciliation face à des doublons dans le fichier d'ingestion.

## Contexte
Deux assurés (`ID_CLIENT` identiques) sont enregistrés deux fois dans les fichiers sources.

## Comportement attendu dans ActuaRecette
- Lors de l'ingestion ou de la jointure, le système détecte des lignes dupliquées pour le même identifiant.
- Une alerte technique est levée pour indiquer que la clé d'assuré n'est pas unique.
- Cela permet de tester la résilience et les messages d'avertissement de l'application sur la cohérence des bases.
