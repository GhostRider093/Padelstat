#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEST VOCAL VISUEL - PADEL STAT
Interface graphique Tkinter avec reconnaissance vocale en temps réel
Actions visuelles pour chaque commande reconnue
"""

import tkinter as tk
from tkinter import ttk
import speech_recognition as sr
import threading
import random
from datetime import datetime

class TestVocalVisuel:
    def __init__(self, root):
        self.root = root
        self.root.title("🎤 TEST VOCAL VISUEL - PADEL STAT")
        self.root.geometry("1200x800")
        self.root.configure(bg="#1e1e1e")
        
        # Variables
        self.en_ecoute = False
        self.stats = {
            "point": 0,
            "faute": 0,
            "faute_provoquee": 0,
            "non_reconnues": 0
        }
        
        # Reconnaissance vocale
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        # Calibrage initial
        self.calibrer_micro()
        
        # Interface
        self.creer_interface()
        
    def calibrer_micro(self):
        """Calibre le microphone pour le bruit ambiant"""
        print("🎤 Calibrage du microphone...")
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
        print("✅ Calibrage terminé")
    
    def normaliser_texte(self, texte):
        """Normalise le texte pour comparaison - accepte TOUTES les variantes réelles"""
        texte = texte.lower().strip()
        
        # === CATÉGORIES PRINCIPALES ===
        # "point" - pas de variantes directes
        texte = texte.replace('points', 'point')
        
        # "faute" et toutes ses variantes
        texte = texte.replace('fautes', 'faute')
        texte = texte.replace('faut', 'faute')
        texte = texte.replace('foot', 'faute')
        texte = texte.replace('ford', 'faute')
        texte = texte.replace('photos', 'faute')
        texte = texte.replace('phoque', 'faute')
        
        # "faute provoquée" et toutes ses variantes
        texte = texte.replace('faute provoqué', 'faute provoquée')
        texte = texte.replace('faute provoquer', 'faute provoquée')
        texte = texte.replace('faut provoquer', 'faute provoquée')
        texte = texte.replace('faut te provoquer', 'faute provoquée')
        texte = texte.replace('faut te provoquée', 'faute provoquée')
        texte = texte.replace('faute pro ok', 'faute provoquée')
        texte = texte.replace('foot pro ok', 'faute provoquée')
        texte = texte.replace('phoque provoquer', 'faute provoquée')
        
        # === JOUEURS ===
        # Joueur 1
        texte = texte.replace('joueur un', 'joueur1')
        texte = texte.replace('joueur 1', 'joueur1')
        texte = texte.replace('jour un', 'joueur1')
        texte = texte.replace('jour 1', 'joueur1')
        texte = texte.replace('jours 1', 'joueur1')
        texte = texte.replace('joue un', 'joueur1')
        texte = texte.replace('genre un', 'joueur1')
        
        # Joueur 2
        texte = texte.replace('joueur deux', 'joueur2')
        texte = texte.replace('joueur 2', 'joueur2')
        texte = texte.replace('joueur de', 'joueur2')
        texte = texte.replace('joueurs de', 'joueur2')
        
        # === TYPES DE COUPS ===
        
        # SERVICE
        texte = texte.replace('services', 'service')
        
        # VOLÉE et TOUTES ses variantes
        texte = texte.replace('volley-ball hot', 'volée balle haute')
        texte = texte.replace('volley balle au', 'volée balle haute')
        texte = texte.replace('volley ball au', 'volée balle haute')
        texte = texte.replace('volley-ball', 'volée')
        texte = texte.replace('volley', 'volée')
        texte = texte.replace('volleys', 'volée')
        texte = texte.replace('volées', 'volée')
        texte = texte.replace('vollée', 'volée')
        texte = texte.replace('vollées', 'volée')
        texte = texte.replace('volé', 'volée')
        texte = texte.replace('volets', 'volée')
        texte = texte.replace('volet', 'volée')
        
        # FOND DE COURT et variantes
        texte = texte.replace('fond de cour', 'fond de court')
        texte = texte.replace('fond de cours', 'fond de court')
        texte = texte.replace('fin de cours', 'fond de court')
        texte = texte.replace('fond de courbe', 'fond de court')
        texte = texte.replace('fond de courbevoie', 'fond de court')
        texte = texte.replace('fond de couverts', 'fond de court')
        texte = texte.replace('franco rover', 'fond de court revers')
        texte = texte.replace('francos rover', 'fond de court revers')
        texte = texte.replace('fond-de-court', 'fond de court')
        texte = texte.replace('fon de court', 'fond de court')
        
        # COUP DROIT et variantes
        texte = texte.replace('coup-droit', 'coup droit')
        texte = texte.replace('cou droit', 'coup droit')
        texte = texte.replace('coups droits', 'coup droit')
        texte = texte.replace('coudra', 'coup droit')
        
        # REVERS et variantes
        texte = texte.replace('rêveur', 'revers')
        texte = texte.replace('rêve', 'revers')
        texte = texte.replace('rover', 'revers')
        texte = texte.replace('reverre', 'revers')
        texte = texte.replace('reverts', 'revers')
        
        # BALLE HAUTE et variantes
        texte = texte.replace('ball au', 'balle haute')
        texte = texte.replace('ball hot', 'balle haute')
        texte = texte.replace('balle au', 'balle haute')
        texte = texte.replace('ballotte', 'balle haute')
        texte = texte.replace('balles hautes', 'balle haute')
        texte = texte.replace('balle-haute', 'balle haute')
        texte = texte.replace('bal haute', 'balle haute')
        
        # LOB et variantes
        texte = texte.replace('lobes', 'lob')
        texte = texte.replace('lobs', 'lob')
        texte = texte.replace('lobe', 'lob')
        texte = texte.replace("l'aube", 'lob')
        texte = texte.replace("de l'aube", 'lob')
        texte = texte.replace('lots', 'lob')
        
        # === NETTOYAGE FINAL ===
        texte = texte.replace(' à l\'autre', '')
        texte = texte.replace('faute toujours un', 'faute joueur1')
        texte = texte.replace('faute dire', 'faute')
        texte = texte.replace('point genre', 'point')
        
        # Nettoyer les espaces multiples
        while '  ' in texte:
            texte = texte.replace('  ', ' ')
        
        return texte.strip()
    
    def identifier_commande(self, texte_normalise):
        """Identifie le type de commande et extrait les informations"""
        mots = texte_normalise.split()
        
        if not mots:
            return None
        
        # FAUTE PROVOQUÉE
        if 'faute provoquée' in texte_normalise:
            return {
                'type': 'faute_provoquee',
                'categorie': 'FAUTE PROVOQUÉE',
                'joueur': self.extraire_joueur(mots),
                'coup': self.extraire_coup(texte_normalise),
                'couleur': '#ff6b35',  # Orange
                'icon': '⚡'
            }
        
        # FAUTE
        elif mots[0] == 'faute':
            return {
                'type': 'faute',
                'categorie': 'FAUTE',
                'joueur': self.extraire_joueur(mots),
                'coup': self.extraire_coup(texte_normalise),
                'couleur': '#ff0000',  # Rouge
                'icon': '❌'
            }
        
        # POINT
        elif mots[0] == 'point':
            return {
                'type': 'point',
                'categorie': 'POINT',
                'joueur': self.extraire_joueur(mots),
                'coup': self.extraire_coup(texte_normalise),
                'couleur': '#00ff00',  # Vert
                'icon': '✓'
            }
        
        return None
    
    def extraire_joueur(self, mots):
        """Extrait le joueur de la liste de mots"""
        if 'joueur1' in mots:
            return 'JOUEUR 1'
        elif 'joueur2' in mots:
            return 'JOUEUR 2'
        return 'INCONNU'
    
    def extraire_coup(self, texte):
        """Extrait le type de coup du texte"""
        if 'service' in texte:
            return 'SERVICE'
        elif 'volée balle haute' in texte:
            return 'VOLÉE BALLE HAUTE'
        elif 'volée coup droit' in texte:
            return 'VOLÉE COUP DROIT'
        elif 'volée revers' in texte:
            return 'VOLÉE REVERS'
        elif 'volée' in texte:
            return 'VOLÉE'
        elif 'fond de court balle haute' in texte:
            return 'FOND DE COURT BALLE HAUTE'
        elif 'fond de court coup droit' in texte:
            return 'FOND DE COURT COUP DROIT'
        elif 'fond de court revers' in texte:
            return 'FOND DE COURT REVERS'
        elif 'fond de court' in texte:
            return 'FOND DE COURT'
        elif 'lob' in texte:
            return 'LOB'
        return 'NON SPÉCIFIÉ'
    
    def get_toutes_commandes(self):
        """Retourne la liste complète des 48 commandes à tester"""
        joueurs = ['joueur1', 'joueur2']
        types_coups = [
            'service',
            'volée coup droit',
            'volée revers',
            'volée balle haute',
            'fond de court coup droit',
            'fond de court revers',
            'fond de court balle haute',
            'lob'
        ]
        
        commandes = []
        
        # POINT (16 commandes)
        for joueur in joueurs:
            for coup in types_coups:
                commandes.append(f"point {joueur} {coup}")
        
        # FAUTE (16 commandes)
        for joueur in joueurs:
            for coup in types_coups:
                commandes.append(f"faute {joueur} {coup}")
        
        # FAUTE PROVOQUÉE (16 commandes)
        for joueur in joueurs:
            for coup in types_coups:
                commandes.append(f"faute provoquée {joueur} joueur{3-int(joueur[-1])} {coup}")
        
        return commandes
    
    def creer_interface(self):
        """Crée l'interface graphique"""
        
        # TITRE
        titre = tk.Label(
            self.root,
            text="🎤 TEST VOCAL VISUEL",
            font=("Arial", 28, "bold"),
            bg="#1e1e1e",
            fg="#00ff00"
        )
        titre.pack(pady=10)
        
        # FRAME PRINCIPAL (2 colonnes)
        frame_principal = tk.Frame(self.root, bg="#1e1e1e")
        frame_principal.pack(fill="both", expand=True, padx=10, pady=10)
        
        # COLONNE GAUCHE : LISTE DES COMMANDES
        frame_gauche = tk.Frame(frame_principal, bg="#1e1e1e")
        frame_gauche.pack(side="left", fill="both", expand=False, padx=(0, 10))
        
        tk.Label(
            frame_gauche,
            text="📋 COMMANDES À TESTER (48)",
            font=("Arial", 12, "bold"),
            bg="#1e1e1e",
            fg="#ffffff"
        ).pack(pady=5)
        
        # Listbox avec scrollbar
        frame_listbox = tk.Frame(frame_gauche, bg="#1e1e1e")
        frame_listbox.pack(fill="both", expand=True)
        
        scrollbar = tk.Scrollbar(frame_listbox)
        scrollbar.pack(side="right", fill="y")
        
        self.listbox = tk.Listbox(
            frame_listbox,
            font=("Courier", 9),
            bg="#2d2d2d",
            fg="#00ff00",
            selectbackground="#00ff00",
            selectforeground="#000000",
            width=35,
            height=35,
            yscrollcommand=scrollbar.set
        )
        self.listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.listbox.yview)
        
        # Remplir la listbox
        toutes_commandes = self.get_toutes_commandes()
        for i, cmd in enumerate(toutes_commandes, 1):
            self.listbox.insert(tk.END, f"{i:2d}. {cmd}")
        
        # COLONNE DROITE : ZONE D'ACTION
        frame_droite = tk.Frame(frame_principal, bg="#1e1e1e")
        frame_droite.pack(side="right", fill="both", expand=True)
        # COLONNE DROITE : ZONE D'ACTION
        frame_droite = tk.Frame(frame_principal, bg="#1e1e1e")
        frame_droite.pack(side="right", fill="both", expand=True)
        
        # ZONE D'ACTION VISUELLE (Canvas)
        self.canvas = tk.Canvas(
            frame_droite,
            width=700,
            height=350,
            bg="#2d2d2d",
            highlightthickness=2,
            highlightbackground="#00ff00"
        )
        self.canvas.pack(pady=10)
        
        # Texte d'attente sur le canvas
        self.canvas_text = self.canvas.create_text(
            350, 175,
            text="En attente de commande vocale...",
            font=("Arial", 18),
            fill="#888888"
        )
        
        # ZONE TRANSCRIPTION
        frame_transcription = tk.Frame(self.root, bg="#1e1e1e")
        frame_transcription.pack(pady=10, fill="x", padx=50)
        
        tk.Label(
            frame_transcription,
            text="🎙️ TRANSCRIPTION :",
            font=("Arial", 12, "bold"),
            bg="#1e1e1e",
            fg="#ffffff"
        ).pack(side="left", padx=10)
        
        self.label_transcription = tk.Label(
            frame_transcription,
            text="---",
            font=("Arial", 12),
            bg="#1e1e1e",
            fg="#ffff00"
        )
        self.label_transcription.pack(side="left", padx=10)
        
        # ZONE COMMANDE RECONNUE
        frame_commande = tk.Frame(self.root, bg="#1e1e1e")
        frame_commande.pack(pady=5, fill="x", padx=50)
        
        tk.Label(
            frame_commande,
            text="✅ COMMANDE :",
            font=("Arial", 12, "bold"),
            bg="#1e1e1e",
            fg="#ffffff"
        ).pack(side="left", padx=10)
        
        self.label_commande = tk.Label(
            frame_commande,
            text="---",
            font=("Arial", 12),
            bg="#1e1e1e",
            fg="#00ff00"
        )
        self.label_commande.pack(side="left", padx=10)
        
        # STATISTIQUES
        frame_stats = tk.Frame(self.root, bg="#1e1e1e")
        frame_stats.pack(pady=20, fill="x", padx=50)
        
        tk.Label(
            frame_stats,
            text="📊 STATISTIQUES",
            font=("Arial", 14, "bold"),
            bg="#1e1e1e",
            fg="#ffffff"
        ).pack()
        
        self.label_stats = tk.Label(
            frame_stats,
            text=self.formater_stats(),
            font=("Courier", 11),
            bg="#1e1e1e",
            fg="#00ffff",
            justify="left"
        )
        self.label_stats.pack(pady=5)
        
        # BOUTON DÉMARRER/ARRÊTER
        self.bouton_ecoute = tk.Button(
            self.root,
            text="▶️ DÉMARRER L'ÉCOUTE",
            font=("Arial", 14, "bold"),
            bg="#00ff00",
            fg="#000000",
            command=self.toggle_ecoute,
            width=25,
            height=2
        )
        self.bouton_ecoute.pack(pady=20)
    
    def formater_stats(self):
        """Formate les statistiques pour affichage"""
        total = sum(self.stats.values())
        return f"""
        ✓ POINT           : {self.stats['point']:3d}
        ❌ FAUTE           : {self.stats['faute']:3d}
        ⚡ FAUTE PROVOQUÉE : {self.stats['faute_provoquee']:3d}
        ❓ NON RECONNUES   : {self.stats['non_reconnues']:3d}
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━
        📈 TOTAL           : {total:3d}
        """
    
    def toggle_ecoute(self):
        """Démarre ou arrête l'écoute"""
        if self.en_ecoute:
            self.arreter_ecoute()
        else:
            self.demarrer_ecoute()
    
    def demarrer_ecoute(self):
        """Démarre l'écoute en continu"""
        self.en_ecoute = True
        self.bouton_ecoute.config(
            text="⏸️ ARRÊTER L'ÉCOUTE",
            bg="#ff0000",
            fg="#ffffff"
        )
        
        # Thread pour l'écoute continue
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
    
    def ecoute_continue(self):
        """Écoute continue en boucle"""
        while self.en_ecoute:
            try:
                with self.microphone as source:
                    # Indiquer qu'on écoute
                    self.root.after(0, self.label_transcription.config, 
                                   {"text": "🎤 Écoute en cours..."})
                    
                    # Écouter (SANS timeout pour avoir tout le temps)
                    audio = self.recognizer.listen(source, timeout=None, phrase_time_limit=15)
                    
                    # Indiquer qu'on transcrit
                    self.root.after(0, self.label_transcription.config, 
                                   {"text": "🔄 Transcription..."})
                    
                    # Reconnaissance
                    texte_original = self.recognizer.recognize_google(audio, language="fr-FR")
                    texte_normalise = self.normaliser_texte(texte_original)
                    
                    # Identifier la commande
                    commande = self.identifier_commande(texte_normalise)
                    
                    if commande:
                        # Mettre à jour l'interface
                        self.root.after(0, self.afficher_commande, texte_original, texte_normalise, commande)
                    else:
                        # Commande non reconnue
                        self.root.after(0, self.afficher_non_reconnue, texte_original, texte_normalise)
                    
            except sr.WaitTimeoutError:
                # Timeout - pas de son détecté
                pass
            except sr.UnknownValueError:
                # Impossible de comprendre
                self.root.after(0, self.label_transcription.config, 
                               {"text": "❌ Impossible de comprendre"})
            except Exception as e:
                print(f"Erreur : {e}")
    
    def afficher_commande(self, original, normalise, commande):
        """Affiche une commande reconnue et déclenche l'animation"""
        # Mettre à jour les labels
        self.label_transcription.config(text=f'"{original}"')
        self.label_commande.config(
            text=f"{commande['icon']} {commande['categorie']} - {commande['joueur']} - {commande['coup']}",
            fg=commande['couleur']
        )
        
        # Mettre à jour les stats
        self.stats[commande['type']] += 1
        self.label_stats.config(text=self.formater_stats())
        
        # ANIMATION VISUELLE
        self.animer_commande(commande)
    
    def afficher_non_reconnue(self, original, normalise):
        """Affiche une commande non reconnue"""
        self.label_transcription.config(text=f'"{original}"')
        self.label_commande.config(
            text=f"⚠️ NON RECONNUE : {normalise}",
            fg="#ff6b00"
        )
        self.stats['non_reconnues'] += 1
        self.label_stats.config(text=self.formater_stats())
    
    def animer_commande(self, commande):
        """Anime visuellement la commande reconnue"""
        # Effacer le canvas
        self.canvas.delete("all")
        
        # Couleur et icône selon le type
        couleur = commande['couleur']
        icon = commande['icon']
        
        # ANIMATION : Balle qui apparaît et rebondit
        x_start = random.randint(100, 1000)
        y_start = 50
        
        # Créer la balle
        balle = self.canvas.create_oval(
            x_start - 30, y_start - 30,
            x_start + 30, y_start + 30,
            fill=couleur,
            outline="#ffffff",
            width=3
        )
        
        # Texte sur la balle
        texte_balle = self.canvas.create_text(
            x_start, y_start,
            text=icon,
            font=("Arial", 30, "bold"),
            fill="#ffffff"
        )
        
        # Infos de la commande
        info_text = f"{commande['categorie']}\n{commande['joueur']}\n{commande['coup']}"
        texte_info = self.canvas.create_text(
            550, 350,
            text=info_text,
            font=("Arial", 20, "bold"),
            fill=couleur
        )
        
        # Animation de rebond
        self.rebondir_balle(balle, texte_balle, x_start, y_start, 0, 0)
    
    def rebondir_balle(self, balle, texte, x, y, vx, vy, etape=0):
        """Anime le rebond de la balle"""
        if etape > 60:  # Arrêter après 60 frames (environ 2 secondes)
            return
        
        # Gravité
        vy += 0.5
        
        # Déplacement horizontal aléatoire initial
        if etape == 0:
            vx = random.uniform(-3, 3)
        
        # Nouvelle position
        x += vx
        y += vy
        
        # Rebond sur les bords
        if y > 370:  # Sol
            y = 370
            vy = -vy * 0.8  # Perte d'énergie
        if x < 30 or x > 1070:  # Murs
            vx = -vx
        
        # Déplacer les objets
        coords_balle = self.canvas.coords(balle)
        if coords_balle:
            dx = x - (coords_balle[0] + 30)
            dy = y - (coords_balle[1] + 30)
            self.canvas.move(balle, dx, dy)
            self.canvas.move(texte, dx, dy)
        
        # Récursion après 33ms (30 FPS)
        self.root.after(33, lambda: self.rebondir_balle(balle, texte, x, y, vx, vy, etape + 1))


def main():
    root = tk.Tk()
    app = TestVocalVisuel(root)
    root.mainloop()


if __name__ == "__main__":
    print("=" * 70)
    print("🎤 TEST VOCAL VISUEL - PADEL STAT")
    print("=" * 70)
    print()
    print("📋 Instructions :")
    print("  1. Cliquez sur 'DÉMARRER L'ÉCOUTE'")
    print("  2. Dites une commande vocale")
    print("  3. Observez l'animation visuelle")
    print("  4. Vérifiez les statistiques")
    print()
    print("💡 Exemples de commandes :")
    print("  - 'point joueur 1 service'")
    print("  - 'faute joueur 2 volée coup droit'")
    print("  - 'faute provoquée joueur 1 joueur 2 lob'")
    print()
    print("=" * 70)
    print()
    
    main()
