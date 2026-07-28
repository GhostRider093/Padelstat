"""
Normalisation du texte transcrit.

**Aucune substitution lexicale metier ici.** Pas de « foot » -> « faute »,
pas de « volet » -> « volee ». C'est ce qui a tue la version precedente :
80 `str.replace()` enchaines, dont certains s'auto-sabotaient (remplacer
« faute provoque » par « faute provoquee » dans une chaine deja correcte
produisait « faute provoqueee », qui ne matchait plus rien).

Ce module ne fait que ramener un texte a une forme canonique. Le sens vit
dans vocabulaire.py.

**La meme fonction s'applique au texte ET aux synonymes.** C'est une
obligation, pas une commodite : `de` est un mot vide et figure aussi dans
« fond de court ». Filtrer d'un seul cote ferait cesser le synonyme de
matcher. Voir `test_normalizer.py::test_symetrie_texte_synonymes`.

Voir SPEC_MODULE_VOCAL_PTT_V2.md section 7.1.
"""

from __future__ import annotations

import re
import unicodedata

from app.voice.vocabulaire import MOTS_VIDES

# Chiffres -> lettres. Whisper rend « joueur 3 » aussi bien que
# « joueur trois » ; on unifie sur la forme lettre.
CHIFFRES = {
    "0": "zero", "1": "un", "2": "deux", "3": "trois", "4": "quatre",
    "5": "cinq", "6": "six", "7": "sept", "8": "huit", "9": "neuf",
}

_MOTS_VIDES_SIMPLES = frozenset(m for m in MOTS_VIDES if " " not in m)
_MOTS_VIDES_COMPOSES = tuple(m for m in MOTS_VIDES if " " in m)

_PONCTUATION = re.compile(r"[^a-z0-9 ]")
_ESPACES = re.compile(r"\s+")


def sans_accents(texte: str) -> str:
    decompose = unicodedata.normalize("NFKD", texte)
    return "".join(c for c in decompose if not unicodedata.combining(c))


def normaliser(texte: str) -> str:
    """Forme canonique d'un enonce ou d'un synonyme.

    Idempotente : `normaliser(normaliser(x)) == normaliser(x)`.
    """
    if not texte:
        return ""

    texte = sans_accents(texte.lower())

    # L'apostrophe devient une frontiere de mot : « l'objet » -> « l objet ».
    texte = _PONCTUATION.sub(" ", texte)
    texte = _ESPACES.sub(" ", texte).strip()

    # Les expressions vides d'abord, tant que leurs mots sont voisins.
    for expression in _MOTS_VIDES_COMPOSES:
        texte = texte.replace(f" {expression} ", " ")
        for bord in (f"{expression} ", f" {expression}"):
            if texte.startswith(bord) or texte.endswith(bord):
                texte = _ESPACES.sub(" ", texte.replace(bord, " ")).strip()

    mots = []
    for mot in texte.split():
        mot = CHIFFRES.get(mot, mot)
        if mot in _MOTS_VIDES_SIMPLES:
            continue
        mots.append(mot)

    return " ".join(mots)


def tokens(texte: str) -> list:
    """Texte normalise, decoupe en mots."""
    normalise = normaliser(texte)
    return normalise.split() if normalise else []


def ngrammes(mots: list, taille_max: int = 4):
    """(debut, longueur, texte) pour chaque n-gramme, du plus long au plus
    court. L'ordre importe : « fond de court » doit etre essaye avant
    « fond », et « balle haute » avant « balle »."""
    for longueur in range(min(taille_max, len(mots)), 0, -1):
        for debut in range(len(mots) - longueur + 1):
            yield debut, longueur, " ".join(mots[debut:debut + longueur])
