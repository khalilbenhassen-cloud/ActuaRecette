# formula_parser.py — Parseur AST sécurisé d'expressions arithmétiques
# Phase 2c — Moteur de calcul dynamique Solvabilité II
"""
Parseur et évaluateur d'expressions mathématiques simples fondé sur l'AST Python.
Évite l'utilisation dangereuse d'eval() en limitant l'évaluation aux opérateurs
arithmétiques de base et aux variables autorisées (colonnes mappées).

Optimisé pour évaluer les formules rapidement sur de grandes volumétries.
"""

import ast
import operator
from typing import Any
import pandas as pd

class SafeFormulaParser:
    """Parseur et évaluateur arithmétique sécurisé."""

    # Opérateurs autorisés
    _operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.USub: operator.neg,
        ast.UAdd: lambda x: x,
        ast.Lt: operator.lt,
        ast.Gt: operator.gt,
        ast.Eq: operator.eq,
        ast.LtE: operator.le,
        ast.GtE: operator.ge
    }

    def __init__(self, expression_str: str):
        """
        Initialise et pré-compile la formule pour optimiser l'évaluation ultérieure.
        
        Args:
            expression_str (str): L'expression arithmétique sous forme de chaîne de caractères.
        """
        self.expression = expression_str.strip() if expression_str else "0.0"
        self._tree = None
        self._compile()

    def _compile(self):
        """Compile l'expression en un arbre AST et valide sa structure de sécurité."""
        try:
            # Parse en mode 'eval' pour n'accepter qu'une seule expression
            self._tree = ast.parse(self.expression, mode='eval')
            # Valider la sécurité de l'arbre
            self._validate_node(self._tree.body)
        except Exception as e:
            raise ValueError(
                f"La formule '{self.expression}' est invalide ou contient "
                f"des éléments non autorisés : {e}"
            )

    def _validate_node(self, node):
        """Vérifie récursivement qu'aucun noeud interdit n'est présent dans l'AST."""
        # Autoriser uniquement les nombres
        if hasattr(ast, 'Num') and isinstance(node, ast.Num):  # Python < 3.8
            return
        elif isinstance(node, ast.Constant):  # Python >= 3.8
            if isinstance(node.value, (int, float, bool, str)):
                return
            raise ValueError(f"Type de constante non autorisé : {type(node.value).__name__}")
        
        # Autoriser les identifiants de variables (noms de colonnes)
        elif isinstance(node, ast.Name):
            return
        
        # Autoriser les opérations binaires (+, -, *, /)
        elif isinstance(node, ast.BinOp):
            if type(node.op) not in self._operators:
                raise ValueError(f"Opérateur binaire non autorisé : {type(node.op).__name__}")
            self._validate_node(node.left)
            self._validate_node(node.right)
            
        # Autoriser les opérateurs unaires (+, -)
        elif isinstance(node, ast.UnaryOp):
            if type(node.op) not in self._operators:
                raise ValueError(f"Opérateur unaire non autorisé : {type(node.op).__name__}")
            self._validate_node(node.operand)

        # Autoriser les comparaisons simples (ex: age_conducteur < 25)
        elif isinstance(node, ast.Compare):
            self._validate_node(node.left)
            for op in node.ops:
                if type(op) not in self._operators:
                    raise ValueError(f"Opérateur de comparaison non autorisé : {type(op).__name__}")
            for comp in node.comparators:
                self._validate_node(comp)
            
        # Refuser tout le reste (appels de fonctions, logique conditionnelle, etc.)
        else:
            raise ValueError(f"Structure syntaxique non autorisée : {type(node).__name__}")

    def evaluate(self, row_variables: dict) -> Any:
        """
        Évalue la formule pré-compilée en injectant les valeurs de variables fournies.

        Args:
            row_variables (dict): Dictionnaire mapping {nom_variable: valeur} pour la ligne courante.

        Returns:
            Any: Le résultat de l'évaluation de l'expression.
        """
        if self._tree is None:
            return 0.0
        try:
            val = self._eval_node(self._tree.body, row_variables)
            # Conserver le booléen pour les conditions logiques, sinon caster en float
            if isinstance(val, bool):
                return val
            return float(val)
        except ZeroDivisionError:
            return float('inf')
        except Exception as e:
            raise ValueError(f"Erreur d'évaluation pour la formule '{self.expression}' : {e}")

    def _eval_node(self, node, variables: dict) -> Any:
        """Évalue un noeud d'arbre AST de manière récursive."""
        if hasattr(ast, 'Num') and isinstance(node, ast.Num):
            return float(node.n)
        elif isinstance(node, ast.Constant):
            if isinstance(node.value, str):
                return node.value
            return float(node.value) if not isinstance(node.value, bool) else node.value
        
        elif isinstance(node, ast.Name):
            var_name = node.id
            if var_name in variables:
                val = variables[var_name]
                # Convertir proprement en float ou conserver chaîne si c'est une chaîne
                if pd.isna(val) or val == "" or val is None:
                    return 0.0
                try:
                    # Tenter de convertir en float
                    return float(str(val).replace(",", ".").strip())
                except ValueError:
                    # Conserver sous forme de chaîne pour les comparaisons textuelles (ex: type_risque)
                    return str(val).strip()
            raise ValueError(f"La variable requise '{var_name}' n'est pas présente dans les données.")
            
        elif isinstance(node, ast.BinOp):
            op_fn = self._operators[type(node.op)]
            left_val = self._eval_node(node.left, variables)
            right_val = self._eval_node(node.right, variables)
            return op_fn(left_val, right_val)
            
        elif isinstance(node, ast.UnaryOp):
            op_fn = self._operators[type(node.op)]
            operand_val = self._eval_node(node.operand, variables)
            return op_fn(operand_val)

        elif isinstance(node, ast.Compare):
            left_val = self._eval_node(node.left, variables)
            op_type = type(node.ops[0])
            op_fn = self._operators[op_type]
            right_val = self._eval_node(node.comparators[0], variables)
            # Si l'un est chaîne et l'autre non, tenter de comparer en chaîne
            if isinstance(left_val, str) or isinstance(right_val, str):
                return bool(op_fn(str(left_val), str(right_val)))
            return bool(op_fn(left_val, right_val))
            
        raise ValueError(f"Noeud non pris en charge lors de l'évaluation : {type(node).__name__}")
