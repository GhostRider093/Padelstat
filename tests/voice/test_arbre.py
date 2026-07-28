"""
Tests de l'arbre du domaine.

Structure seule : ni texte, ni audio, ni vocabulaire. Si l'arbre est faux,
tout ce qui s'appuie dessus l'est aussi.

Voir SPEC_MODULE_VOCAL_PTT_V2.md sections 3 et 11.2.
"""

import pytest

from app.voice import arbre
from app.voice.arbre import (
    COUP,
    RACINE,
    chemin,
    coups_terminaux,
    est_complete,
    identifiant_coup,
    noeud_courant,
    roster_sans_equipes,
    slot_attendu,
    slots_applicables,
    valeurs_admises,
)


# Les 13 coups terminaux attendus, ecrits a la main pour que le test verifie
# l'arbre plutot que de se contenter de le recopier.
COUPS_ATTENDUS = {
    "service",
    "lob",
    "fond_de_court_CD",
    "fond_de_court_R",
    "fond_de_court_BH_smash",
    "fond_de_court_BH_vibora",
    "fond_de_court_BH_bandeja",
    "fond_de_court_BH_bajada",
    "volee_CD",
    "volee_R",
    "volee_BH_smash",
    "volee_BH_vibora",
    "volee_BH_bandeja",
}


@pytest.fixture
def roster():
    """Deux equipes de deux, format annotation_manager."""
    return [
        {"nom": "pascal", "equipe": 1, "zone": "gauche"},
        {"nom": "arnaud", "equipe": 1, "zone": "droite"},
        {"nom": "philippe", "equipe": 2, "zone": "gauche"},
        {"nom": "alex", "equipe": 2, "zone": "droite"},
    ]


@pytest.fixture
def roster_plat():
    """Ancien format players.json : des prenoms, sans equipe."""
    return ["pascal", "arnaud", "philippe", "alex"]


# --------------------------------------------------------------------------
# Structure
# --------------------------------------------------------------------------


def test_treize_coups_terminaux():
    assert coups_terminaux() == COUPS_ATTENDUS


def test_types_de_point():
    assert set(RACINE.valeurs()) == {
        "point_gagnant", "faute_directe", "faute_provoquee",
    }


def test_c3_le_defenseur_ne_sert_pas():
    """Le defenseur subit le coup, il n'est pas en train de servir."""
    positions_defenseur = set(arbre.COUP_DEFENSEUR.valeurs())

    assert "service" not in positions_defenseur
    assert positions_defenseur == {"lob", "fond_de_court", "volee"}
    assert "service" in set(COUP().valeurs())          # mais l'attaquant, oui


def test_c3_le_defenseur_produit_douze_coups():
    coups = coups_terminaux(suffixe="_def", avec_service=False)
    assert coups == COUPS_ATTENDUS - {"service"}
    assert len(coups) == 12


def test_c4_bajada_seulement_au_fond_de_court():
    """La bajada se joue apres rebond au mur du fond : impossible en volee."""
    racine_coup = COUP()

    bh_fond = racine_coup.branches["fond_de_court"].branches["balle_haute"]
    bh_volee = racine_coup.branches["volee"].branches["balle_haute"]

    assert "bajada" in bh_fond.valeurs()
    assert "bajada" not in bh_volee.valeurs()
    assert set(bh_volee.valeurs()) == {"smash_plat", "vibora", "bandeja"}


def test_c4_vaut_aussi_pour_le_defenseur():
    bh_volee = arbre.COUP_DEFENSEUR.branches["volee"].branches["balle_haute"]
    assert "bajada" not in bh_volee.valeurs()


def test_service_et_lob_sont_terminaux():
    racine_coup = COUP()
    assert racine_coup.suite("service") is None
    assert racine_coup.suite("lob") is None


# --------------------------------------------------------------------------
# Parcours
# --------------------------------------------------------------------------


def test_faute_directe_porte_un_coup():
    """Contrairement au schema historique, qui l'arretait au joueur."""
    etat = {"type_point": "faute_directe", "joueur": 2}

    assert not est_complete(etat)
    assert slot_attendu(etat) == "zone"

    etat["zone"] = "service"
    assert est_complete(etat)


def test_point_gagnant_complet():
    etat = {
        "type_point": "point_gagnant",
        "joueur": 3,
        "zone": "fond_de_court",
        "type_coup": "balle_haute",
        "coup_bh": "bajada",
    }
    assert est_complete(etat)
    assert identifiant_coup(etat) == "fond_de_court_BH_bajada"


def test_une_seule_question_a_la_fois():
    """On demande le noeud courant, jamais une liste de slots manquants."""
    etat = {}
    attendus = []

    while not est_complete(etat):
        slot = slot_attendu(etat)
        attendus.append(slot)
        etat[slot] = {
            "type_point": "point_gagnant",
            "joueur": 1,
            "zone": "volee",
            "type_coup": "revers",
        }[slot]

    assert attendus == ["type_point", "joueur", "zone", "type_coup"]


def test_faute_provoquee_decrit_un_joueur_puis_l_autre():
    """Attaquant + son coup, puis defenseur + son coup. Pas d'entrelacement."""
    etat = {"type_point": "faute_provoquee", "joueur": 1}

    # D'abord le coup de l'attaquant, entierement.
    assert slot_attendu(etat) == "zone"
    etat["zone"] = "volee"
    assert slot_attendu(etat) == "type_coup"
    etat["type_coup"] = "balle_haute"
    assert slot_attendu(etat) == "coup_bh"
    etat["coup_bh"] = "vibora"

    # Seulement ensuite, le defenseur.
    assert slot_attendu(etat) == "defenseur"
    etat["defenseur"] = 3
    assert slot_attendu(etat) == "zone_def"

    etat["zone_def"] = "fond_de_court"
    assert slot_attendu(etat) == "type_coup_def"

    etat["type_coup_def"] = "revers"
    assert est_complete(etat)

    assert identifiant_coup(etat) == "volee_BH_vibora"
    assert identifiant_coup(etat, suffixe="_def") == "fond_de_court_R"


def test_le_defenseur_vient_apres_le_coup_de_l_attaquant():
    """Le defenseur n'est pas demande tant que l'attaquant est incomplet."""
    etat = {"type_point": "faute_provoquee", "joueur": 1, "zone": "volee"}
    assert slot_attendu(etat) == "type_coup"      # pas "defenseur"


def test_faute_provoquee_va_jusqu_a_neuf_slots():
    etat = {
        "type_point": "faute_provoquee",
        "joueur": 2,
        "defenseur": 4,
        "zone": "fond_de_court",
        "type_coup": "balle_haute",
        "coup_bh": "bajada",
        "zone_def": "volee",
        "type_coup_def": "balle_haute",
        "coup_bh_def": "bandeja",
    }
    assert est_complete(etat)
    assert len(chemin(etat)) == 9


def test_valeur_inadmissible_ne_bloque_pas_le_parcours():
    """« volee bajada » : la valeur est rejetee, la question est reposee."""
    etat = {
        "type_point": "point_gagnant",
        "joueur": 1,
        "zone": "volee",
        "type_coup": "balle_haute",
        "coup_bh": "bajada",          # C4 : impossible en volee
    }

    assert not est_complete(etat)
    assert slot_attendu(etat) == "coup_bh"
    assert valeurs_admises(etat, "coup_bh") == {
        "smash_plat", "vibora", "bandeja",
    }


# --------------------------------------------------------------------------
# Slots applicables
# --------------------------------------------------------------------------


def test_service_ferme_le_coup():
    """« service coup droit » : le type de coup n'est pas applicable."""
    etat = {"type_point": "point_gagnant", "joueur": 1, "zone": "service"}
    assert "type_coup" not in slots_applicables(etat)


def test_volee_ouvre_le_type_de_coup():
    etat = {"type_point": "point_gagnant", "joueur": 1, "zone": "volee"}
    applicables = slots_applicables(etat)
    assert "type_coup" in applicables
    assert "coup_bh" in applicables


def test_faute_directe_n_a_pas_de_slots_defenseur():
    etat = {"type_point": "faute_directe", "joueur": 1}
    applicables = slots_applicables(etat)
    assert "defenseur" not in applicables
    assert "zone_def" not in applicables


def test_faute_provoquee_a_les_slots_defenseur():
    etat = {"type_point": "faute_provoquee", "joueur": 1}
    applicables = slots_applicables(etat)
    assert {"defenseur", "zone_def", "type_coup_def"} <= applicables


# --------------------------------------------------------------------------
# Contraintes contextuelles (C1, C2)
# --------------------------------------------------------------------------


def test_c1_c2_le_defenseur_est_un_adversaire(roster):
    etat = {"type_point": "faute_provoquee", "joueur": 1}
    assert valeurs_admises(etat, "defenseur", roster) == {3, 4}


def test_c1_c2_depuis_l_autre_equipe(roster):
    """L'equipe est lue sur le roster, jamais deduite du rang."""
    etat = {"type_point": "faute_provoquee", "joueur": 3}
    assert valeurs_admises(etat, "defenseur", roster) == {1, 2}


def test_c1_c2_rejettent_un_coequipier(roster):
    etat = {"type_point": "faute_provoquee", "joueur": 1,
            "zone": "service", "defenseur": 2}
    assert slot_attendu(etat, roster) == "defenseur"


def test_c1_c2_rejettent_soi_meme(roster):
    etat = {"type_point": "faute_provoquee", "joueur": 1,
            "zone": "service", "defenseur": 1}
    assert slot_attendu(etat, roster) == "defenseur"


def test_c1_seule_si_le_roster_n_a_pas_d_equipes(roster_plat):
    """Degradation explicite : sans equipes, C2 tombe, C1 tient."""
    assert roster_sans_equipes(roster_plat)

    etat = {"type_point": "faute_provoquee", "joueur": 1}
    assert valeurs_admises(etat, "defenseur", roster_plat) == {2, 3, 4}


def test_roster_avec_equipes_est_reconnu(roster):
    assert not roster_sans_equipes(roster)


def test_sans_roster_aucune_contrainte_de_joueur():
    """Sans roster, un coequipier passe : C1/C2 sont contextuelles."""
    etat = {"type_point": "faute_provoquee", "joueur": 1,
            "zone": "service", "defenseur": 2}
    assert slot_attendu(etat) == "zone_def"     # defenseur accepte


# --------------------------------------------------------------------------
# Identifiants
# --------------------------------------------------------------------------


@pytest.mark.parametrize("etat, attendu", [
    ({"zone": "service"}, "service"),
    ({"zone": "lob"}, "lob"),
    ({"zone": "volee", "type_coup": "coup_droit"}, "volee_CD"),
    ({"zone": "volee", "type_coup": "revers"}, "volee_R"),
    ({"zone": "fond_de_court", "type_coup": "coup_droit"},
     "fond_de_court_CD"),
    ({"zone": "fond_de_court", "type_coup": "balle_haute",
      "coup_bh": "smash_plat"}, "fond_de_court_BH_smash"),
    ({"zone": "fond_de_court", "type_coup": "balle_haute",
      "coup_bh": "bajada"}, "fond_de_court_BH_bajada"),
])
def test_identifiant_coup(etat, attendu):
    assert identifiant_coup(etat) == attendu


def test_identifiant_none_tant_que_le_coup_est_incomplet():
    assert identifiant_coup({}) is None
    assert identifiant_coup({"zone": "volee"}) is None
    assert identifiant_coup(
        {"zone": "volee", "type_coup": "balle_haute"}) is None


def test_smash_plat_garde_la_cle_historique():
    """`smash_plat` s'ecrit `smash` : compatibilite des matchs annotes."""
    etat = {"zone": "volee", "type_coup": "balle_haute",
            "coup_bh": "smash_plat"}
    assert identifiant_coup(etat) == "volee_BH_smash"


# --------------------------------------------------------------------------
# Coherence avec les libelles d'export
# --------------------------------------------------------------------------


def test_les_libelles_couvrent_l_arbre():
    """Tout coup annotable doit avoir un libelle.

    Sans ca, un point au lob s'affiche « ❓ lob » dans les rapports — ce
    qui etait le cas avant la refonte.
    """
    from app.exports.type_coup_labels import TYPE_COUP_LABELS_V2

    manquantes = coups_terminaux() - set(TYPE_COUP_LABELS_V2)
    assert manquantes == set()


def test_tout_coup_a_une_categorie():
    """Les regroupements des graphiques doivent couvrir l'arbre aussi."""
    from app.exports.type_coup_labels import get_coup_category

    sans_categorie = {c for c in coups_terminaux()
                      if get_coup_category(c) == "autre"}
    assert sans_categorie == set()


def test_la_refonte_est_retrocompatible():
    """11 des 13 identifiants existaient deja a l'identique : les matchs
    annotes avant la refonte restent lisibles."""
    from app.exports.type_coup_labels import TYPE_COUP_LABELS_V2

    ajoutees = {"lob", "fond_de_court_BH_bajada"}
    assert len(coups_terminaux() - ajoutees) == 11
    assert ajoutees <= set(TYPE_COUP_LABELS_V2)


# --------------------------------------------------------------------------
# Garde-fous structurels
# --------------------------------------------------------------------------


def test_l_arbre_termine_sur_tous_les_chemins():
    """Aucun cycle : tout parcours atteint une feuille."""

    def descendre(noeud, profondeur=0):
        assert profondeur < 20, f"parcours trop profond en {noeud.slot}"
        if noeud is None:
            return
        suites = (noeud.branches.values() if noeud.branches
                  else [noeud.suivant])
        for suite in suites:
            descendre(suite, profondeur + 1)

    descendre(RACINE)


def test_noeud_courant_est_none_quand_complet():
    etat = {"type_point": "faute_directe", "joueur": 1, "zone": "lob"}
    assert noeud_courant(etat) is None
    assert slot_attendu(etat) is None
