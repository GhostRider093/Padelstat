"""
Tests du vocabulaire.

Le vocabulaire est la seule source de synonymes. Ces tests verifient qu'il
couvre l'arbre, qu'il ne se contredit pas, et qu'il est deja sous la forme
que produit le normaliseur.

Voir SPEC_MODULE_VOCAL_PTT_V2.md section 11.2.
"""

import unicodedata

import pytest

from app.voice import arbre, vocabulaire
from app.voice.extraction import SCORER
from app.voice.vocabulaire import (
    TABLES,
    synonymes,
    termes_du_noeud,
    toutes_les_entrees,
)

SEUIL_FUZZY = 80


# --------------------------------------------------------------------------
# Forme des synonymes
# --------------------------------------------------------------------------


def test_synonymes_deja_normalises():
    """Le normaliseur passe en minuscules et retire les accents. Un synonyme
    accentue ne serait jamais atteint."""
    fautifs = []
    for slot, valeur, synonyme in toutes_les_entrees():
        texte = str(synonyme)
        sans_accent = "".join(
            c for c in unicodedata.normalize("NFKD", texte)
            if not unicodedata.combining(c)
        )
        if texte != texte.lower() or texte != sans_accent:
            fautifs.append((slot, valeur, synonyme))
    assert fautifs == []


def test_pas_de_synonyme_vide():
    for slot, valeur, synonyme in toutes_les_entrees():
        assert str(synonyme).strip(), f"{slot}/{valeur} porte un synonyme vide"


def test_pas_de_doublon_dans_une_meme_cle():
    for slot, table in TABLES.items():
        for valeur, liste in table.items():
            liste = [str(s) for s in liste]
            assert len(liste) == len(set(liste)), f"{slot}/{valeur}"


# --------------------------------------------------------------------------
# Couverture de l'arbre
# --------------------------------------------------------------------------


def _valeurs_de_l_arbre():
    """Toutes les (slot, valeur) que l'arbre peut demander."""
    trouvees = set()
    vus = set()
    pile = [arbre.RACINE]
    while pile:
        noeud = pile.pop()
        if noeud is None or id(noeud) in vus:
            continue
        vus.add(id(noeud))
        if noeud.branches:
            for valeur, suite in noeud.branches.items():
                trouvees.add((noeud.slot, valeur))
                pile.append(suite)
        else:
            for valeur in (1, 2, 3, 4):
                trouvees.add((noeud.slot, valeur))
            pile.append(noeud.suivant)
    return trouvees


def test_toute_valeur_de_l_arbre_est_prononcable():
    """Une valeur sans synonyme est inatteignable a la voix."""
    muettes = []
    for slot, valeur in sorted(_valeurs_de_l_arbre(), key=str):
        if not synonymes(slot).get(valeur):
            muettes.append((slot, valeur))
    assert muettes == []


def test_le_vocabulaire_n_invente_pas_de_valeurs():
    """Un synonyme pour une valeur absente de l'arbre ne servirait jamais."""
    connues = _valeurs_de_l_arbre()
    orphelines = []
    for slot, table in TABLES.items():
        if slot in ("joueur", "defenseur") or slot.endswith("_def"):
            continue
        for valeur in table:
            if (slot, valeur) not in connues:
                orphelines.append((slot, valeur))
    assert orphelines == []


def test_les_slots_defenseur_partagent_le_vocabulaire():
    assert synonymes("zone_def") is synonymes("zone")
    assert synonymes("coup_bh_def") is synonymes("coup_bh")


# --------------------------------------------------------------------------
# Collisions
# --------------------------------------------------------------------------
#
# L'extraction essaie les n-grammes du plus long au plus court et consomme
# les tokens retenus. Une ambiguite entre « faute » et « faute provoquee »
# est donc tranchee par la longueur, pas par le score. Ce qui doit etre
# discriminable, ce sont les synonymes de MEME longueur en tokens.


def _par_longueur():
    groupes = {}
    for slot, valeur, synonyme in toutes_les_entrees():
        texte = str(synonyme)
        groupes.setdefault(len(texte.split()), []).append(
            (slot, valeur, texte))
    return groupes


def test_pas_de_synonyme_partage_entre_deux_cles():
    """Le meme mot ne peut pas designer deux choses."""
    proprietaires = {}
    conflits = []
    for slot, valeur, synonyme in toutes_les_entrees():
        texte = str(synonyme)
        precedent = proprietaires.get(texte)
        if precedent and precedent != (slot, valeur):
            conflits.append((texte, precedent, (slot, valeur)))
        proprietaires[texte] = (slot, valeur)
    assert conflits == []


def test_pas_de_collision_fuzzy_a_longueur_egale():
    """Deux valeurs distinctes ne doivent pas etre confondables.

    L'egalite stricte ne suffit pas : « bandera » et « barada » sont
    distincts mais phonetiquement voisins, et c'est le score qui tranche.
    """
    collisions = []
    for longueur, entrees in _par_longueur().items():
        for i, (slot_a, val_a, texte_a) in enumerate(entrees):
            for slot_b, val_b, texte_b in entrees[i + 1:]:
                if (slot_a, val_a) == (slot_b, val_b):
                    continue
                score = SCORER(texte_a, texte_b)
                if score >= SEUIL_FUZZY:
                    collisions.append(
                        (score, texte_a, f"{slot_a}={val_a}",
                         texte_b, f"{slot_b}={val_b}"))

    detail = "\n".join(
        f"  {s:.0f}  {a!r} ({ka})  vs  {b!r} ({kb})"
        for s, a, ka, b, kb in sorted(collisions, reverse=True)
    )
    assert not collisions, f"\n{detail}"


# --------------------------------------------------------------------------
# Biais de decodage contextuel
# --------------------------------------------------------------------------


def test_termes_du_noeud_restreint_au_noeud():
    """En attente d'un slot, on ne propose que ce que ce noeud admet."""
    coup_bh = arbre.COUP().branches["fond_de_court"].branches["balle_haute"]
    termes = termes_du_noeud(coup_bh)

    assert "bandeja" in termes
    assert "bajada" in termes
    assert "coup droit" not in termes
    assert "filet" not in termes


def test_termes_du_noeud_respecte_c4():
    """Au filet, la bajada n'est pas proposable."""
    volee_bh = arbre.COUP().branches["volee"].branches["balle_haute"]
    termes = termes_du_noeud(volee_bh)

    assert "bandeja" in termes
    assert "bajada" not in termes


def test_termes_du_noeud_respecte_c3():
    """Le defenseur ne sert pas : « service » ne lui est jamais propose."""
    termes = termes_du_noeud(arbre.COUP_DEFENSEUR)
    assert "service" not in termes
    assert "filet" in termes


# --------------------------------------------------------------------------
# Ancrage sur les mesures
# --------------------------------------------------------------------------


@pytest.mark.parametrize("deformation, slot, attendu", [
    ("barada", "coup_bh", "bajada"),
    ("barana", "coup_bh", "bajada"),
    ("parada", "coup_bh", "bajada"),
    ("mahada", "coup_bh", "bajada"),
    ("bandera", "coup_bh", "bandeja"),
    ("vibra", "coup_bh", "vibora"),
    ("vibro", "coup_bh", "vibora"),
    ("ou droit", "type_coup", "coup_droit"),
    ("pour droit", "type_coup", "coup_droit"),
    ("roue droit", "type_coup", "coup_droit"),
    ("bouroir", "type_coup", "coup_droit"),
    ("courant", "type_coup", "coup_droit"),
    ("tour de court", "zone", "fond_de_court"),
    ("fillet", "zone", "volee"),
])
def test_deformations_mesurees_resolues(deformation, slot, attendu):
    """Chaque deformation relevee sur les 89 captures doit se resoudre.

    Soit elle figure comme synonyme, soit le fuzzy la rattrape.
    """
    table = synonymes(slot)
    meilleur, score_max = None, 0
    for valeur, liste in table.items():
        for synonyme in liste:
            score = SCORER(deformation, str(synonyme))
            if score > score_max:
                meilleur, score_max = valeur, score

    assert score_max >= SEUIL_FUZZY, (
        f"{deformation!r} ne matche rien (meilleur {score_max:.0f})")
    assert meilleur == attendu, (
        f"{deformation!r} -> {meilleur} au lieu de {attendu}")
