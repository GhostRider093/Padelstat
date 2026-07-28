"""
Tests du pont vers l'AnnotationManager.

Le vrai AnnotationManager ecrit sur disque et fait de l'autosave : on le
remplace par une doublure qui enregistre les appels.
"""

import pytest

from app.voice.integration import AnnotateurVocal, question
from app.voice.parser import parser

ROSTER = [
    {"nom": "pascal", "equipe": 1, "position": "gauche"},
    {"nom": "arnaud", "equipe": 1, "position": "droite"},
    {"nom": "philippe", "equipe": 2, "position": "gauche"},
    {"nom": "alex", "equipe": 2, "position": "droite"},
]


class FauxManager:
    def __init__(self):
        self.appels = []
        self.annotations = []

    def add_point_gagnant(self, joueur, timestamp, frame, type_coup=None):
        return self._ajouter("point_gagnant", joueur=joueur,
                             type_coup=type_coup)

    def add_faute_directe(self, joueur, timestamp, frame, type_coup=None):
        return self._ajouter("faute_directe", joueur=joueur,
                             type_coup=type_coup)

    def add_faute_provoquee(self, attaquant, defenseur, timestamp, frame,
                            type_coup_attaquant=None,
                            type_coup_defenseur=None):
        return self._ajouter("faute_provoquee", attaquant=attaquant,
                             defenseur=defenseur,
                             type_coup_attaquant=type_coup_attaquant,
                             type_coup_defenseur=type_coup_defenseur)

    def remove_last_annotation(self):
        return self.annotations.pop() if self.annotations else None

    def _ajouter(self, genre, **champs):
        annotation = dict(champs, type=genre)
        self.appels.append(annotation)
        self.annotations.append(annotation)
        return annotation


@pytest.fixture
def annotateur():
    return AnnotateurVocal(FauxManager(), lambda: (12.5, 375), ROSTER)


def test_point_gagnant_ecrit_avec_le_nom_du_joueur(annotateur):
    """L'arbre travaille avec des rangs, l'AnnotationManager avec des noms."""
    intention = parser("point gagnant joueur trois filet revers", ROSTER)
    annotateur.appliquer(intention)

    ecrit = annotateur.annotation_manager.appels[0]
    assert ecrit["type"] == "point_gagnant"
    assert ecrit["joueur"] == "philippe"
    assert ecrit["type_coup"] == "volee_R"


def test_faute_directe_porte_son_coup(annotateur):
    intention = parser("faute directe joueur deux fond de court coup droit",
                       ROSTER)
    annotateur.appliquer(intention)

    ecrit = annotateur.annotation_manager.appels[0]
    assert ecrit["type"] == "faute_directe"
    assert ecrit["joueur"] == "arnaud"
    assert ecrit["type_coup"] == "fond_de_court_CD"


def test_faute_provoquee_ecrit_les_deux_coups(annotateur):
    intention = parser(
        "faute provoquee joueur un filet balle haute vibora "
        "joueur trois fond de court revers", ROSTER)
    annotateur.appliquer(intention)

    ecrit = annotateur.annotation_manager.appels[0]
    assert ecrit["attaquant"] == "pascal"
    assert ecrit["defenseur"] == "philippe"
    assert ecrit["type_coup_attaquant"] == "volee_BH_vibora"
    assert ecrit["type_coup_defenseur"] == "fond_de_court_R"


def test_rien_n_est_ecrit_sans_joueur(annotateur):
    intention = parser("point gagnant filet revers", ROSTER)
    assert annotateur.appliquer(intention) is None
    assert annotateur.annotation_manager.appels == []


def test_faute_provoquee_incomplete_n_ecrit_rien(annotateur):
    intention = parser("faute provoquee joueur un service", ROSTER)
    assert annotateur.appliquer(intention) is None
    assert annotateur.annotation_manager.appels == []


def test_annuler_efface_la_derniere(annotateur):
    annotateur.appliquer(parser("point gagnant joueur un service", ROSTER))
    annotateur.appliquer(parser("faute directe joueur deux lob", ROSTER))
    assert len(annotateur.annotation_manager.annotations) == 2

    annotateur.annuler()
    assert len(annotateur.annotation_manager.annotations) == 1
    assert annotateur.annotation_manager.annotations[0]["joueur"] == "pascal"


# --------------------------------------------------------------------------
# Affichage
# --------------------------------------------------------------------------


def test_description_lisible(annotateur):
    intention = parser("point gagnant joueur trois fond de court balle haute "
                       "bandeja", ROSTER)
    texte = annotateur.decrire(intention)

    assert "Point gagnant" in texte
    assert "philippe" in texte
    assert "Bandeja" in texte


def test_description_faute_provoquee_montre_les_deux(annotateur):
    intention = parser(
        "faute provoquee joueur un service joueur trois lob", ROSTER)
    texte = annotateur.decrire(intention)

    assert "pascal sur philippe" in texte


def test_description_d_une_intention_partielle(annotateur):
    """Rien ne doit etre ecrit sans que l'utilisateur ait pu le voir : la
    description doit fonctionner meme incomplete."""
    intention = parser("point gagnant joueur trois", ROSTER)
    texte = annotateur.decrire(intention)
    assert "Point gagnant" in texte
    assert "philippe" in texte


def test_chaque_slot_a_une_question():
    from app.voice.parser import SLOTS
    for slot in SLOTS:
        assert question(slot) != f"{slot} ?", f"{slot} sans question"


# --------------------------------------------------------------------------
# Roster
# --------------------------------------------------------------------------


def test_roster_au_format_plat(annotateur):
    """players.json stocke encore une liste de prenoms."""
    annotateur.set_roster(["pascal", "arnaud", "philippe", "alex"])
    assert annotateur.nom(3) == "philippe"


def test_rang_hors_roster(annotateur):
    assert annotateur.nom(9) is None
    assert annotateur.nom(None) is None
