# Scénario 13 : Domaine Contrat - Cas nominal (Sans écart)

## Objectif
Valider le bon fonctionnement de la réconciliation et du data profiling sur le domaine **Contrat** sans écart de calcul.

## Contexte
- Portefeuille : Automobile Particuliers (`LOB_AUTO_PART`)
- Domaine : Contrat
- Seuil de tolérance du domaine : **1.0 %**
- Noms de colonnes : `ID_CONTRAT` (clé), `CONTRAT_REF` (référence), `CONTRAT_DSI` (production).

## Comportement attendu dans ActuaRecette
1. Sélectionner le LOB **"Automobile Particuliers"** et le domaine **"Contrat"** à la création.
2. Mappez la clé sur : `ID_CONTRAT`
3. Mappez le Contrat Référence sur : `CONTRAT_REF`
4. Mappez le Contrat Production sur : `CONTRAT_DSI`
5. La réconciliation produit un taux de conformité de **100%**.
