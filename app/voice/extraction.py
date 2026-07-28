"""
Extraction des valeurs presentes dans un enonce.

Trouve *ce qui a ete dit*. C'est `parser.py` qui decide ensuite *ce que ca
veut dire* selon l'arbre. Les deux se testent separement.

Principe : n-grammes du plus long au plus court, fuzzy matching, et
consommation des tokens retenus. Un mot ne peut alimenter qu'un seul slot.

Voir SPEC_MODULE_VOCAL_PTT_V2.md section 7.2.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from rapidfuzz import fuzz, process

#: `ratio` et non `WRatio`. WRatio fait du *partial matching* : « on » obtient
#: 90 contre « fond » parce qu'il en est une sous-chaine, et un enonce de
#: bruit se voyait attribuer une zone. `ratio` est une pure distance
#: d'edition — il rend des scores identiques sur toutes les deformations
#: mesurees (barada/bajada 83, bandera/bandeja 86, ou droit/coup droit 89)
#: et rejette « on »/« fond » a 67. Voir tests/voice/test_extraction.py.
SCORER = fuzz.ratio

from app.voice import vocabulaire
from app.voice.normalizer import ngrammes, normaliser, tokens

#: En deca de cet ecart entre les deux meilleures valeurs d'un meme slot,
#: on refuse de trancher. Mieux vaut une question qu'une annotation fausse.
ECART_AMBIGU = 5

#: Slots cherches dans le texte. Les variantes `_def` ne sont pas cherchees
#: separement : c'est l'ordre d'apparition qui les distingue (cf. §3.5).
SLOTS_CHERCHES = ("type_point", "joueur", "zone", "type_coup", "coup_bh")

#: Slot cherche -> slots de l'intention qu'il peut alimenter, dans l'ordre.
#: Le defenseur partage le vocabulaire du joueur mais porte un autre nom :
#: sans cette table, completer « joueur trois » apres le coup de l'attaquant
#: ne trouverait plus rien.
CIBLES = {
    "type_point": ("type_point",),
    "joueur": ("joueur", "defenseur"),
    "zone": ("zone", "zone_def"),
    "type_coup": ("type_coup", "type_coup_def"),
    "coup_bh": ("coup_bh", "coup_bh_def"),
}


@dataclass
class Trouvaille:
    slot: str
    valeur: object
    score: float
    debut: int          # position du premier token, pour ordonner
    longueur: int
    texte: str
    role: Optional[str] = None   # "attaquant" / "defenseur", si annonce

    @property
    def fin(self) -> int:
        return self.debut + self.longueur


# --------------------------------------------------------------------------
# Index du vocabulaire
# --------------------------------------------------------------------------
#
# Les synonymes sont normalises une fois pour toutes, avec la meme fonction
# que le texte. Sans ca, « fond de court » deviendrait « fond court » d'un
# cote seulement et cesserait de matcher.

def _indexer(table: dict) -> dict:
    """{nombre de mots: {forme normalisee: valeur canonique}}.

    L'indexation par longueur n'est pas une optimisation, c'est une
    correction. `WRatio` fait du *partial matching* : « fond court balle
    haute » obtient un score eleve contre « fond court » parce qu'il le
    contient. Combine a la priorite au n-gramme long, ce comportement
    faisait avaler « balle haute » par la zone.

    On ne compare donc qu'a longueur egale. Toutes les deformations
    mesurees s'y pretent : « bandera »/« bandeja », « roue droit »/« coup
    droit », « fillet »/« filet » ont le meme nombre de mots que leur cible.
    """
    par_longueur = {}
    for valeur, synonymes in table.items():
        for synonyme in synonymes:
            forme = normaliser(str(synonyme))
            if not forme:
                continue
            par_longueur.setdefault(len(forme.split()), {}).setdefault(
                forme, valeur)
    return par_longueur


def _construire_index() -> dict:
    index = {slot: _indexer(vocabulaire.synonymes(slot))
             for slot in SLOTS_CHERCHES}
    index["_controle"] = _indexer(vocabulaire.CONTROLE)
    index["_role"] = _indexer(vocabulaire.ROLES)
    return index


INDEX = _construire_index()


def index_avec_roster(roster) -> dict:
    """Copie de l'index enrichie des prenoms du match.

    Les prenoms changent a chaque match : ils n'ont rien a faire dans
    vocabulaire.py, mais tout a faire dans l'index d'execution.
    """
    if not roster:
        return INDEX

    index = {slot: {n: dict(formes) for n, formes in par_longueur.items()}
             for slot, par_longueur in INDEX.items()}
    for rang, joueur in enumerate(roster, start=1):
        nom = joueur.get("nom") if isinstance(joueur, dict) else joueur
        forme = normaliser(str(nom or ""))
        if not forme:
            continue
        formes = index["joueur"].setdefault(len(forme.split()), {})
        formes.setdefault(forme, rang)
    return index


# --------------------------------------------------------------------------
# Commandes de controle
# --------------------------------------------------------------------------


#: Au-dela, l'enonce decrit un point, pas une commande. « faute directe
#: deux » fait trois mots : on ne peut pas monter plus haut sans risquer
#: qu'un mot de controle prononce au milieu d'une annotation la detourne.
MOTS_MAX_CONTROLE = 3


def commande_de_controle(texte: str, seuil: int = 80) -> Optional[str]:
    """Reconnue en amont de l'arbre : elle court-circuite le parsing.

    On accepte l'enonce entier (« annuler ») comme un mot de controle isole
    dans un enonce court (« annuler le point », « on annule »). Sans ca, ces
    formulations naturelles partaient dans l'arbre — et « annuler le point »
    y trouvait « point », donc ouvrait un point gagnant au lieu d'annuler.
    """
    mots = tokens(texte)
    if not mots or len(mots) > MOTS_MAX_CONTROLE:
        return None

    index = INDEX["_controle"]

    # 1. L'enonce entier.
    formes = index.get(len(mots))
    if formes:
        resultat = process.extractOne(
            " ".join(mots), formes.keys(), scorer=SCORER)
        if resultat and resultat[1] >= seuil:
            return formes[resultat[0]]

    # 2. Un mot de controle isole dans un enonce court.
    formes = index.get(1)
    if formes:
        for mot in mots:
            resultat = process.extractOne(mot, formes.keys(), scorer=SCORER)
            if resultat and resultat[1] >= seuil:
                return formes[resultat[0]]

    return None


# --------------------------------------------------------------------------
# Extraction
# --------------------------------------------------------------------------


def extraire(texte: str, slots=None, roster=None, seuil: int = 80) -> list:
    """Toutes les valeurs reconnues, dans l'ordre d'apparition.

    `slots` restreint la recherche — en completion progressive, on ne
    cherche que ce que l'arbre attend encore.
    """
    mots = tokens(texte)
    if not mots:
        return []

    index = index_avec_roster(roster)
    cherches = [s for s in SLOTS_CHERCHES
                if slots is None
                or any(cible in slots for cible in CIBLES[s])]

    consommes = [False] * len(mots)

    # Les marqueurs de role d'abord : ils ne designent aucune valeur, mais
    # ils determinent a qui appartiennent celles qui suivent.
    marqueurs = _marqueurs_de_role(mots, consommes, seuil)

    trouvailles = []

    # Du plus long au plus court : « balle haute » doit gagner contre
    # « balle », « fond de court » contre « fond ».
    for debut, longueur, ngramme in ngrammes(mots):
        if any(consommes[debut:debut + longueur]):
            continue

        meilleure = _meilleure_valeur(ngramme, longueur, cherches,
                                      index, seuil)
        if meilleure is None:
            continue

        slot, valeur, score = meilleure
        trouvailles.append(Trouvaille(slot, valeur, score, debut, longueur,
                                      ngramme, _role_a(marqueurs, debut)))
        for i in range(debut, debut + longueur):
            consommes[i] = True

    trouvailles.sort(key=lambda t: t.debut)
    return trouvailles


def _marqueurs_de_role(mots: list, consommes: list, seuil: int) -> list:
    """[(position, role)] pour les mots qui annoncent explicitement un role.

    Les tokens correspondants sont consommes : « defenseur » ne doit pas
    aller nourrir un slot de l'arbre.
    """
    formes = INDEX["_role"].get(1) or {}
    if not formes:
        return []

    marqueurs = []
    for position, mot in enumerate(mots):
        if consommes[position]:
            continue
        resultat = process.extractOne(mot, formes.keys(), scorer=SCORER)
        if resultat and resultat[1] >= seuil:
            marqueurs.append((position, formes[resultat[0]]))
            consommes[position] = True
    return marqueurs


def _role_a(marqueurs: list, position: int) -> Optional[str]:
    """Le role annonce le plus recemment avant cette position."""
    role = None
    for debut, valeur in marqueurs:
        if debut > position:
            break
        role = valeur
    return role


def _meilleure_valeur(ngramme, longueur, slots, index, seuil):
    """(slot, valeur, score) du meilleur match, ou None.

    Un ecart trop faible entre les deux meilleures valeurs rend le n-gramme
    non concluant : on prefere ne rien retenir et poser la question.
    """
    candidats = []
    for slot in slots:
        formes = (index.get(slot) or {}).get(longueur)
        if not formes:
            continue
        resultats = process.extract(
            ngramme, formes.keys(), scorer=SCORER, limit=2)
        for forme, score, _ in resultats:
            candidats.append((score, slot, formes[forme]))

    if not candidats:
        return None

    candidats.sort(key=lambda c: -c[0])
    score, slot, valeur = candidats[0]
    if score < seuil:
        return None

    for autre_score, autre_slot, autre_valeur in candidats[1:]:
        if (autre_slot, autre_valeur) == (slot, valeur):
            continue
        if score - autre_score < ECART_AMBIGU:
            return None                      # ambigu : on ne devine pas
        break

    return slot, valeur, score


def repartir(trouvailles: list, ouverts=None) -> dict:
    """Affecte les trouvailles aux slots de l'intention, doublons compris.

    L'ordre est sans importance entre slots differents. Entre deux
    occurrences d'un MEME slot, l'ordre d'apparition tranche : la premiere
    revient a l'attaquant, la seconde au defenseur. C'est deja la convention
    de l'ancien parseur, qui triait les joueurs par position dans la phrase.

    `ouverts` restreint aux slots encore a remplir. En completion
    progressive, « joueur trois » prononce apres le coup de l'attaquant
    doit alimenter `defenseur`, pas `joueur` qui est deja resolu.
    """
    par_slot = {}
    for trouvaille in trouvailles:
        par_slot.setdefault(trouvaille.slot, []).append(trouvaille)

    affectations = {}
    for slot, liste in par_slot.items():
        cibles = [c for c in CIBLES[slot]
                  if ouverts is None or c in ouverts]
        if not cibles:
            continue

        # Un role annonce l'emporte toujours sur l'ordre : dire
        # « defenseur joueur quatre » place le quatre en defense, meme s'il
        # est cite en premier.
        libres = list(cibles)
        sans_role = []

        for trouvaille in liste:
            cible = _cible_du_role(trouvaille.role, cibles)
            if cible is not None and cible in libres:
                affectations[cible] = trouvaille
                libres.remove(cible)
            else:
                sans_role.append(trouvaille)

        # Le reste garde la regle d'ordre d'apparition (§3.5).
        for trouvaille, cible in zip(sans_role, libres):
            affectations[cible] = trouvaille

    return affectations


def _cible_du_role(role, cibles) -> Optional[str]:
    """Slot correspondant a un role annonce, parmi les cibles disponibles."""
    if role is None:
        return None
    if role == "defenseur":
        return next((c for c in cibles if c.endswith("_def")
                     or c == "defenseur"), None)
    return next((c for c in cibles if not c.endswith("_def")
                 and c != "defenseur"), None)
