"""
Toute annotation vocale doit compter dans les statistiques.

`AnnotationManager.get_stats` range un `type_coup` inconnu dans « autre »,
sans rien signaler. Une annotation ecrite mais invisible dans les rapports
est exactement l'erreur silencieuse que le §10 de la spec interdit — et ni
les tests de l'arbre ni ceux des libelles ne l'auraient attrapee.
"""

import pytest

from app.annotations.annotation_manager import AnnotationManager
from app.voice.arbre import coups_terminaux

ROSTER = [
    {"nom": "pascal", "equipe": 1, "position": "gauche"},
    {"nom": "arnaud", "equipe": 1, "position": "droite"},
    {"nom": "philippe", "equipe": 2, "position": "gauche"},
    {"nom": "alex", "equipe": 2, "position": "droite"},
]


@pytest.fixture
def manager(tmp_path):
    m = AnnotationManager(data_folder=str(tmp_path), enable_background_ai=False)
    m.set_players(ROSTER)
    return m


def _stats_joueur(manager, nom="pascal"):
    stats = manager.get_stats()
    assert nom in stats, f"joueur {nom} absent des stats"
    return stats[nom]


def test_tout_coup_gagnant_est_compte(manager):
    """Aucun identifiant de l'arbre ne doit finir dans « autre »."""
    coups = sorted(coups_terminaux())
    for coup in coups:
        manager.add_point_gagnant("pascal", 10.0, 300, coup)

    detail = _stats_joueur(manager)["points_gagnants_detail"]

    assert detail["autre"] == 0, (
        "coups tombes dans « autre » : "
        + str([c for c in coups if c not in detail]))
    for coup in coups:
        assert detail.get(coup) == 1, f"{coup} non compte"


def test_toute_faute_directe_est_comptee(manager):
    coups = sorted(coups_terminaux())
    for coup in coups:
        manager.add_faute_directe("pascal", 10.0, 300, coup)

    detail = _stats_joueur(manager)["fautes_directes_detail"]
    assert detail["autre"] == 0
    assert sum(detail.values()) == len(coups)


def test_faute_provoquee_compte_les_deux_coups(manager):
    """Le coup de l'attaquant et celui du defenseur sont ranges chacun de
    leur cote."""
    manager.add_faute_provoquee(
        "pascal", "philippe", 10.0, 300,
        type_coup_attaquant="volee_BH_vibora",
        type_coup_defenseur="fond_de_court_R")

    stats = manager.get_stats()
    genere = stats["pascal"]["fautes_provoquees_generees_detail"]
    subi = stats["philippe"]["fautes_provoquees_subies_detail"]

    assert genere["volee_BH_vibora"] == 1
    assert genere["autre"] == 0
    assert subi["fond_de_court_R"] == 1
    assert subi["autre"] == 0


def test_les_coups_alimentent_les_categories_techniques(manager):
    """Une bandeja au filet doit compter en balle haute, en volee ET en
    bandeja : l'identifiant V2 porte les trois informations."""
    manager.add_point_gagnant("pascal", 10.0, 300, "volee_BH_bandeja")
    techniques = _stats_joueur(manager)["coups_techniques"]

    assert techniques["balle_haute"]["gagnants"] == 1
    assert techniques["volee"]["gagnants"] == 1
    assert techniques["bandeja"]["gagnants"] == 1
    assert techniques["fond_de_court"]["gagnants"] == 0


def test_la_bajada_a_sa_categorie(manager):
    """C4 : elle ne se joue qu'au fond de court."""
    manager.add_point_gagnant("pascal", 10.0, 300, "fond_de_court_BH_bajada")
    techniques = _stats_joueur(manager)["coups_techniques"]

    assert techniques["bajada"]["gagnants"] == 1
    assert techniques["fond_de_court"]["gagnants"] == 1
    assert techniques["volee"]["gagnants"] == 0


def test_le_lob_est_compte(manager):
    """Il manquait partout : libelles, categories, et ici."""
    manager.add_point_gagnant("pascal", 10.0, 300, "lob")
    stats = _stats_joueur(manager)

    assert stats["points_gagnants_detail"]["lob"] == 1
    assert stats["coups_techniques"]["lobe"]["gagnants"] == 1


def test_un_type_inconnu_tombe_bien_dans_autre(manager):
    """Le comportement de repli reste intact pour les vraies inconnues."""
    manager.add_point_gagnant("pascal", 10.0, 300, "coup_inexistant")
    assert _stats_joueur(manager)["points_gagnants_detail"]["autre"] == 1
