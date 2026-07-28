"""
Pont entre une intention vocale et l'AnnotationManager.

Tout ce qui sait ce qu'est un arbre s'arrete ici. `main_window.py` ne voit
qu'un objet avec `appliquer()`, `annuler()` et `decrire()` — critere
d'acceptation 10 de la spec.

Voir SPEC_MODULE_VOCAL_PTT_V2.md section 8.
"""

from __future__ import annotations

import logging
from typing import Callable, Optional

from app.voice.parser import Intention

logger = logging.getLogger(__name__)

LIBELLES_TYPE = {
    "point_gagnant": "Point gagnant",
    "faute_directe": "Faute directe",
    "faute_provoquee": "Faute provoquée",
}


class AnnotateurVocal:
    """Ecrit une intention dans l'AnnotationManager.

    `horodatage` rend `(timestamp, frame)` a l'instant de l'annotation :
    c'est la position de la video, que seul l'appelant connait.
    """

    def __init__(self, annotation_manager, horodatage: Callable, roster=None):
        self.annotation_manager = annotation_manager
        self.horodatage = horodatage
        self.roster = roster or []

    def set_roster(self, roster) -> None:
        self.roster = roster or []

    # ------------------------------------------------------------- joueurs

    def nom(self, rang: Optional[int]) -> Optional[str]:
        """Rang 1..4 -> nom du joueur. L'AnnotationManager travaille avec
        des noms, l'arbre avec des rangs."""
        if rang is None or not (1 <= rang <= len(self.roster)):
            return None
        joueur = self.roster[rang - 1]
        return joueur.get("nom") if isinstance(joueur, dict) else str(joueur)

    # ------------------------------------------------------------- ecriture

    def appliquer(self, intention: Intention):
        """Ecrit l'annotation. Rend le dict cree, ou None si refusee."""
        joueur = self.nom(intention.joueur)
        if joueur is None:
            logger.warning("intention sans joueur identifiable, ignoree")
            return None

        timestamp, frame = self.horodatage()
        type_coup = intention.type_coup_id()

        if intention.type_point == "point_gagnant":
            return self.annotation_manager.add_point_gagnant(
                joueur, timestamp, frame, type_coup)

        if intention.type_point == "faute_directe":
            return self.annotation_manager.add_faute_directe(
                joueur, timestamp, frame, type_coup)

        if intention.type_point == "faute_provoquee":
            defenseur = self.nom(intention.defenseur)
            if defenseur is None:
                logger.warning("faute provoquee sans defenseur, ignoree")
                return None
            return self.annotation_manager.add_faute_provoquee(
                joueur, defenseur, timestamp, frame,
                type_coup_attaquant=type_coup,
                type_coup_defenseur=intention.type_coup_id("_def"))

        logger.warning("type de point inconnu : %r", intention.type_point)
        return None

    def annuler(self):
        """Efface la derniere annotation ecrite."""
        return self.annotation_manager.remove_last_annotation()

    # ------------------------------------------------------------- affichage

    def decrire(self, intention: Intention) -> str:
        """Phrase lisible, pour confirmation avant ecriture.

        « Aucune annotation ne doit etre ecrite sans que l'utilisateur ait
        pu la voir » — c'est ce texte qu'il voit.
        """
        from app.exports.type_coup_labels import get_coup_label

        morceaux = [LIBELLES_TYPE.get(intention.type_point, "?")]

        joueur = self.nom(intention.joueur)
        if intention.type_point == "faute_provoquee":
            defenseur = self.nom(intention.defenseur)
            morceaux.append(f"{joueur or '?'} sur {defenseur or '?'}")
        elif joueur:
            morceaux.append(joueur)

        coup = intention.type_coup_id()
        if coup:
            morceaux.append(get_coup_label(coup))

        coup_def = intention.type_coup_id("_def")
        if coup_def:
            morceaux.append(f"→ {get_coup_label(coup_def)}")

        return " · ".join(morceaux)


def question(slot: str) -> str:
    """Ce qu'on demande a l'utilisateur pour un slot manquant.

    Une seule question a la fois : celle du noeud courant.
    """
    return QUESTIONS.get(slot, f"{slot} ?")


QUESTIONS = {
    "type_point": "Point gagnant, faute directe ou faute provoquée ?",
    "joueur": "Quel joueur ?",
    "defenseur": "Qui a subi la faute ?",
    "zone": "D'où : service, lob, filet ou fond de court ?",
    "type_coup": "Coup droit, revers ou balle haute ?",
    "coup_bh": "Smash, víbora, bandeja ou bajada ?",
    "zone_def": "Le défenseur : lob, filet ou fond de court ?",
    "type_coup_def": "Le défenseur : coup droit, revers ou balle haute ?",
    "coup_bh_def": "Le défenseur : smash, víbora ou bandeja ?",
}
