#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEST VOCAL ADAPTATIF - PADEL STAT
Système intelligent qui demande uniquement les informations manquantes
"""

import tkinter as tk
from tkinter import ttk
import speech_recognition as sr
import threading
import random
from datetime import datetime

class TestVocalAdaptatif:
    def __init__(self, root):
        self.root = root
        self.root.title("🎤 TEST VOCAL ADAPTATIF - PADEL STAT")
        self.root.geometry("1400x900")
        self.root.configure(bg="#1e1e1e")
        
        # Configuration joueurs
        self.joueurs = ["Pierre", "Lucas", "Marie", "Sophie"]
        
        # État de la commande en cours
        self.commande_en_cours = {
            'categorie': None,      # point, faute, faute_provoquee
            'joueur1': None,        # Pierre, Lucas, etc.
            'joueur2': None,        # Pour faute provoquée uniquement
            'type_coup': None,      # service, volee, fond_de_court, lob
            'direction': None,      # coup_droit, revers, balle_haute (si applicable)
        }
        
        # Statistiques
        self.stats = {
            "point": 0,
            "faute": 0,
            "faute_provoquee": 0,
            "total": 0
        }
        
        # Reconnaissance vocale
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.en_ecoute = False
        
        # Calibrage
        self.calibrer_micro()
        
        # Interface
        self.creer_interface()
        
    def calibrer_micro(self):
        """Calibre le microphone"""
        print("🎤 Calibrage du microphone...")
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
        print("✅ Calibrage terminé")
    
    def normaliser_texte(self, texte):
        """Normalise le texte"""
        texte = texte.lower().strip()
        
        # CATÉGORIES
        texte = texte.replace('points', 'point')
        texte = texte.replace('fautes', 'faute')
        texte = texte.replace('faut', 'faute')
        texte = texte.replace('foot', 'faute')
        texte = texte.replace('ford', 'faute')
        texte = texte.replace('photos', 'faute')
        texte = texte.replace('phoque', 'faute')
        
        # FAUTE PROVOQUÉE
        texte = texte.replace('faute provoqué', 'faute provoquée')
        texte = texte.replace('faute provoquer', 'faute provoquée')
        texte = texte.replace('faut provoquer', 'faute provoquée')
        texte = texte.replace('faut te provoquer', 'faute provoquée')
        texte = texte.replace('foot pro ok', 'faute provoquée')
        
        # JOUEURS (prénoms)
        for i, prenom in enumerate(self.joueurs, 1):
            texte = texte.replace(f'joueur {i}', prenom.lower())
            texte = texte.replace(f'joueur{i}', prenom.lower())
            texte = texte.replace(f'jour {i}', prenom.lower())
            texte = texte.replace(f'jours {i}', prenom.lower())
        
        # Variantes courantes
        texte = texte.replace('joueur un', self.joueurs[0].lower())
        texte = texte.replace('genre un', self.joueurs[0].lower())  # Pierre
        texte = texte.replace('joueur de', self.joueurs[1].lower())
        texte = texte.replace('joueur deux', self.joueurs[1].lower())
        
        # TYPES DE COUPS
        texte = texte.replace('services', 'service')
        texte = texte.replace('volley', 'volée')
        texte = texte.replace('volets', 'volée')
        texte = texte.replace('volet', 'volée')
        texte = texte.replace('lobs', 'lob')
        texte = texte.replace('lobes', 'lob')
        texte = texte.replace("l'aube", 'lob')
        
        # DIRECTIONS
        texte = texte.replace('coup-droit', 'coup droit')
        texte = texte.replace('coudra', 'coup droit')
        texte = texte.replace('rêveur', 'revers')
        texte = texte.replace('rêve', 'revers')
        texte = texte.replace('rover', 'revers')
        texte = texte.replace('ball au', 'balle haute')
        texte = texte.replace('ballotte', 'balle haute')
        texte = texte.replace('ball hot', 'balle haute')
        
        # FOND DE COURT
        texte = texte.replace('fond de cour', 'fond de court')
        texte = texte.replace('fond de cours', 'fond de court')
        texte = texte.replace('fin de cours', 'fond de court')
        texte = texte.replace('fond de courbe', 'fond de court')
        
        while '  ' in texte:
            texte = texte.replace('  ', ' ')
        
        return texte.strip()
    
    def analyser_texte(self, texte):
        """Analyse le texte et extrait toutes les informations disponibles"""
        infos = {
            'categorie': None,
            'joueur1': None,
            'joueur2': None,
            'type_coup': None,
            'direction': None
        }
        
        # CATÉGORIE
        if 'faute provoquée' in texte:
            infos['categorie'] = 'faute_provoquee'
        elif 'faute' in texte:
            infos['categorie'] = 'faute'
        elif 'point' in texte:
            infos['categorie'] = 'point'
        
        # JOUEURS
        joueurs_trouves = []
        for joueur in self.joueurs:
            if joueur.lower() in texte:
                joueurs_trouves.append(joueur)
        
        if joueurs_trouves:
            infos['joueur1'] = joueurs_trouves[0]
            if len(joueurs_trouves) > 1:
                infos['joueur2'] = joueurs_trouves[1]
        
        # DIRECTION D'ABORD (pour éviter confusion avec type)
        has_direction = False
        if 'coup droit' in texte:
            infos['direction'] = 'coup_droit'
            has_direction = True
        elif 'revers' in texte:
            infos['direction'] = 'revers'
            has_direction = True
        elif 'balle haute' in texte:
            infos['direction'] = 'balle_haute'
            has_direction = True
        
        # TYPE DE COUP (vérifier d'abord les plus spécifiques)
        if 'fond de court' in texte:
            infos['type_coup'] = 'fond_de_court'
        elif 'service' in texte:
            infos['type_coup'] = 'service'
        elif 'lob' in texte:
            infos['type_coup'] = 'lob'
        elif 'volée' in texte:
            infos['type_coup'] = 'volee'
        # Si direction détectée mais pas de type, c'est forcément volée ou fond de court
        elif has_direction:
            # Si on a une direction mais pas de type explicite, deviner
            # "coup droit" seul = probablement fond de court
            # Mais on laisse le système demander pour être sûr
            pass
        
        return infos
    
    def fusionner_infos(self, nouvelles_infos):
        """Fusionne les nouvelles infos avec la commande en cours"""
        for cle, valeur in nouvelles_infos.items():
            if valeur is not None:
                self.commande_en_cours[cle] = valeur
    
    def identifier_manquant(self):
        """Identifie ce qui manque dans la commande"""
        manquant = []
        
        # Catégorie obligatoire
        if self.commande_en_cours['categorie'] is None:
            manquant.append('categorie')
        
        # Joueur obligatoire
        if self.commande_en_cours['joueur1'] is None:
            manquant.append('joueur')
        
        # Pour faute provoquée, il faut 2 joueurs
        if self.commande_en_cours['categorie'] == 'faute_provoquee':
            if self.commande_en_cours['joueur2'] is None:
                manquant.append('joueur2')
        
        # Type de coup obligatoire
        if self.commande_en_cours['type_coup'] is None:
            manquant.append('type_coup')
        
        # Direction obligatoire SAUF pour service et lob
        if self.commande_en_cours['type_coup'] in ['volee', 'fond_de_court']:
            if self.commande_en_cours['direction'] is None:
                manquant.append('direction')
        
        return manquant
    
    def generer_question(self, manquant):
        """Génère une question pour demander l'info manquante"""
        if not manquant:
            return None
        
        premier = manquant[0]
        
        if premier == 'categorie':
            return "❓ Quelle catégorie ? (point / faute / faute provoquée)"
        elif premier == 'joueur':
            return f"❓ Quel joueur ? ({' / '.join(self.joueurs)})"
        elif premier == 'joueur2':
            return f"❓ Quel deuxième joueur subit la faute ? ({' / '.join(self.joueurs)})"
        elif premier == 'type_coup':
            return "❓ Quel type de coup ? (service / volée / fond de court / lob)"
        elif premier == 'direction':
            return "❓ Quelle direction ? (coup droit / revers / balle haute)"
        
        return "❓ Information manquante"
    
    def commande_complete(self):
        """Vérifie si la commande est complète"""
        return len(self.identifier_manquant()) == 0
    
    def reinitialiser_commande(self):
        """Réinitialise la commande en cours"""
        self.commande_en_cours = {
            'categorie': None,
            'joueur1': None,
            'joueur2': None,
            'type_coup': None,
            'direction': None
        }
    
    def formater_commande_en_cours(self):
        """Formate la commande en cours pour affichage"""
        parties = []
        
        if self.commande_en_cours['categorie']:
            cat = self.commande_en_cours['categorie'].replace('_', ' ').upper()
            parties.append(cat)
        
        if self.commande_en_cours['joueur1']:
            parties.append(self.commande_en_cours['joueur1'])
        
        if self.commande_en_cours['joueur2']:
            parties.append(f"→ {self.commande_en_cours['joueur2']}")
        
        if self.commande_en_cours['type_coup']:
            type_affichage = self.commande_en_cours['type_coup'].replace('_', ' ').upper()
            parties.append(type_affichage)
        
        if self.commande_en_cours['direction']:
            dir_affichage = self.commande_en_cours['direction'].replace('_', ' ').upper()
            parties.append(dir_affichage)
        
        return ' | '.join(parties) if parties else '---'
    
    def creer_interface(self):
        """Crée l'interface graphique"""
        
        # TITRE
        titre = tk.Label(
            self.root,
            text="🎤 TEST VOCAL ADAPTATIF",
            font=("Arial", 28, "bold"),
            bg="#1e1e1e",
            fg="#00ff00"
        )
        titre.pack(pady=10)
        
        # FRAME PRINCIPAL
        frame_principal = tk.Frame(self.root, bg="#1e1e1e")
        frame_principal.pack(fill="both", expand=True, padx=10, pady=10)
        
        # === COLONNE GAUCHE ===
        frame_gauche = tk.Frame(frame_principal, bg="#1e1e1e", width=400)
        frame_gauche.pack(side="left", fill="both", expand=False, padx=(0, 10))
        
        # JOUEURS
        tk.Label(
            frame_gauche,
            text="👥 JOUEURS",
            font=("Arial", 14, "bold"),
            bg="#1e1e1e",
            fg="#ffffff"
        ).pack(pady=5)
        
        frame_joueurs = tk.Frame(frame_gauche, bg="#2d2d2d")
        frame_joueurs.pack(fill="x", padx=10, pady=5)
        
        for i, prenom in enumerate(self.joueurs, 1):
            tk.Label(
                frame_joueurs,
                text=f"{i}. {prenom}",
                font=("Courier", 11),
                bg="#2d2d2d",
                fg="#00ffff"
            ).pack(anchor="w", padx=10, pady=2)
        
        # GUIDE
        tk.Label(
            frame_gauche,
            text="━" * 40,
            font=("Arial", 10),
            bg="#1e1e1e",
            fg="#444444"
        ).pack(pady=10)
        
        tk.Label(
            frame_gauche,
            text="📖 COMMENT ÇA MARCHE ?",
            font=("Arial", 14, "bold"),
            bg="#1e1e1e",
            fg="#ffffff"
        ).pack(pady=5)
        
        guide_text = """
Dites les infos dans N'IMPORTE QUEL ORDRE !

Le système vous demandera
uniquement ce qui manque.

Exemples :
• "coup droit"
  → Demande : catégorie, joueur, type
  
• "Pierre volée"
  → Demande : catégorie, direction
  
• "point service"
  → Demande : joueur seulement
  
• "faute provoquée Pierre"
  → Demande : joueur 2, type de coup
        """
        
        tk.Label(
            frame_gauche,
            text=guide_text,
            font=("Courier", 9),
            bg="#2d2d2d",
            fg="#ffff00",
            justify="left",
            anchor="w"
        ).pack(fill="x", padx=10, pady=5)
        
        # STATISTIQUES
        tk.Label(
            frame_gauche,
            text="━" * 40,
            font=("Arial", 10),
            bg="#1e1e1e",
            fg="#444444"
        ).pack(pady=10)
        
        tk.Label(
            frame_gauche,
            text="📊 STATISTIQUES",
            font=("Arial", 14, "bold"),
            bg="#1e1e1e",
            fg="#ffffff"
        ).pack(pady=5)
        
        self.label_stats = tk.Label(
            frame_gauche,
            text=self.formater_stats(),
            font=("Courier", 11),
            bg="#1e1e1e",
            fg="#00ffff",
            justify="left"
        )
        self.label_stats.pack(pady=5)
        
        # === COLONNE DROITE ===
        frame_droite = tk.Frame(frame_principal, bg="#1e1e1e")
        frame_droite.pack(side="right", fill="both", expand=True)
        
        # ZONE D'ANIMATION
        self.canvas = tk.Canvas(
            frame_droite,
            width=900,
            height=400,
            bg="#2d2d2d",
            highlightthickness=2,
            highlightbackground="#00ff00"
        )
        self.canvas.pack(pady=10)
        
        self.canvas_text = self.canvas.create_text(
            450, 200,
            text="En attente...",
            font=("Arial", 20),
            fill="#888888"
        )
        
        # TRANSCRIPTION
        frame_trans = tk.Frame(frame_droite, bg="#1e1e1e")
        frame_trans.pack(pady=10, fill="x", padx=20)
        
        tk.Label(
            frame_trans,
            text="🎙️ VOUS AVEZ DIT :",
            font=("Arial", 12, "bold"),
            bg="#1e1e1e",
            fg="#ffffff"
        ).pack(side="left", padx=10)
        
        self.label_transcription = tk.Label(
            frame_trans,
            text="---",
            font=("Arial", 12),
            bg="#1e1e1e",
            fg="#ffff00"
        )
        self.label_transcription.pack(side="left", padx=10)
        
        # COMMANDE EN COURS
        frame_encours = tk.Frame(frame_droite, bg="#1e1e1e")
        frame_encours.pack(pady=5, fill="x", padx=20)
        
        tk.Label(
            frame_encours,
            text="📝 EN COURS :",
            font=("Arial", 12, "bold"),
            bg="#1e1e1e",
            fg="#ffffff"
        ).pack(side="left", padx=10)
        
        self.label_encours = tk.Label(
            frame_encours,
            text="---",
            font=("Arial", 12, "bold"),
            bg="#1e1e1e",
            fg="#ff6b00"
        )
        self.label_encours.pack(side="left", padx=10)
        
        # QUESTION
        frame_question = tk.Frame(frame_droite, bg="#1e1e1e")
        frame_question.pack(pady=5, fill="x", padx=20)
        
        self.label_question = tk.Label(
            frame_question,
            text="",
            font=("Arial", 14, "bold"),
            bg="#1e1e1e",
            fg="#ff00ff"
        )
        self.label_question.pack(pady=5)
        
        # COMMANDE VALIDÉE
        frame_valide = tk.Frame(frame_droite, bg="#1e1e1e")
        frame_valide.pack(pady=5, fill="x", padx=20)
        
        tk.Label(
            frame_valide,
            text="✅ VALIDÉ :",
            font=("Arial", 12, "bold"),
            bg="#1e1e1e",
            fg="#ffffff"
        ).pack(side="left", padx=10)
        
        self.label_valide = tk.Label(
            frame_valide,
            text="---",
            font=("Arial", 12, "bold"),
            bg="#1e1e1e",
            fg="#00ff00"
        )
        self.label_valide.pack(side="left", padx=10)
        
        # BOUTON
        self.bouton_ecoute = tk.Button(
            frame_droite,
            text="▶️ DÉMARRER L'ÉCOUTE",
            font=("Arial", 14, "bold"),
            bg="#00ff00",
            fg="#000000",
            command=self.toggle_ecoute,
            width=30,
            height=2
        )
        self.bouton_ecoute.pack(pady=20)
    
    def formater_stats(self):
        """Formate les statistiques"""
        return f"""
✓ POINT            : {self.stats['point']:3d}
❌ FAUTE            : {self.stats['faute']:3d}
⚡ FAUTE PROVOQUÉE  : {self.stats['faute_provoquee']:3d}
━━━━━━━━━━━━━━━━━━━━━━━━
📈 TOTAL            : {self.stats['total']:3d}
        """
    
    def toggle_ecoute(self):
        """Démarre/arrête l'écoute"""
        if self.en_ecoute:
            self.arreter_ecoute()
        else:
            self.demarrer_ecoute()
    
    def demarrer_ecoute(self):
        """Démarre l'écoute"""
        self.en_ecoute = True
        self.reinitialiser_commande()
        self.bouton_ecoute.config(
            text="⏸️ ARRÊTER L'ÉCOUTE",
            bg="#ff0000",
            fg="#ffffff"
        )
        self.label_question.config(text="🎤 Dites n'importe quelle information...")
        thread = threading.Thread(target=self.ecoute_continue, daemon=True)
        thread.start()
    
    def arreter_ecoute(self):
        """Arrête l'écoute"""
        self.en_ecoute = False
        self.bouton_ecoute.config(
            text="▶️ DÉMARRER L'ÉCOUTE",
            bg="#00ff00",
            fg="#000000"
        )
        self.label_question.config(text="")
    
    def ecoute_continue(self):
        """Écoute continue"""
        while self.en_ecoute:
            try:
                with self.microphone as source:
                    self.root.after(0, self.label_transcription.config, 
                                   {"text": "🎤 Écoute..."})
                    
                    audio = self.recognizer.listen(source, timeout=None, phrase_time_limit=15)
                    
                    self.root.after(0, self.label_transcription.config, 
                                   {"text": "🔄 Transcription..."})
                    
                    texte_original = self.recognizer.recognize_google(audio, language="fr-FR")
                    texte_normalise = self.normaliser_texte(texte_original)
                    
                    self.root.after(0, self.traiter_texte, texte_original, texte_normalise)
                    
            except sr.UnknownValueError:
                self.root.after(0, self.label_transcription.config, 
                               {"text": "❌ Impossible de comprendre"})
            except Exception as e:
                print(f"Erreur : {e}")
    
    def traiter_texte(self, original, normalise):
        """Traite le texte reçu"""
        self.label_transcription.config(text=f'"{original}"')
        
        # Analyser et fusionner
        nouvelles_infos = self.analyser_texte(normalise)
        self.fusionner_infos(nouvelles_infos)
        
        # Afficher l'état actuel
        etat_actuel = self.formater_commande_en_cours()
        self.label_encours.config(text=etat_actuel)
        
        # DEBUG : Afficher ce qui a été détecté
        print(f"\n🔍 DEBUG :")
        print(f"   Original   : {original}")
        print(f"   Normalisé  : {normalise}")
        print(f"   Détecté    : {nouvelles_infos}")
        print(f"   État       : {self.commande_en_cours}")
        
        # Vérifier si complet
        if self.commande_complete():
            # COMMANDE COMPLÈTE !
            print(f"   ✅ COMPLET !")
            self.valider_commande()
        else:
            # Il manque des infos
            manquant = self.identifier_manquant()
            print(f"   ⚠️ Manque  : {manquant}")
            question = self.generer_question(manquant)
            self.label_question.config(text=question)
            
            # Mise à jour visuelle du canvas
            self.canvas.delete("all")
            self.canvas.create_text(
                450, 200,
                text=etat_actuel + "\n\n" + question,
                font=("Arial", 18, "bold"),
                fill="#ffff00"
            )
    
    def valider_commande(self):
        """Valide et anime la commande complète"""
        # Formater pour affichage
        cmd = self.commande_en_cours
        
        if cmd['categorie'] == 'faute_provoquee':
            texte_final = f"⚡ FAUTE PROVOQUÉE : {cmd['joueur1']} → {cmd['joueur2']} | "
            couleur = '#ff6b35'
            icon = '⚡'
        elif cmd['categorie'] == 'faute':
            texte_final = f"❌ FAUTE : {cmd['joueur1']} | "
            couleur = '#ff0000'
            icon = '❌'
        else:  # point
            texte_final = f"✓ POINT : {cmd['joueur1']} | "
            couleur = '#00ff00'
            icon = '✓'
        
        # Type de coup
        type_affichage = cmd['type_coup'].replace('_', ' ').upper()
        texte_final += type_affichage
        
        # Direction si applicable
        if cmd['direction']:
            dir_affichage = cmd['direction'].replace('_', ' ').upper()
            texte_final += f" {dir_affichage}"
        
        self.label_valide.config(text=texte_final, fg=couleur)
        self.label_question.config(text="✅ COMMANDE COMPLÈTE !")
        
        # Mettre à jour stats
        self.stats[cmd['categorie']] += 1
        self.stats['total'] += 1
        self.label_stats.config(text=self.formater_stats())
        
        # ANIMATION
        self.animer_validation(icon, couleur, texte_final)
        
        # Réinitialiser après 2 secondes
        self.root.after(2000, self.reinitialiser_apres_validation)
    
    def reinitialiser_apres_validation(self):
        """Réinitialise après validation"""
        if self.en_ecoute:
            self.reinitialiser_commande()
            self.label_encours.config(text="---")
            self.label_question.config(text="🎤 Dites n'importe quelle information...")
            self.canvas.delete("all")
            self.canvas.create_text(
                450, 200,
                text="En attente de la prochaine commande...",
                font=("Arial", 20),
                fill="#888888"
            )
    
    def animer_validation(self, icon, couleur, texte):
        """Anime la validation"""
        self.canvas.delete("all")
        
        x = random.randint(150, 750)
        y = 50
        
        balle = self.canvas.create_oval(
            x - 50, y - 50, x + 50, y + 50,
            fill=couleur, outline="#ffffff", width=4
        )
        
        texte_balle = self.canvas.create_text(
            x, y,
            text=icon,
            font=("Arial", 40, "bold"),
            fill="#ffffff"
        )
        
        self.canvas.create_text(
            450, 350,
            text=texte,
            font=("Arial", 16, "bold"),
            fill=couleur
        )
        
        self.rebondir(balle, texte_balle, x, y, random.uniform(-4, 4), 0, 0)
    
    def rebondir(self, balle, texte, x, y, vx, vy, etape):
        """Animation rebond"""
        if etape > 40:
            return
        
        vy += 0.6
        x += vx
        y += vy
        
        if y > 350:
            y = 350
            vy = -vy * 0.75
        if x < 50 or x > 850:
            vx = -vx
        
        coords = self.canvas.coords(balle)
        if coords:
            dx = x - (coords[0] + 50)
            dy = y - (coords[1] + 50)
            self.canvas.move(balle, dx, dy)
            self.canvas.move(texte, dx, dy)
        
        self.root.after(30, lambda: self.rebondir(balle, texte, x, y, vx, vy, etape + 1))


def main():
    root = tk.Tk()
    app = TestVocalAdaptatif(root)
    root.mainloop()


if __name__ == "__main__":
    print("=" * 70)
    print("🎤 TEST VOCAL ADAPTATIF - PADEL STAT")
    print("=" * 70)
    print()
    print("💡 FONCTIONNEMENT :")
    print("  Dites les infos dans N'IMPORTE QUEL ORDRE !")
    print("  Le système demande uniquement ce qui manque.")
    print()
    print("📝 EXEMPLES :")
    print("  • 'coup droit'          → Demande : catégorie, joueur, type")
    print("  • 'Pierre volée'        → Demande : catégorie, direction")
    print("  • 'point service'       → Demande : joueur")
    print("  • 'faute provoquée'     → Demande : 2 joueurs, type")
    print()
    print("=" * 70)
    print()
    
    main()
