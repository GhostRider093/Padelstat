"""
Assemblage d'un enonce en intention d'annotation.

`extraction.py` trouve ce qui a ete dit ; ce module decide ce que ca veut
dire, en interrogeant l'arbre. Aucune regle de completude n'est ecrite ici :
elles vivent toutes dans `arbre.py`.

Voir SPEC_MODULE_VOCAL_PTT_V2.md sections 6.1 et 7.3.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Literal, Optional

from app.voice import arbre, extraction, vocabulaire
from app.voice.normalizer import normaliser

TypePoint = Literal["point_gagnant", "faute_directe", "faute_provoquee"]
Zone = Literal["service", "lob", "fond_de_court", "volee"]
TypeCoup = Literal["coup_droit", "revers", "balle_haute"]
CoupBH = Literal["smash_plat", "vibora", "bandeja", "bajada"]

SLOTS = (
    "type_point", "joueur", "zone", "type_coup", "coup_bh",
    "defenseur", "zone_def", "type_coup_def", "coup_bh_def",
)


@dataclass
class Intention:
    """Une annotation en cours de construction."""

    type_point: Optional[TypePoint] = None
    joueur: Optional[int] = None            # attaquant si faute provoquee
    zone: Optional[Zone] = None
    type_coup: Optional[TypeCoup] = None
    coup_bh: Optional[CoupBH] = None

    defenseur: Optional[int] = None
    zone_def: Optional[Zone] = None         # jamais "service" (C3)
    type_coup_def: Optional[TypeCoup] = None
    coup_bh_def: Optional[CoupBH] = None

    confiance: float = 0.0
    texte_brut: str = ""
    scores: dict = field(default_factory=dict)
    deduits: set = field(default_factory=set)
    ignores: list = field(default_factory=list)   # valeurs hors branche

    # --- delegation a l'arbre ---

    def est_complete(self, roster=None) -> bool:
        return arbre.est_complete(self, roster)

    def slot_attendu(self, roster=None) -> Optional[str]:
        return arbre.slot_attendu(self, roster)

    def noeud_attendu(self, roster=None):
        return arbre.noeud_courant(self, roster)

    def type_coup_id(self, suffixe: str = "") -> Optional[str]:
        return arbre.identifiant_coup(self, suffixe)

    def slots_resolus(self) -> dict:
        return {slot: getattr(self, slot) for slot in SLOTS
                if getattr(self, slot) is not None}


@dataclass
class Commande:
    """Un enonce de controle. Ne passe jamais par l'arbre."""

    nom: str
    texte_brut: str = ""


def parser(texte: str, roster=None, base: Optional[Intention] = None,
           confiance_acoustique: float = 0.0, seuil: int = 80):
    """Enonce -> `Commande` ou `Intention`.

    `base` est l'intention en cours quand on complete un enonce partiel :
    les slots deja resolus sont conserves, et seuls ceux que l'arbre attend
    encore sont cherches dans le texte.
    """
    # 1. Commande de controle : court-circuit, on n'entre pas dans l'arbre.
    commande = extraction.commande_de_controle(texte, seuil)
    if commande is not None:
        return Commande(nom=commande, texte_brut=texte)

    intention = replace(base) if base is not None else Intention()
    intention.texte_brut = texte
    intention.scores = dict(base.scores) if base else {}
    intention.deduits = set(base.deduits) if base else set()
    intention.ignores = []

    # 2. Restreindre la recherche a ce que l'arbre attend encore.
    applicables = arbre.slots_applicables(intention, roster)
    dejà_resolus = set(intention.slots_resolus())
    cherches = applicables - dejà_resolus

    # 3. Expressions composees, avant l'extraction slot a slot.
    texte_normalise = normaliser(texte)
    composes = _appliquer_composes(texte_normalise, cherches)

    # 4. Extraction, puis affectation attaquant / defenseur par ordre.
    trouvailles = extraction.extraire(
        texte_normalise, slots=cherches, roster=roster, seuil=seuil)
    affectations = extraction.repartir(trouvailles, ouverts=cherches)

    candidats = dict(composes)
    for slot, trouvaille in affectations.items():
        candidats[slot] = (trouvaille.valeur, trouvaille.score)

    # 5. Poser les valeurs, en refusant tout ce qui sort de la branche.
    _poser(intention, candidats, roster)

    # 6. Inference ascendante, puis nouvelle passe : un slot deduit peut
    #    rendre applicable un slot qui ne l'etait pas.
    _deduire(intention, roster)
    _poser(intention, candidats, roster)

    intention.confiance = _confiance(intention, confiance_acoustique)
    return intention


# --------------------------------------------------------------------------


def _appliquer_composes(texte_normalise: str, cherches: set) -> dict:
    """Un n-gramme qui renseigne plusieurs slots d'un coup.

    Seul mecanisme autorise a le faire, et il reste declaratif.
    """
    candidats = {}
    for expression, slots in vocabulaire.COMPOSES.items():
        if normaliser(expression) in texte_normalise:
            for slot, valeur in slots.items():
                if slot in cherches:
                    candidats[slot] = (valeur, 100.0)
    return candidats


def _poser(intention: Intention, candidats: dict, roster) -> None:
    """Ecrit les valeurs admissibles, ignore les autres.

    Deux filtres, dans cet ordre :
      - le slot doit etre applicable (C3, C4 — la branche existe-t-elle ?)
      - la valeur doit etre admise (C1, C2 — le roster l'autorise-t-il ?)

    Une valeur rejetee n'est jamais stockee en silence : elle est notee dans
    `ignores`, et son slot redevient la question posee.
    """
    # Placer, puis rendre au defenseur ce qui ne peut pas etre a l'attaquant,
    # puis replacer. Deux tours suffisent : une valeur migree ne migre plus.
    for _ in range(2):
        _placer(intention, candidats, roster)
        if not _migrer_vers_defenseur(intention, candidats, roster):
            break

    # Ce qui reste n'a jamais ete applicable : hors branche.
    applicables = arbre.slots_applicables(intention, roster)
    for slot in list(candidats):
        if getattr(intention, slot) is None and slot not in applicables:
            valeur, _ = candidats.pop(slot)
            intention.ignores.append((slot, valeur, "hors branche"))


def _migrer_vers_defenseur(intention: Intention, candidats: dict,
                           roster) -> bool:
    """Rend au defenseur un coup qui ne peut pas appartenir a l'attaquant.

    « premier cite = attaquant » (§3.5) ne suffit pas quand le coup de
    l'attaquant est terminal. Dans « faute provoquee joueur un SERVICE
    joueur quatre fond de court REVERS », il n'y a qu'un seul `type_coup`
    cite : la regle d'ordre l'attribuait a l'attaquant, dont la branche
    `service` n'admet aucun type de coup, et il etait jete.

    L'arbre tranche mieux que l'ordre : si le slot de l'attaquant n'est pas
    applicable et que celui du defenseur l'est, la valeur lui revient.
    """
    applicables = arbre.slots_applicables(intention, roster)
    migre = False

    for slot in list(candidats):
        if slot.endswith("_def") or getattr(intention, slot) is not None:
            continue
        if slot in applicables:
            continue

        cible = f"{slot}_def"
        if (cible in applicables and cible not in candidats
                and getattr(intention, cible) is None):
            candidats[cible] = candidats.pop(slot)
            migre = True

    return migre


def _placer(intention: Intention, candidats: dict, roster) -> None:
    """Une passe de placement, slot par slot, tant qu'elle progresse."""
    for _ in range(len(SLOTS)):
        applicables = arbre.slots_applicables(intention, roster)
        progres = False

        for slot in SLOTS:
            if slot not in candidats or getattr(intention, slot) is not None:
                continue

            valeur, score = candidats[slot]

            if slot not in applicables:
                continue        # peut-etre applicable plus tard

            admises = arbre.valeurs_admises(intention, slot, roster)
            if admises is not None and valeur not in admises:
                intention.ignores.append((slot, valeur, "valeur non admise"))
                del candidats[slot]
                progres = True
                break

            setattr(intention, slot, valeur)
            intention.scores[slot] = score
            progres = True
            break

        if not progres:
            break


def _deduire(intention: Intention, roster) -> None:
    """Remonte l'arbre depuis les slots resolus."""
    for suffixe in ("", "_def"):
        avec_service = suffixe == ""
        deduits = arbre.deduire_coup(intention, suffixe, avec_service)
        for slot, valeur in deduits.items():
            if getattr(intention, slot) is None:
                setattr(intention, slot, valeur)
                intention.deduits.add(slot)


def _confiance(intention: Intention, acoustique: float) -> float:
    """Moitie acoustique, moitie qualite des correspondances.

    Les slots deduits n'entrent pas dans la moyenne : ils n'ont pas ete
    entendus, donc ils n'ont pas de score propre.
    """
    scores = [s for slot, s in intention.scores.items()
              if slot not in intention.deduits]
    if not scores:
        return 0.0
    fuzzy = sum(scores) / len(scores) / 100.0
    return round(0.5 * acoustique + 0.5 * fuzzy, 4)
