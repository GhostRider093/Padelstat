"""Tests du normaliseur. Voir SPEC section 7.1."""

import pytest

from app.voice import vocabulaire
from app.voice.normalizer import ngrammes, normaliser, tokens


@pytest.mark.parametrize("brut, attendu", [
    ("Point Gagnant", "point gagnant"),
    ("faute provoquée", "faute provoquee"),
    ("víbora", "vibora"),
    ("Point gagnant, joueur un, service.", "point gagnant un service"),
    ("l'objet", "l objet"),
    ("joueur 3", "trois"),
    ("fond   de    court", "fond court"),
    ("", ""),
])
def test_normalisation(brut, attendu):
    assert normaliser(brut) == attendu


def test_idempotence():
    """Renormaliser ne doit plus rien changer."""
    for brut in ["Point gagnant, joueur un, service.", "víbora", "l'objet",
                 "faute provoquée joueur deux", "smash à plat", ""]:
        une = normaliser(brut)
        assert normaliser(une) == une


def test_le_mot_joueur_disparait():
    """« joueur un » et « joueur deux » ont un WRatio de 80, exactement le
    seuil : le prefixe commun noie la syllabe discriminante."""
    assert normaliser("joueur un") == "un"
    assert normaliser("joueur deux") == "deux"


def test_liaisons_parasites_retirees():
    """Mesure : Whisper insere « de », « et », « a » entre les termes."""
    assert normaliser("filet de balle haute") == "filet balle haute"
    assert normaliser("balle haute et vibora") == "balle haute vibora"
    assert normaliser("joueur a un") == "un"


def test_symetrie_texte_synonymes():
    """Le filtrage des mots vides doit s'appliquer des deux cotes.

    « de » est un mot vide et figure dans « fond de court ». Normaliser le
    texte sans normaliser les synonymes ferait cesser le synonyme de matcher.
    """
    assert normaliser("fond de court") == normaliser("fond de court")
    assert normaliser("le fond de court") == "fond court"

    for slot, valeur, synonyme in vocabulaire.toutes_les_entrees():
        forme = normaliser(str(synonyme))
        assert forme == normaliser(forme), f"{slot}/{valeur}: {synonyme!r}"


def test_aucun_synonyme_ne_disparait_a_la_normalisation():
    """Un synonyme entierement compose de mots vides serait inatteignable."""
    vides = [(s, v, syn) for s, v, syn in vocabulaire.toutes_les_entrees()
             if not normaliser(str(syn))]
    assert vides == []


def test_tokens():
    assert tokens("Point gagnant, joueur trois !") == [
        "point", "gagnant", "trois"]
    assert tokens("") == []


def test_ngrammes_du_plus_long_au_plus_court():
    mots = ["fond", "court", "revers"]
    tailles = [longueur for _, longueur, _ in ngrammes(mots)]
    assert tailles == sorted(tailles, reverse=True)
    textes = [texte for _, _, texte in ngrammes(mots)]
    assert "fond court revers" in textes
    assert textes.index("fond court revers") < textes.index("fond")
