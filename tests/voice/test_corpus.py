"""
Rejoue les transcriptions Whisper reellement mesurees a travers le parseur.

C'est le test qui compte : il ne verifie pas que le code fait ce que j'ai
imagine, mais qu'il tient sur ce que le moteur produit vraiment. Aucun audio
n'est necessaire — les transcriptions sont figees dans le journal.

Corpus : tests_audio/corpus_whisper/mesures.jsonl (114 captures).
"""

import json
import os

import pytest

from app.voice.parser import Commande, parser

CORPUS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "tests_audio", "corpus_whisper", "mesures.jsonl",
)

ROSTER = [
    {"nom": "pascal", "equipe": 1, "position": "gauche"},
    {"nom": "arnaud", "equipe": 1, "position": "droite"},
    {"nom": "philippe", "equipe": 2, "position": "gauche"},
    {"nom": "alex", "equipe": 2, "position": "droite"},
]


def _charger():
    if not os.path.exists(CORPUS):
        pytest.skip("corpus de mesures absent")

    entrees = []
    with open(CORPUS, encoding="utf-8") as fichier:
        for ligne in fichier:
            ligne = ligne.strip()
            if not ligne:
                continue
            entree = json.loads(ligne)
            if "attendu_slots" not in entree:
                continue
            # La premiere campagne disait « volee », qui n'est plus au
            # vocabulaire : ces enonces ne sont plus representatifs.
            if "volée" in entree["attendu_dit"]:
                continue
            # Le corpus a ete ecrit avant le renommage position -> zone.
            entree["attendu_slots"] = {
                ("zone" if cle == "position" else cle): valeur
                for cle, valeur in entree["attendu_slots"].items()
            }
            entrees.append(entree)
    return entrees


CAPTURES = _charger()


def _resultat(entree):
    """(genre, contradictions) pour une capture."""
    obtenu = parser(entree["transcription"], ROSTER)
    if isinstance(obtenu, Commande):
        return "faux", {"_": ("intention", "commande")}

    slots = obtenu.slots_resolus()
    contradictions = {
        cle: (valeur, slots.get(cle))
        for cle, valeur in entree["attendu_slots"].items()
        if slots.get(cle) != valeur
    }
    if not contradictions:
        return "exact", {}
    # Un slot non resolu sera demande ; un slot resolu differemment est faux.
    if all(obt is None for _, obt in contradictions.values()):
        return "incomplet", contradictions
    return "faux", contradictions


def test_corpus_non_vide():
    assert len(CAPTURES) >= 50


def test_aucune_intention_fausse_hors_bruit():
    """Une intention fausse coute plus cher qu'une question de trop.

    Les deux echecs tolerés sont des defauts de la donnée, pas du parseur :
    une capture ou l'annotateur commente au lieu d'annoter, et une ou
    Whisper insere un « joueur un » qui n'a pas ete prononcé.
    """
    faux = [(e, c) for e in CAPTURES
            for genre, c in [_resultat(e)] if genre == "faux"]

    detail = "\n".join(
        f"  {e['transcription']!r}\n     {c}" for e, c in faux)
    assert len(faux) <= 2, f"\n{detail}"


def test_taux_d_intentions_exactes():
    """Seuil fixé sous la mesure du 28/07/2026 (93 %), pour détecter une
    régression sans se casser sur du bruit."""
    genres = [_resultat(entree)[0] for entree in CAPTURES]
    exactes = genres.count("exact")
    taux = exactes / len(genres)

    assert taux >= 0.90, (
        f"{exactes}/{len(genres)} = {taux:.0%} — "
        f"incompletes {genres.count('incomplet')}, faux {genres.count('faux')}")


def test_aucune_annotation_ecrite_sans_type_de_point():
    """Garde-fou du §10 : rien ne doit pouvoir etre annoté sans type."""
    for entree in CAPTURES:
        obtenu = parser(entree["transcription"], ROSTER)
        if isinstance(obtenu, Commande):
            continue
        if obtenu.est_complete(ROSTER):
            assert obtenu.type_point is not None
            assert obtenu.joueur is not None


@pytest.mark.parametrize("transcription, attendu", [
    # Deformations espagnoles, relevees plusieurs fois chacune.
    ("Point gagnant, joueur trois, fond de court, balle haute, bandera.",
     {"type_point": "point_gagnant", "joueur": 3, "zone": "fond_de_court",
      "type_coup": "balle_haute", "coup_bh": "bandeja"}),
    ("Point gagnant, joueur quatre, fond de court, balle haute, barada.",
     {"type_point": "point_gagnant", "joueur": 4, "zone": "fond_de_court",
      "type_coup": "balle_haute", "coup_bh": "bajada"}),
    ("Point gagnant, joueur deux, fond de court, balle haute, vibra.",
     {"type_point": "point_gagnant", "joueur": 2, "zone": "fond_de_court",
      "type_coup": "balle_haute", "coup_bh": "vibora"}),
    # Liaisons parasites inserees par Whisper.
    ("point gagnant joueur trois filet de balle haute smash",
     {"type_point": "point_gagnant", "joueur": 3, "zone": "volee",
      "type_coup": "balle_haute", "coup_bh": "smash_plat"}),
    ("faute directe joueur a un service",
     {"type_point": "faute_directe", "joueur": 1, "zone": "service"}),
    # Variante orthographique de « filet ».
    ("fillet de revers point gagnant joueur trois",
     {"type_point": "point_gagnant", "joueur": 3, "zone": "volee",
      "type_coup": "revers"}),
])
def test_deformations_mesurees_bout_en_bout(transcription, attendu):
    """Chaque deformation relevee doit produire la bonne intention."""
    obtenu = parser(transcription, ROSTER).slots_resolus()
    for cle, valeur in attendu.items():
        assert obtenu.get(cle) == valeur, f"{cle}: {obtenu.get(cle)!r}"
