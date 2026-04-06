"""
Parseur de commandes vocales pour annotation de matchs de padel.
Interprète le langage naturel en actions structurées.

Structure hiérarchique (conforme SCHEMA_COUPS_HIERARCHIE.md) :

  TYPE_POINT  → JOUEUR(S)  → ZONE_FRAPPE  → TECHNIQUE  → COUP_FINAL
  ----------    ---------    -----------    ---------    ----------
  point_gagnant              service        —            —
  faute_directe              lob            —            —
  faute_provoquee            fond_de_court  coup_droit   —
                             volee          revers       —
                                            balle_haute  smash / bandeja / vibora

Champs produits par parse() :
  action       : nouveau_point | annuler | sauvegarder | rapport
               | pause | lecture | retour | avance
               | retour_2s | avance_2s | retour_10s | avance_10s
               | point_precedent | point_suivant
               | vitesse_lente | vitesse_normale | vitesse_rapide
               | review_vocal | stats | zoom_in | zoom_out
  joueur       : nom du joueur (attaquant / gagnant / fautif)
  defenseur    : nom du défenseur (faute provoquée)
  type_point   : faute_directe | point_gagnant | faute_provoquee
  zone_frappe  : service | fond_de_court | volee | lob      (niveau 3)
  technique    : coup_droit | revers | balle_haute           (niveau 4)
  coup_final   : smash | bandeja | vibora                    (niveau 5)
  type_coup    : compat — construit automatiquement depuis zone_frappe+technique+coup_final
  zone         : filet | milieu | fond  (position terrain)
  diagonale    : parallele | croise
  label        : coeur_bandeja | coeur_smash | coeur_vibora
  raw_text     : texte normalisé

API stable :
  CommandParser.parse(text) -> dict | None
  CommandParser.validate_command(command) -> (bool, str)
  CommandParser.get_missing_fields(command) -> list[str]
"""

import re
from typing import Optional, Dict, Tuple, List


class CommandParser:
    """Parse les commandes vocales en actions d'annotation"""

    def __init__(self, joueurs: Optional[List[str]] = None):
        self.joueurs = joueurs or []

        # --- Patterns TYPE DE POINT ---
        self._p_type_point = {
            "faute_provoquee": r"(faute provoquée|faute provoquee|provoquée|provoquee)",
            "faute_directe": r"faute directe",
            "point_gagnant": r"(point gagnant|gagnant\b)",
        }

        # --- Patterns ZONE DE FRAPPE (niveau 3) ---
        # Ordre important : fond_de_court AVANT fond (pour éviter match partiel)
        self._p_zone = {
            "fond_de_court": r"fond de court",
            "volee": r"(vollée|vollee|volley|volleys|volets|volet|volé|volée)\b",
            "lob": r"\b(lob|lobes|lobs|lots|l'aube|globo)\b",
            "service": r"\bservice\b",
        }

        # --- Patterns TECHNIQUE (niveau 4) ---
        self._p_technique = {
            "balle_haute": r"(balle haute|balles hautes|ball au|balle au|ballotte|ball hot|balot|balo)",
            "coup_droit": r"(coup droit|coup-droit|coudra|coudroy|coupe droit|drive|derecha)",
            "revers": r"(revers|rêveur|rêve\b|rover\b|reverre|reverts|backhand|revés)",
        }

        # --- Patterns COUP FINAL / sous-type balle haute (niveau 5) ---
        self._p_coup_final = {
            "smash": r"(smash à plat|smash a plat|smash|smach|smas\b)",
            "bandeja": r"bandeja",
            "vibora": r"(víbora|vibora)",
        }

        # --- Patterns LABELS (coeur) ---
        self._p_labels = {
            "coeur_bandeja": r"(cœur bandeja|coeur bandeja|bandeja cœur|bandeja coeur)",
            "coeur_smash": r"(cœur smash|coeur smash|smash cœur|smash coeur)",
            "coeur_vibora": r"(cœur víbora|coeur vibora|víbora cœur|vibora coeur)",
        }

        # --- Patterns ACTIONS SIMPLES ---
        self._p_actions = {
            # Annotations
            "annuler": r"(annuler|annule|supprime|efface|supprimer dernier|annuler dernier)",
            "sauvegarder": r"(sauvegarde|sauver|enregistre)",
            "rapport": r"(génère rapport|générer rapport|créer rapport|générer le rapport)",

            # Contrôle vidéo - sauts temporels précis
            "retour_10s": r"(retour 10|reculer 10|en arrière 10|-10)",
            "avance_10s": r"(avance 10|avancer 10|en avant 10|\+10)",
            "retour_2s": r"(retour 2|reculer 2|en arrière 2|-2)",
            "avance_2s": r"(avance 2|avancer 2|en avant 2|\+2)",

            # Navigation points
            "point_precedent": r"(point précédent|annotation précédente|précédent\b)",
            "point_suivant": r"(point suivant|prochain point|annotation suivante|suivant\b)",

            # Vitesse
            "vitesse_lente": r"(vitesse lente|ralentir|ralenti|demi-vitesse|x0\.5|0[.,]5)",
            "vitesse_normale": r"(vitesse normale|vitesse 1|normal|x1\b)",
            "vitesse_rapide": r"(vitesse rapide|accélérer|double vitesse|x2\b|x1\.5)",

            # Play / pause
            "pause": r"\b(pause|stop|arrête|arrêter)\b",
            "lecture": r"\b(lecture|play|reprend|reprendre|lancer)\b",

            # Déplacements génériques (si pas de durée précise)
            "retour": r"\b(recule|en arrière)\b",
            "avance": r"\b(avance|en avant)\b",

            # Affichages / stats
            "review_vocal": r"(review vocal|review|revoir vocal|correction vocale|revoir les erreurs)",
            "stats": r"\b(stats|statistiques|afficher stats|voir stats|tableau de bord)\b",
            "zoom_in": r"(zoom avant|agrandir|zoom\+)",
            "zoom_out": r"(zoom arrière|réduire|zoom-)",
        }

        # --- Patterns ZONE terrain (position, pas frappe) ---
        self._p_zone_terrain = {
            "filet": r"(filet|red|au filet)",
            "milieu": r"\b(milieu|medio)\b",
            "fond_terrain": r"\b(fond du terrain|fond terrain)\b",
        }

        # --- Patterns DIAGONALE ---
        self._p_diagonale = {
            "parallele": r"(parallèle|paralelo|long de ligne)",
            "croise": r"(croisé|cruzado|diagonal)",
        }

    def set_joueurs(self, joueurs: List[str]):
        self.joueurs = joueurs

    # ------------------------------------------------------------------
    # Normalisation
    # ------------------------------------------------------------------
    def normaliser_texte(self, texte: str) -> str:
        """
        Normalise le texte STT (corrections phonétiques + variantes FR).
        Doit être appelé AVANT parse().
        """
        texte = texte.lower().strip()

        # CATÉGORIES
        texte = texte.replace("points", "point")
        texte = texte.replace("fautes", "faute")
        texte = re.sub(r"\bfaut\b", "faute", texte)  # évite de corrompre 'faute' → 'fautee'
        texte = texte.replace("foot", "faute")
        texte = texte.replace("ford", "faute")
        texte = texte.replace("photos", "faute")
        texte = texte.replace("phoque", "faute")
        texte = texte.replace("fort", "faute")

        # FAUTE PROVOQUÉE - variantes
        texte = texte.replace("faute provoqué", "faute provoquée")
        texte = texte.replace("faute provoquer", "faute provoquée")
        texte = texte.replace("faute de provoquer", "faute provoquée")
        texte = texte.replace("faut provoquer", "faute provoquée")
        texte = texte.replace("faut de provoquer", "faute provoquée")
        texte = texte.replace("faut te provoquer", "faute provoquée")
        texte = texte.replace("faute te provoquer", "faute provoquée")
        texte = texte.replace("foot provoquer", "faute provoquée")
        texte = texte.replace("foot de provoquer", "faute provoquée")
        texte = texte.replace("foot te provoquer", "faute provoquée")
        texte = texte.replace("foot pro ok", "faute provoquée")
        texte = texte.replace("ford provoquer", "faute provoquée")
        texte = texte.replace("ford de provoquer", "faute provoquée")
        texte = texte.replace("phoque provoquer", "faute provoquée")
        texte = texte.replace("phoque de provoquer", "faute provoquée")
        texte = texte.replace("photos provoquer", "faute provoquée")
        texte = texte.replace("photos de provoquer", "faute provoquée")
        texte = texte.replace("fort provoquer", "faute provoquée")
        texte = texte.replace("fort de provoquer", "faute provoquée")
        texte = texte.replace("provoquer", "faute provoquée")

        # POINT GAGNANT
        texte = texte.replace("points gagnant", "point gagnant")
        texte = texte.replace("gagnant", "point gagnant")

        # JOUEURS (corrections phonétiques)
        texte = texte.replace("joueur 1", "joueur1")
        texte = texte.replace("joueur un", "joueur1")
        texte = texte.replace("jour 1", "joueur1")
        texte = texte.replace("jour un", "joueur1")
        texte = texte.replace("jours 1", "joueur1")
        texte = texte.replace("joue un", "joueur1")
        texte = texte.replace("genre un", "joueur1")
        texte = texte.replace("joueur 2", "joueur2")
        texte = texte.replace("joueur deux", "joueur2")
        texte = texte.replace("joueur de", "joueur2")
        texte = texte.replace("joueurs de", "joueur2")
        texte = texte.replace("joueur à un", "joueur2")

        # TYPES DE COUPS
        texte = texte.replace("services", "service")
        # Cas complexes en premier (avant les remplacements simples)
        texte = texte.replace("volley-ball hot", "volée balle haute")
        texte = texte.replace("volley-ball", "volée")
        texte = texte.replace("volleys", "volée")
        texte = texte.replace("vollée", "volée")
        texte = texte.replace("volets", "volée")
        texte = texte.replace("volet", "volée")
        texte = texte.replace("volley", "volée")
        texte = re.sub(r"\bvolé\b", "volée", texte)  # évite de corrompre 'volée' → 'voléee'
        texte = texte.replace("lobs", "lob")
        texte = texte.replace("lobes", "lob")
        texte = texte.replace("lots", "lob")
        texte = texte.replace("l'aube", "lob")
        texte = texte.replace("de l'aube", "lob")
        texte = texte.replace("smashs", "smash")
        texte = texte.replace("smach", "smash")
        texte = re.sub(r"\bsmas\b", "smash", texte)  # évite de corrompre 'smash' → 'smashh'

        # DIRECTIONS
        texte = texte.replace("coup-droit", "coup droit")
        texte = texte.replace("coudra", "coup droit")
        texte = texte.replace("coudroy", "coup droit")
        texte = texte.replace("coupe droit", "coup droit")
        texte = texte.replace("rêveur", "revers")
        texte = texte.replace("rêve", "revers")
        texte = texte.replace("rover", "revers")
        texte = texte.replace("reverre", "revers")

        # BALLE HAUTE
        texte = texte.replace("ball au", "balle haute")
        texte = texte.replace("balle au", "balle haute")
        texte = texte.replace("ballotte", "balle haute")
        texte = texte.replace("ball hot", "balle haute")
        texte = texte.replace("balot", "balle haute")
        texte = texte.replace("balo", "balle haute")
        texte = texte.replace("balles hautes", "balle haute")

        # FOND DE COURT
        texte = texte.replace("franco rover", "fond de court revers")
        texte = texte.replace("francos rover", "fond de court revers")
        texte = texte.replace("fond de courbevoie", "fond de court")
        texte = texte.replace("fond de couverts", "fond de court")
        texte = texte.replace("fond de cour", "fond de court")
        texte = texte.replace("fond de cours", "fond de court")
        texte = texte.replace("fontenoy", "fond de court")
        texte = texte.replace("fontenois", "fond de court")
        texte = texte.replace("fin de cours", "fond de court")
        texte = texte.replace("fond de courbe", "fond de court")
        texte = texte.replace("fonds de court", "fond de court")

        while "  " in texte:
            texte = texte.replace("  ", " ")

        return texte.strip()

    def parse(self, text: str) -> Optional[Dict]:
        """
        Parse un texte STT en commande structurée (hiérarchique 5 niveaux).

        Retourne un dict ou None si rien n'est détectable.
        """
        text = self.normaliser_texte(text)

        command: Dict = {
            "action": None,
            "joueur": None,
            "defenseur": None,
            "type_point": None,
            "zone_frappe": None,   # service | fond_de_court | volee | lob
            "technique": None,     # coup_droit | revers | balle_haute
            "coup_final": None,    # smash | bandeja | vibora
            "type_coup": None,     # compat backward (calculé en fin de parse)
            "zone": None,          # position terrain: filet | milieu | fond_terrain
            "diagonale": None,
            "label": None,
            "raw_text": text,
        }

        # ── 1. Actions simples (contrôle vidéo / stats / gestion) ──────
        # On utilise un ordre précis: les patterns les plus spécifiques d'abord.
        for action, pattern in self._p_actions.items():
            if re.search(pattern, text, re.IGNORECASE):
                command["action"] = action
                break  # on prend la première qui matche

        # ── 2. Type de point ────────────────────────────────────────────
        # faute_provoquee AVANT faute_directe (ordre regex critique)
        for tp, pattern in self._p_type_point.items():
            if re.search(pattern, text, re.IGNORECASE):
                command["type_point"] = tp
                break

        # ── 3. Joueur(s) ────────────────────────────────────────────────
        if command.get("type_point") == "faute_provoquee":
            joueurs_trouves = self._extract_all_joueurs(text)
            if len(joueurs_trouves) >= 2:
                command["joueur"] = joueurs_trouves[0]
                command["defenseur"] = joueurs_trouves[1]
            elif joueurs_trouves:
                command["joueur"] = joueurs_trouves[0]
        else:
            command["joueur"] = self._extract_joueur(text)

        # ── 4. Zone de frappe (niveau 3) ────────────────────────────────
        for z, pattern in self._p_zone.items():
            if re.search(pattern, text, re.IGNORECASE):
                command["zone_frappe"] = z
                break

        # ── 5. Technique (niveau 4) — seulement si zone le permet ───────
        #    (fond_de_court ou volee obligatoire ; mais on parse même en l'absence
        #     pour permettre des commandes partielles type "volée coup droit")
        for t, pattern in self._p_technique.items():
            if re.search(pattern, text, re.IGNORECASE):
                command["technique"] = t
                break

        # ── 6. Coup final / sous-type balle haute (niveau 5) ────────────
        for cf, pattern in self._p_coup_final.items():
            if re.search(pattern, text, re.IGNORECASE):
                command["coup_final"] = cf
                break

        # ── 7. Labels cœur ───────────────────────────────────────────────
        for lbl, pattern in self._p_labels.items():
            if re.search(pattern, text, re.IGNORECASE):
                command["label"] = lbl
                break

        # ── 8. Zone terrain + diagonale ──────────────────────────────────
        for z, pattern in self._p_zone_terrain.items():
            if re.search(pattern, text, re.IGNORECASE):
                command["zone"] = z
                break
        for d, pattern in self._p_diagonale.items():
            if re.search(pattern, text, re.IGNORECASE):
                command["diagonale"] = d
                break

        # ── 9. Calcul type_coup (compat backward) ───────────────────────
        command["type_coup"] = self._build_type_coup(command)

        # ── 10. Inférer action "nouveau_point" si pas explicitée ─────────
        if not command["action"]:
            if command["type_point"] or command["zone_frappe"]:
                command["action"] = "nouveau_point"

        # ── 11. Retourner si on a au moins quelque chose ─────────────────
        if (command["action"] or command["type_point"]
                or command["zone_frappe"] or command["type_coup"]):
            return command

        return None

    @staticmethod
    def _build_type_coup(command: Dict) -> Optional[str]:
        """
        Construit un slug 'type_coup' pour la compatibilité backward
        depuis les champs hiérarchiques (zone_frappe / technique / coup_final).

        Exemples:
          zone_frappe=service                                → "service"
          zone_frappe=lob                                    → "lob"
          zone_frappe=fond_de_court, technique=coup_droit    → "fond_de_court_coup_droit"
          zone_frappe=volee, technique=balle_haute,
            coup_final=vibora                                → "volee_balle_haute_vibora"
        """
        zf = command.get("zone_frappe")
        t = command.get("technique")
        cf = command.get("coup_final")

        if not zf:
            # Pas de zone: si on a juste un coup_final ou technique, on retourne quand même
            if cf:
                if t:
                    return f"{t}_{cf}"
                return cf
            if t:
                return t
            return None

        if zf in ("service", "lob"):
            return zf

        # fond_de_court ou volee
        if not t:
            return zf
        if t != "balle_haute":
            return f"{zf}_{t}"
        # balle haute
        if cf:
            return f"{zf}_balle_haute_{cf}"
        return f"{zf}_balle_haute"


    def _extract_joueur(self, text: str) -> Optional[str]:
        for joueur in self.joueurs:
            if re.search(r"\b" + re.escape(joueur.lower()) + r"\b", text, re.IGNORECASE):
                return joueur
        return None

    def _extract_all_joueurs(self, text: str) -> List[str]:
        positions = []
        for joueur in self.joueurs:
            match = re.search(r"\b" + re.escape(joueur.lower()) + r"\b", text, re.IGNORECASE)
            if match:
                positions.append((match.start(), joueur))
        positions.sort(key=lambda x: x[0])
        return [joueur for _pos, joueur in positions]

    def format_command(self, command: Dict) -> str:
        """Formate une commande parsée en texte lisible (arbre)."""
        if not command:
            return "Commande non reconnue"

        parts = []
        if command.get("action"):
            parts.append(f"Action: {command['action']}")
        if command.get("type_point"):
            parts.append(f"Type: {command['type_point']}")
        if command.get("joueur"):
            parts.append(f"Joueur: {command['joueur']}")
        if command.get("defenseur"):
            parts.append(f"Défenseur: {command['defenseur']}")
        if command.get("zone_frappe"):
            parts.append(f"Zone frappe: {command['zone_frappe']}")
        if command.get("technique"):
            parts.append(f"Technique: {command['technique']}")
        if command.get("coup_final"):
            parts.append(f"Coup final: {command['coup_final']}")
        if command.get("type_coup"):
            parts.append(f"type_coup: {command['type_coup']}")
        if command.get("zone"):
            parts.append(f"Zone terrain: {command['zone']}")
        if command.get("diagonale"):
            parts.append(f"Diagonale: {command['diagonale']}")
        if command.get("label"):
            parts.append(f"Label: {command['label']}")

        return " | ".join(parts) if parts else "Commande vide"

    def validate_command(self, command: Dict) -> Tuple[bool, str]:
        """
        Validation stricte : tous les champs obligatoires selon le type de point.

        Règles :
          faute_directe  → type_point + joueur (coup optionnel)
          point_gagnant  → type_point + joueur + zone_frappe
                           si zone=fond_de_court|volee → + technique
                           si technique=balle_haute → + coup_final
          faute_provoquee → type_point + joueur (attaquant) + defenseur

        Les actions contrôle/stats ne nécessitent pas d'autres champs.
        """
        if not command or not command.get("action"):
            return False, "❌ Aucune action détectée"

        action = command["action"]

        # Actions simples → toujours valides
        _simples = {
            "annuler", "sauvegarder", "rapport",
            "pause", "lecture",
            "retour", "avance", "retour_2s", "avance_2s",
            "retour_10s", "avance_10s",
            "point_precedent", "point_suivant",
            "vitesse_lente", "vitesse_normale", "vitesse_rapide",
            "review_vocal", "stats", "zoom_in", "zoom_out",
        }
        if action in _simples:
            return True, "✅ Commande valide"

        if action == "nouveau_point":
            missing: List[str] = []

            if not command.get("type_point"):
                missing.append("TYPE DE POINT (faute directe / point gagnant / faute provoquée)")

            if not command.get("joueur"):
                missing.append("JOUEUR")

            tp = command.get("type_point")
            if tp == "point_gagnant":
                if not command.get("zone_frappe"):
                    missing.append("ZONE DE FRAPPE (service / fond de court / volée / lob)")
                else:
                    zf = command["zone_frappe"]
                    if zf in ("fond_de_court", "volee"):
                        if not command.get("technique"):
                            missing.append("TECHNIQUE (coup droit / revers / balle haute)")
                        elif command["technique"] == "balle_haute":
                            if not command.get("coup_final"):
                                missing.append("SOUS-TYPE BALLE HAUTE (smash / bandeja / víbora)")

            if tp == "faute_provoquee":
                if not command.get("defenseur"):
                    missing.append("DÉFENSEUR / FAUTIF")

            if missing:
                return False, "⚠️ CHAMPS MANQUANTS: " + " | ".join(missing)

        return True, "✅ Commande complète"

    def get_missing_fields(self, command: Dict) -> List[str]:
        """
        Retourne la liste des noms de champs manquants pour guider l'utilisateur.
        """
        if not command or not command.get("action"):
            return ["Action"]

        _simples = {
            "annuler", "sauvegarder", "rapport",
            "pause", "lecture",
            "retour", "avance", "retour_2s", "avance_2s",
            "retour_10s", "avance_10s",
            "point_precedent", "point_suivant",
            "vitesse_lente", "vitesse_normale", "vitesse_rapide",
            "review_vocal", "stats", "zoom_in", "zoom_out",
        }
        if command["action"] in _simples:
            return []

        missing = []
        if command["action"] == "nouveau_point":
            if not command.get("type_point"):
                missing.append("Type de point")
            if not command.get("joueur"):
                missing.append("Joueur")
            tp = command.get("type_point")
            if tp == "point_gagnant":
                if not command.get("zone_frappe"):
                    missing.append("Zone de frappe")
                elif command["zone_frappe"] in ("fond_de_court", "volee"):
                    if not command.get("technique"):
                        missing.append("Technique")
                    elif command["technique"] == "balle_haute" and not command.get("coup_final"):
                        missing.append("Sous-type balle haute")
            if tp == "faute_provoquee" and not command.get("defenseur"):
                missing.append("Défenseur")
        return missing

    def get_suggestions(self, partial_text: str) -> List[str]:
        suggestions = []
        partial = partial_text.lower()
        if "ann" in partial:
            suggestions.append("annuler")
        if "sau" in partial:
            suggestions.append("sauvegarder")
        if "rap" in partial:
            suggestions.append("générer rapport")
        if "fau" in partial:
            suggestions.append("faute directe")
            suggestions.append("faute provoquée")
        if "gag" in partial or "poi" in partial:
            suggestions.append("point gagnant")
        if "sma" in partial:
            suggestions.append("smash")
        if "vol" in partial:
            suggestions.append("volée coup droit")
        if "ban" in partial:
            suggestions.append("bandeja")
        return suggestions[:5]


# ---------------------------------------------------------------------------
# Tests rapides en ligne de commande
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = CommandParser(joueurs=["Arnaud", "Pierre", "Thomas", "Lucas"])

    cases = [
        # Annotations complètes
        ("faute directe Arnaud",                        True),
        ("point gagnant Pierre service",                True),
        ("point gagnant Thomas volée coup droit",       True),
        ("point gagnant Lucas fond de court revers",    True),
        ("point gagnant Arnaud volée balle haute smash", True),
        ("faute provoquée Arnaud Thomas volée revers",  True),
        # Annotations incomplètes
        ("point gagnant Arnaud",                        False),  # manque zone
        ("faute provoquée Arnaud",                      False),  # manque défenseur
        ("point gagnant Pierre volée balle haute",      False),  # manque sous-type
        # Contrôle vidéo
        ("pause",                                       True),
        ("lecture",                                     True),
        ("retour 10",                                   True),
        ("avance 2",                                    True),
        ("vitesse lente",                               True),
        ("review vocal",                                True),
        ("stats",                                       True),
        # Variantes phonétiques
        ("faute provoquer Arnaud Thomas volet coup droit", True),
        ("point gagnant Pierre volets ball au smash",  True),
    ]

    ok_count = 0
    for phrase, expected_valid in cases:
        cmd = parser.parse(phrase)
        valid, msg = parser.validate_command(cmd) if cmd else (False, "Non parsé")
        icon = "✅" if (valid == expected_valid) else "❌"
        ok_count += (1 if valid == expected_valid else 0)
        print(f"{icon} {repr(phrase)}")
        print(f"   type_coup={cmd.get('type_coup') if cmd else None} | "
              f"zone_frappe={cmd.get('zone_frappe') if cmd else None} | "
              f"technique={cmd.get('technique') if cmd else None} | "
              f"coup_final={cmd.get('coup_final') if cmd else None}")
        print(f"   valid={valid} | {msg}\n")

    print(f"Score: {ok_count}/{len(cases)}")
