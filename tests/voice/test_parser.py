"""
Tests du parseur, sans aucun audio.

Voir SPEC_MODULE_VOCAL_PTT_V2.md sections 7.2, 7.3 et 11.
"""

import pytest

from app.voice.extraction import extraire, repartir
from app.voice.parser import Commande, Intention, parser


@pytest.fixture
def roster():
    return [
        {"nom": "pascal", "equipe": 1, "position": "gauche"},
        {"nom": "arnaud", "equipe": 1, "position": "droite"},
        {"nom": "philippe", "equipe": 2, "position": "gauche"},
        {"nom": "alex", "equipe": 2, "position": "droite"},
    ]


# --------------------------------------------------------------------------
# Extraction
# --------------------------------------------------------------------------


def test_ngramme_long_prioritaire():
    """« balle haute » doit gagner contre « balle », « fond de court »
    contre « fond »."""
    trouvailles = {t.slot: t.valeur
                   for t in extraire("fond de court balle haute bandeja")}
    assert trouvailles["zone"] == "fond_de_court"
    assert trouvailles["type_coup"] == "balle_haute"
    assert trouvailles["coup_bh"] == "bandeja"


def test_un_mot_n_alimente_qu_un_slot():
    trouvailles = extraire("fond de court revers")
    positions = [t.debut for t in trouvailles]
    assert len(positions) == len(set(positions))
    couverts = sum(t.longueur for t in trouvailles)
    assert couverts <= len(("fond court revers").split())


def test_ordre_d_apparition_pour_les_doublons():
    """Premier cite = attaquant, second = defenseur."""
    trouvailles = extraire("un service trois lob")
    affectations = repartir(trouvailles)
    assert affectations["joueur"].valeur == 1
    assert affectations["defenseur"].valeur == 3
    assert affectations["zone"].valeur == "service"
    assert affectations["zone_def"].valeur == "lob"


# --------------------------------------------------------------------------
# Intentions completes
# --------------------------------------------------------------------------


def test_point_gagnant_complet():
    intention = parser("point gagnant joueur trois filet revers")
    assert intention.type_point == "point_gagnant"
    assert intention.joueur == 3
    assert intention.zone == "volee"          # on dit filet, on stocke volee
    assert intention.type_coup == "revers"
    assert intention.est_complete()
    assert intention.type_coup_id() == "volee_R"


def test_faute_directe_porte_un_coup():
    intention = parser("faute directe joueur deux fond de court coup droit")
    assert intention.type_point == "faute_directe"
    assert intention.joueur == 2
    assert intention.est_complete()
    assert intention.type_coup_id() == "fond_de_court_CD"


@pytest.mark.parametrize("texte", [
    "point gagnant joueur trois filet revers",
    "filet revers point gagnant joueur trois",
    "trois point gagnant revers filet",
])
def test_ordre_des_mots_sans_importance(texte):
    """Entre slots differents, l'ordre n'intervient jamais."""
    intention = parser(texte)
    assert intention.type_point == "point_gagnant"
    assert intention.joueur == 3
    assert intention.zone == "volee"
    assert intention.type_coup == "revers"


def test_les_roles_annonces_liberent_l_ordre(roster):
    """Nommer « attaquant » et « défenseur » supprime la dernière
    contrainte d'ordre : le défenseur peut être cité en premier."""
    intention = parser(
        "faute provoquee defenseur joueur quatre fond de court revers "
        "attaquant joueur un service", roster)

    assert intention.joueur == 1                 # cité en second
    assert intention.zone == "service"
    assert intention.defenseur == 4              # cité en premier
    assert intention.zone_def == "fond_de_court"
    assert intention.type_coup_def == "revers"
    assert intention.est_complete(roster)


def test_les_roles_donnent_le_meme_resultat_dans_les_deux_sens(roster):
    a = parser("faute provoquee attaquant joueur un service "
               "defenseur joueur quatre fond de court revers", roster)
    b = parser("faute provoquee defenseur joueur quatre fond de court revers "
               "attaquant joueur un service", roster)

    assert a.slots_resolus() == b.slots_resolus()


def test_sans_role_l_ordre_tranche_toujours(roster):
    """Les marqueurs sont optionnels : la règle d'ordre reste la règle."""
    intention = parser(
        "faute provoquee joueur un service "
        "joueur quatre fond de court revers", roster)
    assert intention.joueur == 1
    assert intention.defenseur == 4


def test_le_marqueur_de_role_n_est_pas_pris_pour_une_valeur(roster):
    intention = parser(
        "faute provoquee attaquant joueur trois filet revers", roster)
    assert intention.joueur == 3
    assert intention.type_coup == "revers"
    assert intention.ignores == []


def test_le_coup_revient_au_defenseur_si_l_attaquant_a_servi(roster):
    """Cas mesuré en session : « premier cité = attaquant » jetait le coup.

    L'attaquant sert, donc sa branche n'admet aucun type de coup. Le seul
    coup nommé ne peut être que celui du défenseur.
    """
    intention = parser(
        "faute provoquee joueur un service "
        "joueur quatre fond de court revers", roster)

    assert intention.zone == "service"
    assert intention.type_coup is None          # service est terminal
    assert intention.defenseur == 4
    assert intention.zone_def == "fond_de_court"
    assert intention.type_coup_def == "revers"  # récupéré, pas jeté
    assert intention.ignores == []
    assert intention.est_complete(roster)


def test_meme_chose_avec_un_lob(roster):
    intention = parser(
        "faute provoquee joueur un lob joueur trois filet coup droit", roster)
    assert intention.zone == "lob"
    assert intention.type_coup_def == "coup_droit"
    assert intention.est_complete(roster)


def test_la_migration_ne_vole_pas_le_coup_de_l_attaquant(roster):
    """Si la branche de l'attaquant admet le coup, il lui reste."""
    intention = parser(
        "faute provoquee joueur un filet revers "
        "joueur quatre fond de court coup droit", roster)

    assert intention.type_coup == "revers"
    assert intention.type_coup_def == "coup_droit"


def test_faute_provoquee_un_joueur_puis_l_autre(roster):
    intention = parser(
        "faute provoquee joueur un filet balle haute vibora "
        "joueur trois fond de court revers", roster)

    assert intention.joueur == 1
    assert intention.defenseur == 3
    assert intention.type_coup_id() == "volee_BH_vibora"
    assert intention.type_coup_id("_def") == "fond_de_court_R"
    assert intention.est_complete(roster)


# --------------------------------------------------------------------------
# Inference ascendante
# --------------------------------------------------------------------------


def test_bajada_determine_tout_le_coup():
    """C4 : la bajada n'existe qu'au fond de court. Trois mots pour cinq
    slots, sans aucune question."""
    intention = parser("point gagnant joueur trois bajada")

    assert intention.zone == "fond_de_court"
    assert intention.type_coup == "balle_haute"
    assert intention.coup_bh == "bajada"
    assert intention.deduits == {"zone", "type_coup"}
    assert intention.est_complete()
    assert intention.type_coup_id() == "fond_de_court_BH_bajada"


def test_bandeja_laisse_la_zone_ouverte():
    """Une bandeja se joue du filet comme du fond : la zone reste a demander."""
    intention = parser("point gagnant joueur trois bandeja")

    assert intention.type_coup == "balle_haute"
    assert "type_coup" in intention.deduits
    assert intention.zone is None
    assert intention.slot_attendu() == "zone"


# --------------------------------------------------------------------------
# Refus explicites
# --------------------------------------------------------------------------


def test_slot_hors_branche_ignore():
    """« service coup droit » : le type de coup n'existe pas sous service."""
    intention = parser("point gagnant joueur deux service coup droit")

    assert intention.zone == "service"
    assert intention.type_coup is None
    assert intention.est_complete()
    assert any(slot == "type_coup" for slot, _, _ in intention.ignores)


def test_c2_rejette_un_coequipier(roster):
    """joueur 1 et 2 sont de la meme equipe : le defenseur reste a demander."""
    intention = parser("faute provoquee joueur un service joueur deux", roster)

    assert intention.joueur == 1
    assert intention.defenseur is None
    assert intention.slot_attendu(roster) == "defenseur"


def test_c2_accepte_un_adversaire(roster):
    intention = parser("faute provoquee joueur un service joueur trois", roster)
    assert intention.defenseur == 3


def test_intention_vide_demande_le_type_de_point():
    intention = parser("euh bon alors")
    assert intention.slot_attendu() == "type_point"
    assert not intention.est_complete()


# --------------------------------------------------------------------------
# Completion progressive
# --------------------------------------------------------------------------


def test_completion_conserve_les_slots_resolus():
    partielle = parser("point gagnant joueur trois bandeja")
    assert partielle.slot_attendu() == "zone"

    complete = parser("filet", base=partielle)
    assert complete.type_point == "point_gagnant"
    assert complete.joueur == 3
    assert complete.coup_bh == "bandeja"
    assert complete.zone == "volee"
    assert complete.est_complete()


def test_completion_en_quatre_souffles(roster):
    """L'enonce a 9 slots doit passer en une salve comme en plusieurs."""
    intention = parser("faute provoquee joueur un", roster)
    assert intention.slot_attendu(roster) == "zone"

    intention = parser("filet balle haute vibora", roster, base=intention)
    assert intention.slot_attendu(roster) == "defenseur"

    intention = parser("joueur trois", roster, base=intention)
    assert intention.slot_attendu(roster) == "zone_def"

    intention = parser("fond de court revers", roster, base=intention)
    assert intention.est_complete(roster)
    assert intention.type_coup_id() == "volee_BH_vibora"
    assert intention.type_coup_id("_def") == "fond_de_court_R"


# --------------------------------------------------------------------------
# Commandes de controle
# --------------------------------------------------------------------------


@pytest.mark.parametrize("texte", [
    "annuler",
    "Annuler.",
    "annule",
    "Annulé.",
    "On annule.",
    "Annuler le point.",     # « point » y attirait un point_gagnant
    "annuler ça",
    "supprime",
    "efface",
])
def test_annuler_court_circuite_l_arbre(texte):
    resultat = parser(texte)
    assert isinstance(resultat, Commande), f"{texte!r} est parti dans l'arbre"
    assert resultat.nom == "annuler"


@pytest.mark.parametrize("texte", [
    "faute directe joueur deux service",
    "point gagnant joueur trois filet revers",
    "point gagnant joueur un",
    "faute directe deux",
    "filet balle haute",
    "service coup droit",
    "bandeja",
])
def test_une_annotation_n_est_pas_une_commande(texte):
    """Le mot de contrôle ne doit jamais détourner une annotation."""
    assert isinstance(parser(texte), Intention), f"{texte!r} pris pour une commande"


# --------------------------------------------------------------------------
# Confiance
# --------------------------------------------------------------------------


def test_confiance_ignore_les_slots_deduits():
    intention = parser("point gagnant joueur trois bajada",
                       confiance_acoustique=0.8)
    assert "zone" not in intention.scores
    assert 0.0 < intention.confiance <= 1.0


def test_confiance_nulle_sans_rien_de_reconnu():
    assert parser("euh bon alors").confiance == 0.0
