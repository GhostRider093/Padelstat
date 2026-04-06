"""
Parseur de commandes vocales pour annotation de matchs de padel
Interprète le langage naturel en actions d'annotation
"""

import re
from typing import Optional, Dict, Tuple, List


class CommandParser:
    """Parse les commandes vocales en actions d'annotation"""
    
    def __init__(self, joueurs: List[str] = None):
        """
        Args:
            joueurs: Liste des noms de joueurs du match
        """
        self.joueurs = joueurs or []
        
        # Patterns de commandes (expressions régulières flexibles)
        self.patterns = {
            # Actions de base
            'nouveau_point': r'(nouveau point|point suivant|prochain point)',
            'annuler': r'(annuler|annule|supprime|efface|retour)',
            'sauvegarder': r'(sauvegarde|sauver|enregistre)',
            'rapport': r'(génère rapport|générer rapport|rapport|créer rapport)',
            
            # Types de points
            'faute_directe': r'faute directe',
            'point_gagnant': r'(point gagnant|gagnant)',
            'faute_provoquee': r'(faute provoquée|faute provoquee|provoquée|provoquee)',
            
            # Types de coups
            'service': r'service',
            'balle_haute': r'(balle haute|balles hautes)',
            'smash': r'(smash à plat|smash a plat|smash)',
            'vollee': r'(vollée|vollee|volley|volé|volée)',
            'bandeja': r'bandeja',
            'vibora': r'(víbora|vibora)',
            'coup_droit': r'(coup droit|drive|derecha)',
            'revers': r'(revers|backhand|revés)',
            'lob': r'(lob|globo)',
            'chiquita': r'chiquita',
            'amorti': r'amorti',
            'sortie_vitre': r'(sortie vitre|vitre|pared)',
            'contre_vitre': r'(contre vitre|contre pared)',
            'fond_de_court': r'(fond de court|fond)',
            
            # Zones
            'filet': r'(filet|red)',
            'milieu': r'(milieu|medio)',
            'fond': r'(fond|fondo)',
            
            # Diagonales
            'parallele': r'(parallèle|paralelo|long de ligne)',
            'croise': r'(croisé|cruzado|diagonal)',
            
            # Cœurs/Labels spéciaux
            'coeur_bandeja': r'(cœur bandeja|coeur bandeja|bandeja cœur|bandeja coeur)',
            'coeur_smash': r'(cœur smash|coeur smash|smash cœur|smash coeur)',
            'coeur_vibora': r'(cœur víbora|coeur vibora|víbora cœur|vibora coeur)',
            
            # Contrôle lecture
            'pause': r'(pause|stop|arrête)',
            'lecture': r'(lecture|play|reprend)',
            'retour': r'(retour|recule|en arrière)',
            'avance': r'(avance|en avant)',
        }
    
    def set_joueurs(self, joueurs: List[str]):
        """Mise à jour de la liste des joueurs"""
        self.joueurs = joueurs
    
    def normaliser_texte(self, texte: str) -> str:
        """Normalise le texte pour améliorer la reconnaissance - toutes les variantes"""
        texte = texte.lower().strip()
        
        # CATÉGORIES
        texte = texte.replace('points', 'point')
        texte = texte.replace('fautes', 'faute')
        texte = re.sub(r'\bfaut\b', 'faute', texte)
        texte = texte.replace('foot', 'faute')
        texte = texte.replace('ford', 'faute')
        texte = texte.replace('photos', 'faute')
        texte = texte.replace('phoque', 'faute')
        texte = texte.replace('fort', 'faute')
        
        # FAUTE PROVOQUÉE - Toutes les variantes possibles
        texte = texte.replace('faute provoqué', 'faute provoquée')
        texte = texte.replace('faute provoquer', 'faute provoquée')
        texte = texte.replace('faute de provoquer', 'faute provoquée')
        texte = texte.replace('faut provoquer', 'faute provoquée')
        texte = texte.replace('faut de provoquer', 'faute provoquée')
        texte = texte.replace('faut te provoquer', 'faute provoquée')
        texte = texte.replace('faute te provoquer', 'faute provoquée')
        texte = texte.replace('foot provoquer', 'faute provoquée')
        texte = texte.replace('foot de provoquer', 'faute provoquée')
        texte = texte.replace('foot te provoquer', 'faute provoquée')
        texte = texte.replace('foot pro ok', 'faute provoquée')
        texte = texte.replace('ford provoquer', 'faute provoquée')
        texte = texte.replace('ford de provoquer', 'faute provoquée')
        texte = texte.replace('phoque provoquer', 'faute provoquée')
        texte = texte.replace('phoque de provoquer', 'faute provoquée')
        texte = texte.replace('photos provoquer', 'faute provoquée')
        texte = texte.replace('photos de provoquer', 'faute provoquée')
        texte = texte.replace('fort provoquer', 'faute provoquée')
        texte = texte.replace('fort de provoquer', 'faute provoquée')
        texte = texte.replace('provoquer', 'faute provoquée')  # Fallback si juste "provoquer"
        
        # POINT GAGNANT
        texte = texte.replace('point gagnant', 'point gagnant')
        texte = texte.replace('points gagnant', 'point gagnant')
        texte = texte.replace('gagnant', 'point gagnant')
        
        # JOUEURS (corrections phonétiques critiques)
        texte = texte.replace('joueur 1', 'joueur1')
        texte = texte.replace('joueur un', 'joueur1')
        texte = texte.replace('jour 1', 'joueur1')
        texte = texte.replace('jour un', 'joueur1')
        texte = texte.replace('jours 1', 'joueur1')
        texte = texte.replace('joue un', 'joueur1')
        texte = texte.replace('genre un', 'joueur1')
        texte = texte.replace('joueur 2', 'joueur2')
        texte = texte.replace('joueur deux', 'joueur2')
        texte = texte.replace('joueur de', 'joueur2')  # 95% des cas !
        texte = texte.replace('joueurs de', 'joueur2')
        texte = texte.replace('joueur à un', 'joueur2')
        
        # TYPES DE COUPS
        texte = texte.replace('services', 'service')
        texte = texte.replace('volley', 'volée')
        texte = texte.replace('vollée', 'volée')
        texte = texte.replace('volleys', 'volée')
        texte = texte.replace('volets', 'volée')
        texte = texte.replace('volet', 'volée')
        texte = re.sub(r'\bvolé\b', 'volée', texte)
        texte = texte.replace('volley-ball hot', 'volée balle haute')  # Cas complexe
        texte = texte.replace('volley-ball', 'volée')
        texte = texte.replace('lobs', 'lob')
        texte = texte.replace('lobes', 'lob')
        texte = texte.replace('lots', 'lob')
        texte = texte.replace("l'aube", 'lob')
        texte = texte.replace("de l'aube", 'lob')
        texte = texte.replace('smashs', 'smash')
        texte = texte.replace('smach', 'smash')
        texte = re.sub(r'\bsmas\b', 'smash', texte)
        
        # DIRECTIONS
        texte = texte.replace('coup-droit', 'coup droit')
        texte = texte.replace('coudra', 'coup droit')
        texte = texte.replace('coudroy', 'coup droit')  # Correction phonétique
        texte = texte.replace('coupe droit', 'coup droit')
        texte = texte.replace('rêveur', 'revers')
        texte = texte.replace('rêve', 'revers')
        texte = texte.replace('rover', 'revers')
        texte = texte.replace('reverre', 'revers')
        
        # BALLE HAUTE
        texte = texte.replace('ball au', 'balle haute')
        texte = texte.replace('balle au', 'balle haute')
        texte = texte.replace('ballotte', 'balle haute')
        texte = texte.replace('ball hot', 'balle haute')
        texte = texte.replace('balot', 'balle haute')
        texte = texte.replace('balo', 'balle haute')
        texte = texte.replace('balles hautes', 'balle haute')
        
        # FOND DE COURT (corrections complexes en premier)
        texte = texte.replace('franco rover', 'fond de court revers')  # Cas spécial !
        texte = texte.replace('francos rover', 'fond de court revers')
        texte = texte.replace('fond de courbevoie', 'fond de court')  # Correction exotique
        texte = texte.replace('fond de couverts', 'fond de court')
        texte = texte.replace('fond de cour', 'fond de court')
        texte = texte.replace('fond de cours', 'fond de court')
        texte = texte.replace('fontenoy', 'fond de court')  # Correction phonétique
        texte = texte.replace('fontenois', 'fond de court')  # Correction phonétique
        texte = texte.replace('fin de cours', 'fond de court')
        texte = texte.replace('fond de courbe', 'fond de court')
        texte = texte.replace('fonds de court', 'fond de court')
        
        # Nettoyer espaces multiples
        while '  ' in texte:
            texte = texte.replace('  ', ' ')
        
        return texte.strip()
    
    def parse(self, text: str) -> Optional[Dict]:
        """
        Parse un texte transcrit en commande structurée
        HYBRIDE : Accepte commande complète en 1 fois OU partielle en plusieurs fois
        
        Args:
            text: Texte transcrit par Whisper
            
        Returns:
            Dictionnaire de commande ou None si non reconnu
            {
                'action': str,  # nouveau_point, annuler, etc.
                'joueur': str,  # nom du joueur
                'type_point': str,  # faute_directe, point_gagnant, etc.
                'type_coup': str,  # smash, vollee, etc.
                'zone': str,  # filet, milieu, fond
                'diagonale': str,  # parallele, croise
                'label': str,  # coeur_bandeja, etc.
            }
        """
        # Normaliser AVANT tout traitement
        text = self.normaliser_texte(text)
        
        # Structure de commande
        command = {
            'action': None,
            'joueur': None,
            'defenseur': None,  # Pour fautes provoquées
            'type_point': None,
            'type_coup': None,
            'zone': None,
            'diagonale': None,
            'label': None,
            'raw_text': text
        }
        
        # 1. Détecter l'action principale
        for action, pattern in self.patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                if action in ['nouveau_point', 'annuler', 'sauvegarder', 'rapport', 
                             'pause', 'lecture', 'retour', 'avance']:
                    command['action'] = action
                elif action in ['faute_directe', 'point_gagnant', 'faute_provoquee']:
                    command['type_point'] = action
                elif action in ['service', 'smash', 'vollee', 'bandeja', 'vibora', 'coup_droit',
                              'revers', 'lob', 'chiquita', 'amorti', 'sortie_vitre', 'contre_vitre',
                              'fond_de_court', 'balle_haute']:
                    command['type_coup'] = action
                elif action in ['filet', 'milieu', 'fond']:
                    command['zone'] = action
                elif action in ['parallele', 'croise']:
                    command['diagonale'] = action
                elif action.startswith('coeur_'):
                    command['label'] = action
        
        # 2. Détecter le(s) joueur(s)
        command['joueur'] = self._extract_joueur(text)
        
        # Pour les fautes provoquées, extraire aussi le défenseur
        if command.get('type_point') == 'faute_provoquee':
            joueurs_trouves = self._extract_all_joueurs(text)
            if len(joueurs_trouves) >= 2:
                command['joueur'] = joueurs_trouves[0]  # Attaquant
                command['defenseur'] = joueurs_trouves[1]  # Défenseur/Fautif
            elif len(joueurs_trouves) == 1:
                command['joueur'] = joueurs_trouves[0]
        
        # 3. Inférer l'action si pas explicite
        if not command['action']:
            if command['type_point'] or command['type_coup']:
                command['action'] = 'nouveau_point'
        
        # 4. Valider la commande
        if command['action'] or command['type_point'] or command['type_coup']:
            return command
        
        return None
    
    def _extract_joueur(self, text: str) -> Optional[str]:
        """
        Extrait le nom d'un joueur du texte
        
        Args:
            text: Texte à analyser
            
        Returns:
            Nom du joueur ou None
        """
        for joueur in self.joueurs:
            # Recherche insensible à la casse et flexible
            if re.search(r'\b' + re.escape(joueur.lower()) + r'\b', text, re.IGNORECASE):
                return joueur
        
        return None
    
    def _extract_all_joueurs(self, text: str) -> List[str]:
        """
        Extrait TOUS les joueurs trouvés dans le texte (dans l'ordre d'apparition)
        
        Args:
            text: Texte à analyser
            
        Returns:
            Liste des joueurs trouvés (dans l'ordre)
        """
        joueurs_trouves = []
        
        # Créer une liste de tuples (position, joueur)
        positions = []
        for joueur in self.joueurs:
            match = re.search(r'\b' + re.escape(joueur.lower()) + r'\b', text, re.IGNORECASE)
            if match:
                positions.append((match.start(), joueur))
        
        # Trier par position d'apparition
        positions.sort(key=lambda x: x[0])
        
        # Retourner les joueurs dans l'ordre
        return [joueur for pos, joueur in positions]
    
    def format_command(self, command: Dict) -> str:
        """
        Formate une commande en texte lisible
        
        Args:
            command: Dictionnaire de commande
            
        Returns:
            Description textuelle de la commande
        """
        if not command:
            return "Commande non reconnue"
        
        parts = []
        
        if command.get('action'):
            parts.append(f"Action: {command['action']}")
        
        if command.get('joueur'):
            parts.append(f"Joueur: {command['joueur']}")
        
        if command.get('defenseur'):
            parts.append(f"Défenseur: {command['defenseur']}")
        
        if command.get('type_point'):
            parts.append(f"Type: {command['type_point']}")
        
        if command.get('type_coup'):
            parts.append(f"Coup: {command['type_coup']}")
        
        if command.get('zone'):
            parts.append(f"Zone: {command['zone']}")
        
        if command.get('diagonale'):
            parts.append(f"Diagonale: {command['diagonale']}")
        
        if command.get('label'):
            parts.append(f"Label: {command['label']}")
        
        return " | ".join(parts) if parts else "Commande vide"
    
    def get_suggestions(self, partial_text: str) -> List[str]:
        """
        Génère des suggestions de commandes basées sur un texte partiel
        
        Args:
            partial_text: Début de commande
            
        Returns:
            Liste de suggestions
        """
        suggestions = []
        partial = partial_text.lower()
        
        # Suggestions d'actions
        if 'nou' in partial:
            suggestions.append("nouveau point")
        if 'ann' in partial:
            suggestions.append("annuler")
        if 'sau' in partial:
            suggestions.append("sauvegarder")
        if 'rap' in partial:
            suggestions.append("générer rapport")
        
        # Suggestions de types
        if 'fau' in partial:
            suggestions.append("faute directe")
            suggestions.append("faute provoquée")
        if 'gag' in partial or 'poi' in partial:
            suggestions.append("point gagnant")
        
        # Suggestions de coups
        if 'sma' in partial:
            suggestions.append("smash")
        if 'vol' in partial:
            suggestions.append("vollée")
        if 'ban' in partial:
            suggestions.append("bandeja")
        
        return suggestions[:5]  # Top 5
    
    def validate_command(self, command: Dict) -> Tuple[bool, str]:
        """
        VALIDATION STRICTE : Tous les champs obligatoires doivent être remplis
        
        Args:
            command: Dictionnaire de commande
            
        Returns:
            (valide: bool, message: str avec détails des champs manquants)
        """
        if not command or not command.get('action'):
            return False, "❌ Aucune action détectée"
        
        action = command['action']
        
        # Commandes simples qui ne nécessitent pas plus d'infos
        if action in ['annuler', 'sauvegarder', 'rapport', 'pause', 'lecture']:
            return True, "✅ Commande valide"
        
        # === VALIDATION STRICTE POUR NOUVEAU POINT ===
        if action == 'nouveau_point':
            missing_fields = []
            
            # 1. TYPE DE POINT OBLIGATOIRE
            if not command.get('type_point'):
                missing_fields.append("TYPE DE POINT (faute directe/point gagnant/faute provoquée)")
            
            # 2. JOUEUR OBLIGATOIRE
            if not command.get('joueur'):
                missing_fields.append("JOUEUR")
            
            # 3. TYPE DE COUP OBLIGATOIRE pour point gagnant
            if command.get('type_point') == 'point_gagnant':
                if not command.get('type_coup'):
                    missing_fields.append("TYPE DE COUP (service/volée/fond de court/balle haute/lob/amorti)")
                else:
                    # Si c'est une balle haute, vérifier le sous-type
                    if command.get('type_coup') == 'balle_haute':
                        # Vérifier qu'il y a un sous-type (smash/bandeja/víbora)
                        if not command.get('label'):
                            missing_fields.append("SOUS-TYPE BALLE HAUTE (smash/bandeja/víbora)")
            
            # 4. DEFENSEUR OBLIGATOIRE pour faute provoquée
            if command.get('type_point') == 'faute_provoquee':
                if not command.get('defenseur'):
                    missing_fields.append("DÉFENSEUR/FAUTIF")
            
            # Si des champs manquent, retourner le détail
            if missing_fields:
                error_msg = "⚠️ CHAMPS MANQUANTS: " + " | ".join(missing_fields)
                return False, error_msg
        
        return True, "✅ Commande complète"
    
    def get_missing_fields(self, command: Dict) -> List[str]:
        """
        Retourne la liste des champs manquants
        
        Returns:
            Liste des noms de champs manquants
        """
        if not command or not command.get('action'):
            return ["Action"]
        
        action = command['action']
        
        # Commandes simples
        if action in ['annuler', 'sauvegarder', 'rapport', 'pause', 'lecture']:
            return []
        
        # Nouveau point
        missing = []
        if action == 'nouveau_point':
            if not command.get('type_point'):
                missing.append("Type de point")
            if not command.get('joueur'):
                missing.append("Joueur")
            if command.get('type_point') == 'point_gagnant' and not command.get('type_coup'):
                missing.append("Type de coup")
            if command.get('type_point') == 'faute_provoquee' and not command.get('defenseur'):
                missing.append("Défenseur")
        
        return missing


# Exemples d'utilisation
if __name__ == "__main__":
    # Test du parser
    parser = CommandParser(joueurs=["Arnaud", "Pierre", "Thomas", "Lucas"])
    
    test_phrases = [
        "Nouveau point faute directe Arnaud",
        "Point gagnant smash Pierre",
        "Faute provoquée vollée Thomas",
        "Bandeja cœur Lucas",
        "Annuler dernier point",
        "Générer rapport",
        "Smash parallèle fond de court",
    ]
    
    print("=== Test du parseur de commandes ===\n")
    
    for phrase in test_phrases:
        print(f"📝 '{phrase}'")
        command = parser.parse(phrase)
        if command:
            print(f"   ✅ {parser.format_command(command)}")
            valid, msg = parser.validate_command(command)
            print(f"   {'✓' if valid else '✗'} {msg}")
        else:
            print("   ❌ Non reconnu")
        print()
