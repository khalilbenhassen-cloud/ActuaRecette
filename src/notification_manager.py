"""
Module src/notification_manager.py
==================================
Gère la persistance et le cycle de vie des notifications système stockées dans SQLite.
Assure la propagation sur la base principale et la base redondante.
"""

import os
import uuid
import logging
from typing import List, Dict, Any, Optional
from src.db_adapter import sqlite_connection

logger = logging.getLogger("actuarecette.notification_manager")

DBS = ["data/actuarecette.db", "data/actuarecette_v2.db"]

def create_notification(
    id_portefeuille: Optional[str],
    destinataire_role: Optional[str],
    destinataire_sso: Optional[str],
    titre: str,
    message: str,
    type: str = "INFO"
) -> str:
    """
    Insère une notification système dans les deux bases de données répliquées.
    Retourne l'ID unique de la notification générée.
    """
    notif_id = f"NOTIF-{uuid.uuid4().hex[:8].upper()}"
    
    for db_path in DBS:
        try:
            if not os.path.exists(os.path.dirname(db_path)):
                os.makedirs(os.path.dirname(db_path), exist_ok=True)
            
            with sqlite_connection(db_path) as conn:
                conn.execute(
                    """INSERT INTO notifications 
                    (id, destinataire_sso, destinataire_role, id_portefeuille, titre, message, type, is_read)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 0)""",
                    (notif_id, destinataire_sso, destinataire_role, id_portefeuille, titre, message, type)
                )
        except Exception as e:
            logger.error(f"Erreur lors de la creation de notification dans {db_path} : {e}")
            
    return notif_id

def get_unread_notifications(
    user_role: str,
    user_sso: str,
    visible_lobs: List[str]
) -> List[Dict[str, Any]]:
    """
    Récupère les notifications non lues ciblant le rôle de l'utilisateur ou son SSO spécifique,
    en respectant le cloisonnement par LOB (id_portefeuille).
    """
    db_path = DBS[0] # On lit sur la base principale
    if not os.path.exists(db_path):
        return []
        
    results = []
    try:
        with sqlite_connection(db_path) as conn:
            # Query notifications where is_read is FALSE
            cursor = conn.cursor()
            cursor.execute(
                """SELECT id, destinataire_sso, destinataire_role, id_portefeuille, titre, message, type, is_read, timestamp
                   FROM notifications
                   WHERE is_read = 0
                   ORDER BY timestamp DESC"""
            )
            rows = cursor.fetchall()
            
            for row in rows:
                row_dict = dict(row)
                
                # Filtrage destinataire : soit le SSO correspond, soit le rôle correspond
                dest_sso = row_dict["destinataire_sso"]
                dest_role = row_dict["destinataire_role"]
                lob = row_dict["id_portefeuille"]
                
                # Si un SSO spécifique est indiqué, il doit correspondre à l'utilisateur connecté
                if dest_sso and dest_sso != user_sso:
                    continue
                    
                # Si aucun SSO n'est indiqué mais un rôle l'est, il doit correspondre au rôle connecté
                if not dest_sso and dest_role and dest_role != user_role:
                    continue
                    
                # Si ni SSO ni rôle ne sont indiqués, ou si le rôle correspond, on vérifie le LOB
                if lob and lob not in visible_lobs:
                    continue
                    
                results.append(row_dict)
    except Exception as e:
        logger.error(f"Erreur lors de la lecture des notifications : {e}")
        
    return results

def mark_as_read(notification_id: str) -> bool:
    """
    Marque une notification spécifique comme lue dans les deux bases.
    """
    success = False
    for db_path in DBS:
        if os.path.exists(db_path):
            try:
                with sqlite_connection(db_path) as conn:
                    conn.execute(
                        "UPDATE notifications SET is_read = 1 WHERE id = ?",
                        (notification_id,)
                    )
                    success = True
            except Exception as e:
                logger.error(f"Erreur lors du marquage comme lu dans {db_path} : {e}")
    return success

def mark_all_as_read(user_role: str, user_sso: str) -> int:
    """
    Marque toutes les notifications destinées à l'utilisateur connecté comme lues dans les deux bases.
    Retourne le nombre théorique de lignes modifiées.
    """
    modified_count = 0
    for db_path in DBS:
        if os.path.exists(db_path):
            try:
                with sqlite_connection(db_path) as conn:
                    # En SQL, on met à jour les lignes qui ciblent le SSO ou le rôle connecté
                    cursor = conn.cursor()
                    cursor.execute(
                        """UPDATE notifications
                           SET is_read = 1
                           WHERE is_read = 0 AND (destinataire_sso = ? OR (destinataire_sso IS NULL AND destinataire_role = ?))""",
                        (user_sso, user_role)
                    )
                    if db_path == DBS[0]:
                        modified_count = cursor.rowcount
            except Exception as e:
                logger.error(f"Erreur lors du marquage de toutes les notifications dans {db_path} : {e}")
    return modified_count
