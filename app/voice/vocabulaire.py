"""
Vocabulaire canonique du module vocal.

Seul endroit ou l'on ajoute du vocabulaire. Pas de `str.replace()`, pas de
table texte -> texte : un terme mal reconnu devient un synonyme d'une cle
canonique, ici et nulle part ailleurs.

Les cles sont celles de l'arbre. Ce que l'utilisateur PRONONCE et ce que
l'application STOCKE sont deux choses distinctes : on dit « filet », on
stocke `volee`, et les identifiants des matchs deja annotes sont preserves.

PROVENANCE DES SYNONYMES
    (m) mesure    releve sur les 89 captures de tests_audio/corpus_whisper,
                  faster-whisper `small`, GPU, avec biais de decodage.
    (h) hypothese non observe, ajoute par prudence. A confirmer ou retirer
                  a la prochaine campagne.

REGLE D'ADMISSION
    Une deformation n'entre ici que si elle ne risque pas de capturer un mot
    courant. « nouvelle » et « l'objet » ont ete mesures pour `lob`, mais
    sont refuses : trop generiques, ils declencheraient sur du bruit. Le vrai
    remede a ces cas est le biais de decodage contextuel, pas le synonyme.

Voir SPEC_MODULE_VOCAL_PTT_V2.md section 6.
"""

from __future__ import annotations


# --------------------------------------------------------------------------
# Type de point
# --------------------------------------------------------------------------

TYPES_POINT = {
    "point_gagnant": [
        "point gagnant",        # (m) 45/46
        "gagnant",
        "point",
        "winner",               # (h)
    ],
    "faute_directe": [
        "faute directe",        # (m) 15/16
        "faute",
        "erreur",               # (h)
    ],
    "faute_provoquee": [
        "faute provoquee",      # (m) 5/6
        "provoquee",
        "provoque",             # (h)
    ],
}


# --------------------------------------------------------------------------
# Zone de frappe
# --------------------------------------------------------------------------
#
# `service` et `lob` sont des coups, joues necessairement du fond de court.
# `volee` est la cle de ce qui se prononce « filet » : une volee se joue
# forcement au filet, donc nommer la position suffit. Dire « volee balle
# haute » etait une contradiction — deux coups differents — qu'aucun joueur
# de padel ne comprenait.

ZONES = {
    "service": [
        "service",              # (m) 9/10
        "services",             # (h) frequent en dictee
    ],
    "lob": [
        "lob",                  # (m) 9/11 en phrase, 0/2 isole
        "globo",                # (h) terme espagnol
        "lobe",                 # (h)
    ],
    "fond_de_court": [
        "fond de court",        # (m) 31/32
        "fond",
        "tour de court",        # (m)
    ],
    # Se prononce « filet ». Mesure : 9/10, contre 23/27 pour « volee », et
    # surtout sans jamais etre confondu avec un autre terme du domaine —
    # « volee » ressortait en « balle haute » et en « bandera ». La seule
    # erreur est une variante orthographique, que le fuzzy rattrape.
    "volee": [
        "filet",                # (m) 9/10
        "fillet",               # (m)
        "filets",               # (h)
    ],
}


# --------------------------------------------------------------------------
# Type de coup
# --------------------------------------------------------------------------

TYPES_COUP = {
    "coup_droit": [
        "coup droit",           # (m) 9/15 seulement
        "ou droit",             # (m)
        "pour droit",           # (m)
        "roue droit",           # (m)
        "bouroir",              # (m)
        "courant",              # (m)
        "drive",                # (h)
        "derecha",              # (h)
    ],
    "revers": [
        "revers",               # (m) 11/11, aucun echec
        "backhand",             # (h)
    ],
    "balle_haute": [
        "balle haute",          # (m) 29/31
        "balles hautes",        # (h)
    ],
}


# --------------------------------------------------------------------------
# Coups de balle haute
# --------------------------------------------------------------------------
#
# Les termes espagnols sont les plus fragiles du vocabulaire : ils n'existent
# pas dans le lexique francais du modele, qui les rabat sur des mots voisins.

COUPS_BH = {
    "smash_plat": [
        "smash",                # (m) 11/11, aucun echec
        "smash a plat",
        "smatch",               # (h)
    ],
    "vibora": [
        "vibora",               # (m) 8/10
        "vibra",                # (m)
        "vibro",                # (m)
    ],
    "bandeja": [
        "bandeja",              # (m) 3/7 seulement
        "bandera",              # (m) x2
    ],
    "bajada": [
        "bajada",               # (m) 4/10 seulement, le pire du vocabulaire
        "barada",               # (m) x3
        "barana",               # (m)
        "parada",               # (m)
        "mahada",               # (m)
    ],
}


# --------------------------------------------------------------------------
# Joueurs
# --------------------------------------------------------------------------
#
# Tres fiables a la mesure : 75/76 en phrase. Les prenoms du roster sont
# injectes a l'execution comme synonymes supplementaires — ils changent a
# chaque match et n'ont donc rien a faire dans ce fichier.

#
# Le mot « joueur » ne figure PAS dans les synonymes, et c'est mesure :
# « joueur un » et « joueur deux » ont un WRatio de 80, exactement le seuil.
# Le prefixe commun noie la seule syllabe qui distingue les joueurs. On ne
# garde donc que la partie discriminante ; « joueur » est un mot vide, retire
# avant l'extraction. Dire « joueur trois » fonctionne toujours : le
# n-gramme « trois » suffit.

JOUEURS = {
    1: ["un", "1", "premier"],
    2: ["deux", "2", "deuxieme"],
    3: ["trois", "3", "troisieme"],
    4: ["quatre", "4", "quatrieme"],
}

#: Mots sans valeur discriminante, retires avant l'extraction.
#: « joueur » y figure pour la raison ci-dessus, pas par commodite.
#:
#: `de`, `et` et `a` sont mesures : Whisper insere des liaisons parasites
#: — « filet DE balle haute », « balle haute ET vibora », « joueur A un ».
#:
#: ATTENTION : ces mots apparaissent aussi DANS des synonymes (« fond de
#: court », « ou droit »). Le filtrage doit donc s'appliquer des deux cotes,
#: texte ET synonymes, sinon « fond de court » cesserait de matcher. C'est
#: une contrainte sur normalizer.py, pas une option.
MOTS_VIDES = [
    "joueur", "joueurs", "le", "la", "les", "du", "des", "de", "et",
    "pour", "sur", "c est", "ca", "a", "en",
]


# --------------------------------------------------------------------------
# Commandes de controle
# --------------------------------------------------------------------------
#
# Hors arbre : reconnues en amont, elles court-circuitent le parsing.

# --------------------------------------------------------------------------
# Marqueurs de role
# --------------------------------------------------------------------------
#
# Dans une faute provoquee, deux joueurs et deux coups cohabitent. Sans
# marqueur, seul l'ordre les distingue (§3.5) : le premier cite est
# l'attaquant. Nommer le role explicitement libere completement l'ordre —
# « faute provoquee defenseur joueur quatre fond de court revers attaquant
# joueur un service » devient aussi valide que l'inverse.
#
# Les marqueurs sont optionnels : sans eux, la regle d'ordre s'applique.

ROLES = {
    "attaquant": ["attaquant", "attaque", "attaquer"],
    "defenseur": ["defenseur", "defense", "defenseur subit"],
}


CONTROLE = {
    "annuler": [
        "annuler",              # (m) 2/2
        "annule",
        "supprime",             # (h)
        "efface",               # (h)
    ],
}


# --------------------------------------------------------------------------
# Expressions composees
# --------------------------------------------------------------------------
#
# Seul mecanisme autorise a renseigner plusieurs slots depuis un seul
# n-gramme, et il reste declaratif. Applique avant l'extraction slot a slot.

COMPOSES = {
    # (m) mesure : « volee balle haute » -> « volleyball haute ». Le meme
    # piege figurait dans les releves Google Speech de 2025 sous la forme
    # « volley-ball hot ». Deux moteurs, trois ans d'ecart, meme collision.
    "volleyball haute": {"zone": "volee", "type_coup": "balle_haute"},
    "volley ball haute": {"zone": "volee", "type_coup": "balle_haute"},
}


# --------------------------------------------------------------------------
# Acces
# --------------------------------------------------------------------------

#: slot de l'arbre -> table des synonymes
TABLES = {
    "type_point": TYPES_POINT,
    "zone": ZONES,
    "type_coup": TYPES_COUP,
    "coup_bh": COUPS_BH,
    "joueur": JOUEURS,
    "defenseur": JOUEURS,
}

# Les slots du defenseur partagent le vocabulaire du coup principal.
for _slot, _table in list(TABLES.items()):
    if _slot in ("zone", "type_coup", "coup_bh"):
        TABLES[f"{_slot}_def"] = _table


def synonymes(slot: str) -> dict:
    """Table {valeur canonique: [synonymes]} pour un slot de l'arbre."""
    return TABLES.get(slot, {})


def toutes_les_entrees():
    """Itere (slot, valeur canonique, synonyme) sur tout le vocabulaire.

    Sert aux tests de collision : deux cles distinctes ne doivent pas
    porter de synonymes trop proches.
    """
    vus = set()
    for slot, table in TABLES.items():
        # `defenseur` et les slots `_def` reutilisent la table du slot
        # principal : les parcourir deux fois ferait passer un partage
        # delibere pour un conflit.
        if slot == "defenseur" or slot.endswith("_def"):
            continue
        for valeur, liste in table.items():
            for synonyme in liste:
                cle = (slot, valeur, synonyme)
                if cle not in vus:
                    vus.add(cle)
                    yield cle


def termes_du_noeud(noeud) -> list:
    """Tous les termes prononcables pour un noeud de l'arbre.

    Sert a construire un biais de decodage contextuel : en attente d'un
    slot, on ne propose au moteur que les valeurs que ce noeud admet.
    """
    table = synonymes(noeud.slot)
    if not table:
        return []
    valeurs = noeud.valeurs() or table.keys()
    termes = []
    for valeur in valeurs:
        termes.extend(str(t) for t in table.get(valeur, []))
    return termes
