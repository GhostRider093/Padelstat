"""
Arbre du domaine d'annotation Padelstat.

Source de verite unique du module vocal : la structure d'un point annote,
les valeurs admises a chaque etape, et ce qui manque pour qu'une annotation
soit complete. Le parsing, la validation, la completion progressive et la
generation des libelles lisent tous cet arbre. Aucun ne le reimplemente.

Ce fichier ne connait ni texte, ni audio, ni vocabulaire. Il se teste seul.

Voir SPEC_MODULE_VOCAL_PTT_V2.md sections 3 et 7.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional


# --------------------------------------------------------------------------
# Structure
# --------------------------------------------------------------------------


@dataclass(eq=False)
class Noeud:
    """Une etape de l'arbre.

    Un noeud est soit *ferme* (`branches`), soit *ouvert* (`suivant`) :

    - ferme  : l'ensemble des valeurs est connu a l'avance, et la valeur
               retenue determine la suite du parcours.
    - ouvert : toute valeur du `domaine` mene au meme noeud suivant.
               Sert aux joueurs, dont les valeurs dependent du match.

    Une branche valant None termine l'arbre.
    """

    slot: str
    branches: Optional[dict] = None
    suivant: Optional["Noeud"] = None
    domaine: Optional[Callable] = None

    @property
    def est_ferme(self) -> bool:
        return self.branches is not None

    def valeurs(self) -> tuple:
        """Valeurs canoniques d'un noeud ferme. Vide si le noeud est ouvert."""
        return tuple(self.branches) if self.branches else ()

    def suite(self, valeur) -> Optional["Noeud"]:
        """Noeud suivant une fois `valeur` retenue. None = fin de l'arbre."""
        if self.branches is not None:
            return self.branches.get(valeur)
        return self.suivant

    def accepte(self, valeur, etat=None, roster=None) -> bool:
        """La valeur est-elle admise pour ce noeud, dans cet etat ?"""
        if self.branches is not None:
            return valeur in self.branches
        if self.domaine is not None:
            admises = self.domaine(etat, roster)
            return admises is None or valeur in admises
        return True


def _lire(etat, slot: str):
    """Lit un slot sur un dict ou sur un objet (Intention)."""
    if etat is None:
        return None
    if isinstance(etat, Mapping):
        return etat.get(slot)
    return getattr(etat, slot, None)


# --------------------------------------------------------------------------
# Domaines contextuels (C1, C2)
# --------------------------------------------------------------------------
#
# Un joueur est identifie par son rang dans le roster, de 1 a N.
# Le roster est une liste de dicts {nom, equipe, position} telle que la
# produit annotation_manager. Sans roster, aucune contrainte n'est appliquee.


def _equipe(roster, rang: int):
    """Equipe du joueur de rang `rang`, ou None si l'info manque."""
    if not roster or not (1 <= rang <= len(roster)):
        return None
    joueur = roster[rang - 1]
    return joueur.get("equipe") if isinstance(joueur, Mapping) else None


def tous_les_joueurs(etat, roster) -> Optional[set]:
    if not roster:
        return None
    return set(range(1, len(roster) + 1))


def equipe_adverse(etat, roster) -> Optional[set]:
    """Domaine du defenseur : C1 (pas soi-meme) + C2 (equipe adverse).

    Si le roster ne porte pas d'equipes, C2 est inapplicable et seule C1
    s'applique. C'est une degradation explicite, jamais un contournement
    silencieux : `roster_sans_equipes()` permet a l'appelant de prevenir.
    """
    if not roster:
        return None

    attaquant = _lire(etat, "joueur")
    if attaquant is None:
        return tous_les_joueurs(etat, roster)

    rangs = range(1, len(roster) + 1)
    equipe_attaquant = _equipe(roster, attaquant)

    if equipe_attaquant is None:
        return {r for r in rangs if r != attaquant}          # C1 seule

    return {
        r for r in rangs
        if r != attaquant                                     # C1
        and _equipe(roster, r) not in (None, equipe_attaquant)  # C2
    }


def roster_sans_equipes(roster) -> bool:
    """Vrai si C2 ne peut pas s'appliquer, faute d'equipes dans le roster."""
    if not roster:
        return True
    return any(_equipe(roster, r) is None for r in range(1, len(roster) + 1))


# --------------------------------------------------------------------------
# Le sous-arbre COUP
# --------------------------------------------------------------------------


def COUP(suffixe: str = "", avec_service: bool = True,
         suite: Optional[Noeud] = None) -> Noeud:
    """Instancie le sous-arbre decrivant un coup.

    `suffixe` distingue les instances : "" pour le coup principal,
    "_def" pour celui du defenseur d'une faute provoquee.
    `suite` est le noeud qui prend le relais une fois le coup complet.

    Deux contraintes sont structurelles, donc encodees ici plutot que
    verifiees a l'execution :

    - C3 : le defenseur ne sert pas, il subit  -> `avec_service=False`
    - C4 : la bajada se joue apres rebond au mur du fond, donc uniquement
           depuis le fond de court -> absente du sous-arbre de la volee
    """

    def _coup_bh(avec_bajada: bool) -> Noeud:
        valeurs = ["smash_plat", "vibora", "bandeja"]
        if avec_bajada:                                        # C4
            valeurs.append("bajada")
        return Noeud(f"coup_bh{suffixe}",
                     branches={v: suite for v in valeurs})

    def _type_coup(avec_bajada: bool) -> Noeud:
        return Noeud(f"type_coup{suffixe}", branches={
            "coup_droit": suite,
            "revers": suite,
            "balle_haute": _coup_bh(avec_bajada),
        })

    # `service` et `lob` sont des coups, pas des zones : ils se jouent
    # necessairement du fond de court, donc les rendre terminaux ici evite
    # de demander une position deja connue.
    #
    # `volee` reste la cle canonique de ce qui se prononce « filet ». Une
    # volee se joue forcement au filet : nommer la position suffit a la
    # designer, et « volee balle haute » — deux coups differents — cesse
    # d'etre prononcable. Voir vocabulaire.py.
    zones = {
        "lob": suite,
        "fond_de_court": _type_coup(avec_bajada=True),         # C4
        "volee": _type_coup(avec_bajada=False),                # C4
    }
    if avec_service:                                           # C3
        zones["service"] = suite

    return Noeud(f"zone{suffixe}", branches=zones)


# --------------------------------------------------------------------------
# L'arbre
# --------------------------------------------------------------------------

COUP_DEFENSEUR = COUP(suffixe="_def", avec_service=False)      # C3

RACINE = Noeud("type_point", branches={
    "point_gagnant": Noeud("joueur", domaine=tous_les_joueurs,
                           suivant=COUP()),

    "faute_directe": Noeud("joueur", domaine=tous_les_joueurs,
                           suivant=COUP()),

    # Le coup principal appartient toujours a `joueur`. Pour une faute
    # provoquee, `joueur` EST l'attaquant : pas de troisieme nom de slot.
    #
    # On decrit un joueur entierement avant de passer a l'autre :
    # attaquant + son coup, puis defenseur + son coup. Enchainer les deux
    # joueurs d'abord obligeait a retenir qui avait fait quoi.
    "faute_provoquee": Noeud(
        "joueur", domaine=tous_les_joueurs,
        suivant=COUP(suite=Noeud("defenseur",
                                 domaine=equipe_adverse,       # C1 + C2
                                 suivant=COUP_DEFENSEUR))),
})


# --------------------------------------------------------------------------
# Parcours
# --------------------------------------------------------------------------


def _parcours(etat, roster=None):
    """(noeuds resolus, premier noeud non resolu).

    Une valeur presente mais inadmissible n'est pas consommee : son noeud
    reste le noeud courant et redeviendra la question posee.
    """
    resolus = []
    noeud = RACINE

    while noeud is not None:
        valeur = _lire(etat, noeud.slot)
        if valeur is None or not noeud.accepte(valeur, etat, roster):
            return resolus, noeud
        resolus.append((noeud, valeur))
        noeud = noeud.suite(valeur)

    return resolus, None


def chemin(etat, roster=None) -> list:
    """Noeuds traverses tant que le slot est resolu."""
    resolus, _ = _parcours(etat, roster)
    return [noeud for noeud, _ in resolus]


def noeud_courant(etat, roster=None) -> Optional[Noeud]:
    """Premier noeud non resolu. None si l'intention est complete."""
    _, courant = _parcours(etat, roster)
    return courant


def est_complete(etat, roster=None) -> bool:
    return noeud_courant(etat, roster) is None


def slot_attendu(etat, roster=None) -> Optional[str]:
    """Le seul slot a demander. On ne pose jamais deux questions."""
    courant = noeud_courant(etat, roster)
    return courant.slot if courant else None


def valeurs_admises(etat, slot: str, roster=None) -> Optional[set]:
    """Valeurs acceptables pour `slot` dans cet etat.

    None = domaine non contraint (roster absent). Vide = slot inatteignable.
    C3 et C4 n'ont pas a etre testees ici : la branche n'existe pas.

    Le meme slot peut apparaitre sous plusieurs branches encore ouvertes —
    `coup_bh` existe sous le fond de court avec la bajada, et sous le filet
    sans elle. Tant que la zone n'est pas tranchee, les deux sont possibles,
    et le domaine est leur **union**. Retenir la premiere branche rencontree
    rejetterait « bajada » avant meme que l'inference ait pu deduire la zone.
    """
    admises = set()
    trouve = False

    for noeud in _noeuds_atteignables(etat, roster):
        if noeud.slot != slot:
            continue
        trouve = True
        if noeud.est_ferme:
            admises |= set(noeud.valeurs())
        elif noeud.domaine is not None:
            valeurs = noeud.domaine(etat, roster)
            if valeurs is None:
                return None
            admises |= set(valeurs)
        else:
            return None

    return admises if trouve else set()


def slots_applicables(etat, roster=None) -> set:
    """Slots atteignables depuis l'etat courant.

    Un slot hors de cet ensemble ne doit jamais etre renseigne : c'est ce
    qui fait qu'un « service coup droit » perd son type de coup au lieu de
    le stocker silencieusement.
    """
    return {noeud.slot for noeud in _noeuds_atteignables(etat, roster)}


def _noeuds_atteignables(etat, roster=None) -> list:
    """Noeuds deja resolus, puis tout ce qui reste accessible."""
    resolus, courant = _parcours(etat, roster)
    noeuds = [noeud for noeud, _ in resolus]

    vus = {id(n) for n in noeuds}
    pile = [courant] if courant is not None else []
    while pile:
        noeud = pile.pop()
        if noeud is None or id(noeud) in vus:
            continue
        vus.add(id(noeud))
        noeuds.append(noeud)
        if noeud.branches:
            pile.extend(noeud.branches.values())
        else:
            pile.append(noeud.suivant)

    return noeuds


# --------------------------------------------------------------------------
# Identifiants de coup
# --------------------------------------------------------------------------
#
# Le format reproduit celui de app/exports/type_coup_labels.py, pour rester
# compatible avec les matchs deja annotes. `smash_plat` s'ecrit `smash` dans
# l'identifiant : c'est la cle historique.

_ID_ZONE = {
    "service": "service",
    "lob": "lob",
    "fond_de_court": "fond_de_court",
    "volee": "volee",           # se prononce « filet », se stocke « volee »
}

_ID_TYPE_COUP = {"coup_droit": "CD", "revers": "R", "balle_haute": "BH"}

_ID_COUP_BH = {
    "smash_plat": "smash",
    "vibora": "vibora",
    "bandeja": "bandeja",
    "bajada": "bajada",
}


def identifiant_coup(etat, suffixe: str = "") -> Optional[str]:
    """'fond_de_court_BH_bajada', 'volee_CD', 'service', 'lob'.

    None tant que le coup est incomplet.
    """
    zone = _lire(etat, f"zone{suffixe}")
    if zone is None:
        return None
    if zone in ("service", "lob"):
        return _ID_ZONE[zone]

    type_coup = _lire(etat, f"type_coup{suffixe}")
    if type_coup is None:
        return None
    identifiant = f"{_ID_ZONE[zone]}_{_ID_TYPE_COUP[type_coup]}"
    if type_coup != "balle_haute":
        return identifiant

    coup_bh = _lire(etat, f"coup_bh{suffixe}")
    if coup_bh is None:
        return None
    return f"{identifiant}_{_ID_COUP_BH[coup_bh]}"


def chemins_coup(suffixe: str = "", avec_service: bool = True) -> list:
    """Tous les chemins complets du sous-arbre coup, sous forme d'etats.

    Enumere depuis l'arbre, jamais depuis une liste ecrite a la main. Sert
    a la fois aux identifiants et a l'inference ascendante.
    """
    racine = COUP(suffixe=suffixe, avec_service=avec_service)
    chemins = []

    for zone in racine.valeurs():
        etat = {f"zone{suffixe}": zone}
        noeud_tc = racine.branches[zone]

        if noeud_tc is None or noeud_tc.slot != f"type_coup{suffixe}":
            chemins.append(etat)
            continue

        for type_coup in noeud_tc.valeurs():
            etat_tc = dict(etat, **{f"type_coup{suffixe}": type_coup})
            noeud_bh = noeud_tc.branches[type_coup]

            if noeud_bh is None or noeud_bh.slot != f"coup_bh{suffixe}":
                chemins.append(etat_tc)
                continue

            for coup_bh in noeud_bh.valeurs():
                chemins.append(dict(etat_tc,
                                    **{f"coup_bh{suffixe}": coup_bh}))

    return chemins


def coups_terminaux(suffixe: str = "", avec_service: bool = True) -> set:
    """Tous les identifiants qu'un sous-arbre coup peut produire.

    C'est ce qui permet a type_coup_labels.py d'en etre derive plutot que
    maintenu a la main.
    """
    return {identifiant_coup(chemin, suffixe)
            for chemin in chemins_coup(suffixe, avec_service)}


def deduire_coup(etat, suffixe: str = "", avec_service: bool = True) -> dict:
    """Slots que les valeurs deja connues determinent a elles seules.

    Un slot profond contraint ses ancetres. Entendre « bajada » ne laisse
    qu'un seul chemin possible dans l'arbre : `type_coup` ET `zone` en
    decoulent, et l'intention est complete sans autre question. Entendre
    « bandeja » determine `type_coup=balle_haute`, mais laisse le choix
    entre filet et fond de court : `zone` reste la question posee.

    Gratuit avec un arbre, impossible avec des slots plats.
    """
    slots = [f"zone{suffixe}", f"type_coup{suffixe}", f"coup_bh{suffixe}"]
    connus = {slot: _lire(etat, slot) for slot in slots}
    connus = {slot: v for slot, v in connus.items() if v is not None}
    if not connus:
        return {}

    compatibles = [
        chemin for chemin in chemins_coup(suffixe, avec_service)
        if all(chemin.get(slot) == valeur for slot, valeur in connus.items())
    ]
    if not compatibles:
        return {}

    deduits = {}
    for slot in slots:
        if slot in connus:
            continue
        valeurs = {chemin.get(slot) for chemin in compatibles}
        if len(valeurs) == 1:
            valeur = valeurs.pop()
            if valeur is not None:
                deduits[slot] = valeur

    return deduits
