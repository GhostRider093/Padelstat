"""
Encart de rappel : ce qu'on peut dire, et ce qu'on attend.

Le contenu est **derive de l'arbre et du vocabulaire**, jamais ecrit a la
main : ajouter un coup dans `arbre.py` le fait apparaitre ici sans toucher a
ce fichier. Un aide-memoire qui ment est pire que pas d'aide-memoire.

Le niveau attendu est mis en evidence pendant la completion progressive.
"""

from __future__ import annotations

import tkinter as tk

from app.voice import arbre, vocabulaire

FOND = "#12151a"
FOND_LIGNE = "#1a1f27"
FOND_ACTIF = "#1e3a5f"
TITRE = "#6b7280"
TEXTE = "#cbd5e1"
ACTIF = "#22d3ee"
RESOLU = "#22c55e"


def _dit(table, valeur) -> str:
    """Le mot qu'on prononce pour une valeur canonique.

    Le premier synonyme fait foi : on dit « filet », on stocke `volee`.
    """
    synonymes = table.get(valeur) or []
    return str(synonymes[0]) if synonymes else str(valeur)


def lignes_du_rappel() -> list:
    """[(slot, titre, [mots prononcables])] — construit depuis l'arbre."""
    coup = arbre.COUP()
    fond = coup.branches["fond_de_court"]
    filet = coup.branches["volee"]

    bh_fond = fond.branches["balle_haute"]
    bh_filet = filet.branches["balle_haute"]
    seulement_au_fond = set(bh_fond.valeurs()) - set(bh_filet.valeurs())

    def bh(valeur):
        mot = _dit(vocabulaire.COUPS_BH, valeur)
        return f"{mot} *" if valeur in seulement_au_fond else mot

    return [
        ("type_point", "TYPE",
         [_dit(vocabulaire.TYPES_POINT, v) for v in arbre.RACINE.valeurs()]),
        ("joueur", "JOUEUR",
         [_dit(vocabulaire.JOUEURS, n) for n in (1, 2, 3, 4)]),
        ("zone", "ZONE",
         [_dit(vocabulaire.ZONES, v) for v in coup.valeurs()]),
        ("type_coup", "COUP",
         [_dit(vocabulaire.TYPES_COUP, v) for v in fond.valeurs()]),
        ("coup_bh", "BALLE HAUTE",
         [bh(v) for v in bh_fond.valeurs()]),
    ]


class ApercuArbre:
    """Petite fenetre de rappel, posee a cote de la principale."""

    def __init__(self, parent: tk.Misc, titre: str = "Commandes vocales"):
        self.fenetre = tk.Toplevel(parent)
        self.fenetre.title(titre)
        self.fenetre.configure(bg=FOND)
        self.fenetre.resizable(False, False)
        self.fenetre.attributes("-topmost", True)
        # Fermer l'encart ne doit pas fermer l'application.
        self.fenetre.protocol("WM_DELETE_WINDOW", self.cacher)

        self._lignes = {}
        self._construire()
        self._poser_a_cote(parent)

    # ----------------------------------------------------------- affichage

    def _construire(self):
        tk.Label(self.fenetre, text="Maintiens V et parle",
                 bg=FOND, fg=TITRE, font=("Segoe UI", 9)).pack(
                     anchor="w", padx=12, pady=(10, 8))

        for slot, titre, mots in lignes_du_rappel():
            cadre = tk.Frame(self.fenetre, bg=FOND_LIGNE)
            cadre.pack(fill="x", padx=8, pady=1)

            etiquette = tk.Label(cadre, text=titre, bg=FOND_LIGNE, fg=TITRE,
                                 font=("Segoe UI", 8, "bold"), width=12,
                                 anchor="w")
            etiquette.pack(side="left", padx=(8, 4), pady=5)

            valeurs = tk.Label(cadre, text=" · ".join(mots), bg=FOND_LIGNE,
                               fg=TEXTE, font=("Segoe UI", 10), anchor="w",
                               justify="left")
            valeurs.pack(side="left", pady=5)

            self._lignes[slot] = (cadre, etiquette, valeurs)

        tk.Label(self.fenetre, text="*  bajada : fond de court uniquement",
                 bg=FOND, fg=TITRE, font=("Segoe UI", 8)).pack(
                     anchor="w", padx=12, pady=(6, 2))

        self.etat = tk.Label(self.fenetre, text="", bg=FOND, fg=ACTIF,
                             font=("Segoe UI", 10, "bold"), wraplength=420,
                             justify="left", anchor="w")
        self.etat.pack(anchor="w", fill="x", padx=12, pady=(2, 10))

    def _poser_a_cote(self, parent):
        """A droite de la fenetre principale, sans la recouvrir."""
        try:
            parent.update_idletasks()
            x = parent.winfo_rootx() + parent.winfo_width() + 8
            y = parent.winfo_rooty() + 60
            self.fenetre.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        except Exception:
            pass

    # ------------------------------------------------------------ etat

    def maj(self, intention=None, slot_attendu=None, message="",
            couleur=None):
        """Met en evidence le niveau attendu, grise ce qui est deja resolu.

        `couleur` s'applique au message d'etat : elle sert a distinguer d'un
        coup d'oeil une annotation ecrite d'une question en attente.
        """
        resolus = set(intention.slots_resolus()) if intention else set()

        for slot, (cadre, etiquette, valeurs) in self._lignes.items():
            # Les slots du defenseur reutilisent les memes lignes.
            attendu = slot_attendu in (slot, f"{slot}_def")
            resolu = slot in resolus or f"{slot}_def" in resolus

            if attendu:
                fond, couleur = FOND_ACTIF, ACTIF
            elif resolu:
                fond, couleur = FOND_LIGNE, RESOLU
            else:
                fond, couleur = FOND_LIGNE, TEXTE

            cadre.configure(bg=fond)
            etiquette.configure(bg=fond, fg=ACTIF if attendu else TITRE)
            valeurs.configure(bg=fond, fg=couleur)

        self.etat.configure(text=message, fg=couleur or ACTIF)

    def montrer(self):
        try:
            self.fenetre.deiconify()
            self.fenetre.attributes("-topmost", True)
        except Exception:
            pass

    def cacher(self):
        try:
            self.fenetre.withdraw()
        except Exception:
            pass

    def basculer(self):
        try:
            if self.fenetre.state() == "withdrawn":
                self.montrer()
            else:
                self.cacher()
        except Exception:
            pass

    def fermer(self):
        try:
            self.fenetre.destroy()
        except Exception:
            pass
