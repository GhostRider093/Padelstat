#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEST VOCAL EN 2 ÉTAPES - PADEL STAT
Simplification : commande divisée en 2 parties
1. Catégorie + Joueur(s)
2. Type de coup + Localisation
"""

import tkinter as tk
from tkinter import ttk
import speech_recognition as sr
import threading
import random
from datetime import datetime

class TestVocal2Etapes:
    def __init__(self, root):
        self.root = root
        self.root.title("🎤 TEST VOCAL 2 ÉTAPES - PADEL STAT")
        self.root.geometry("1400x900")
        self.root.configure(bg="#1e1e1e")
        
        # Configuration joueurs (prénoms)
        self.joueurs = ["Pierre", "Lucas", "Marie", "Sophie"]
        
        # État du workflow
        self.etape = 1  # 1 = catégorie+joueur, 2 = type de coup
        self.commande_partielle = None
        
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
        """Normalise le texte - version simplifiée pour 2 étapes"""
        texte = texte.lower().strip()
        
        # CATÉGORIES
        texte = texte.replace('points', 'point')
        texte = texte.replace('fautes', 'faute')
        texte = texte.replace('faut', 'faute')
        texte = texte.replace('foot', 'faute')
        texte = texte.replace('ford', 'faute')
        texte = texte.replace('photos', 'faute')
        texte = texte.replace('phoque', 'faute')
        
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
        texte = texte.replace('provoquer', 'faute provoquée')  # Fallback si juste "provoquer"
        
        # JOUEURS (prénoms)
        for i, prenom in enumerate(self.joueurs, 1):
            texte = texte.replace(f'joueur {i}', prenom.lower())
            texte = texte.replace(f'joueur{i}', prenom.lower())
            texte = texte.replace(f'jour {i}', prenom.lower())
            texte = texte.replace(f'jours {i}', prenom.lower())
        
        # Variantes joueur générique
        texte = texte.replace('joueur un', self.joueurs[0].lower())
        texte = texte.replace('joueur de', self.joueurs[1].lower())
        texte = texte.replace('joueurs de', self.joueurs[1].lower())
        
        # TYPES DE COUPS
        texte = texte.replace('services', 'service')
        texte = texte.replace('volley', 'volée')
        texte = texte.replace('volets', 'volée')
        texte = texte.replace('volet', 'volée')
        texte = texte.replace('lobs', 'lob')
        texte = texte.replace('lobes', 'lob')
        texte = texte.replace("l'aube", 'lob')
        texte = texte.replace("de l'aube", 'lob')
        
        # DIRECTIONS
        texte = texte.replace('coup-droit', 'coup droit')
        texte = texte.replace('coudra', 'coup droit')
        texte = texte.replace('rêveur', 'revers')
        texte = texte.replace('rêve', 'revers')
        texte = texte.replace('rover', 'revers')
        
        # BALLE HAUTE
        texte = texte.replace('ball au', 'balle haute')
        texte = texte.replace('ballotte', 'balle haute')
        texte = texte.replace('ball hot', 'balle haute')
        
        # FOND DE COURT
        texte = texte.replace('fond de cour', 'fond de court')
        texte = texte.replace('fond de cours', 'fond de court')
        texte = texte.replace('fin de cours', 'fond de court')
        texte = texte.replace('fond de courbe', 'fond de court')
        
        # Nettoyer espaces
        while '  ' in texte:
            texte = texte.replace('  ', ' ')
        
        return texte.strip()
    
    def creer_interface(self):
        """Crée l'interface graphique"""
        
        # TITRE
        titre = tk.Label(
            self.root,
            text="🎤 TEST VOCAL EN 2 ÉTAPES",
            font=("Arial", 28, "bold"),
            bg="#1e1e1e",
            fg="#00ff00"
        )
        titre.pack(pady=10)
        
        # FRAME PRINCIPAL
        frame_principal = tk.Frame(self.root, bg="#1e1e1e")
        frame_principal.pack(fill="both", expand=True, padx=10, pady=10)
        
        # === COLONNE GAUCHE : WORKFLOW ===
        frame_gauche = tk.Frame(frame_principal, bg="#1e1e1e", width=400)
        frame_gauche.pack(side="left", fill="both", expand=False, padx=(0, 10))
        
        # CONFIGURATION JOUEURS
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
                text=f"Joueur {i} : {prenom}",
                font=("Courier", 11),
                bg="#2d2d2d",
                fg="#00ffff"
            ).pack(anchor="w", padx=10, pady=2)
        
        # WORKFLOW - ÉTAPE 1
        tk.Label(
            frame_gauche,
            text="━" * 40,
            font=("Arial", 10),
            bg="#1e1e1e",
            fg="#444444"
        ).pack(pady=10)
        
        self.label_etape1 = tk.Label(
            frame_gauche,
            text="ÉTAPE 1️⃣ : Catégorie + Joueur",
            font=("Arial", 14, "bold"),
            bg="#1e1e1e",
            fg="#ffff00"
        )
        self.label_etape1.pack(pady=5)
        
        frame_exemples1 = tk.Frame(frame_gauche, bg="#2d2d2d")
        frame_exemples1.pack(fill="x", padx=10, pady=5)
        
        exemples1 = [
            "✓ 'point Pierre'",
            "✓ 'faute Lucas'",
            "✓ 'faute provoquée Pierre Lucas'"
        ]
        for ex in exemples1:
            tk.Label(
                frame_exemples1,
                text=ex,
                font=("Courier", 10),
                bg="#2d2d2d",
                fg="#00ff00",
                anchor="w"
            ).pack(anchor="w", padx=10, pady=2)
        
        # WORKFLOW - ÉTAPE 2
        tk.Label(
            frame_gauche,
            text="━" * 40,
            font=("Arial", 10),
            bg="#1e1e1e",
            fg="#444444"
        ).pack(pady=10)
        
        self.label_etape2 = tk.Label(
            frame_gauche,
            text="ÉTAPE 2️⃣ : Type de coup",
            font=("Arial", 14, "bold"),
            bg="#1e1e1e",
            fg="#666666"
        )
        self.label_etape2.pack(pady=5)
        
        frame_exemples2 = tk.Frame(frame_gauche, bg="#2d2d2d")
        frame_exemples2.pack(fill="x", padx=10, pady=5)
        
        exemples2 = [
            "✓ 'service'",
            "✓ 'volée coup droit'",
            "✓ 'fond de court revers'",
            "✓ 'lob'"
        ]
        for ex in exemples2:
            tk.Label(
                frame_exemples2,
                text=ex,
                font=("Courier", 10),
                bg="#2d2d2d",
                fg="#888888",
                anchor="w"
            ).pack(anchor="w", padx=10, pady=2)
        
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
        
        # === COLONNE DROITE : CANVAS ET INFOS ===
        frame_droite = tk.Frame(frame_principal, bg="#1e1e1e")
        frame_droite.pack(side="right", fill="both", expand=True)
        
        # ZONE D'ANIMATION
        self.canvas = tk.Canvas(
            frame_droite,
            width=900,
            height=500,
            bg="#2d2d2d",
            highlightthickness=2,
            highlightbackground="#00ff00"
        )
        self.canvas.pack(pady=10)
        
        self.canvas_text = self.canvas.create_text(
            450, 250,
            text="En attente...",
            font=("Arial", 20),
            fill="#888888"
        )
        
        # TRANSCRIPTION
        frame_trans = tk.Frame(frame_droite, bg="#1e1e1e")
        frame_trans.pack(pady=10, fill="x", padx=20)
        
        tk.Label(
            frame_trans,
            text="🎙️ TRANSCRIPTION :",
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
        
        # COMMANDE PARTIELLE
        frame_partielle = tk.Frame(frame_droite, bg="#1e1e1e")
        frame_partielle.pack(pady=5, fill="x", padx=20)
        
        tk.Label(
            frame_partielle,
            text="📝 EN COURS :",
            font=("Arial", 12, "bold"),
            bg="#1e1e1e",
            fg="#ffffff"
        ).pack(side="left", padx=10)
        
        self.label_partielle = tk.Label(
            frame_partielle,
            text="---",
            font=("Arial", 12, "bold"),
            bg="#1e1e1e",
            fg="#ff6b00"
        )
        self.label_partielle.pack(side="left", padx=10)
        
        # COMMANDE FINALE
        frame_finale = tk.Frame(frame_droite, bg="#1e1e1e")
        frame_finale.pack(pady=5, fill="x", padx=20)
        
        tk.Label(
            frame_finale,
            text="✅ VALIDÉ :",
            font=("Arial", 12, "bold"),
            bg="#1e1e1e",
            fg="#ffffff"
        ).pack(side="left", padx=10)
        
        self.label_finale = tk.Label(
            frame_finale,
            text="---",
            font=("Arial", 12, "bold"),
            bg="#1e1e1e",
            fg="#00ff00"
        )
        self.label_finale.pack(side="left", padx=10)
        
        # BOUTON DÉMARRER/ARRÊTER
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
        self.etape = 1
        self.commande_partielle = None
        self.bouton_ecoute.config(
            text="⏸️ ARRÊTER L'ÉCOUTE",
            bg="#ff0000",
            fg="#ffffff"
        )
        self.mettre_a_jour_etape_visuelle()
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
    
    def mettre_a_jour_etape_visuelle(self):
        """Met à jour l'affichage de l'étape en cours"""
        if self.etape == 1:
            self.label_etape1.config(fg="#ffff00", font=("Arial", 14, "bold"))
            self.label_etape2.config(fg="#666666", font=("Arial", 14, "normal"))
        else:
            self.label_etape1.config(fg="#00ff00", font=("Arial", 14, "normal"))
            self.label_etape2.config(fg="#ffff00", font=("Arial", 14, "bold"))
    
    def ecoute_continue(self):
        """Écoute continue"""
        while self.en_ecoute:
            try:
                with self.microphone as source:
                    self.root.after(0, self.label_transcription.config, 
                                   {"text": f"🎤 Écoute ÉTAPE {self.etape}..."})
                    
                    audio = self.recognizer.listen(source, timeout=None, phrase_time_limit=10)
                    
                    self.root.after(0, self.label_transcription.config, 
                                   {"text": "🔄 Transcription..."})
                    
                    texte_original = self.recognizer.recognize_google(audio, language="fr-FR")
                    texte_normalise = self.normaliser_texte(texte_original)
                    
                    # Traiter selon l'étape
                    if self.etape == 1:
                        self.root.after(0, self.traiter_etape1, texte_original, texte_normalise)
                    else:
                        self.root.after(0, self.traiter_etape2, texte_original, texte_normalise)
                    
            except sr.UnknownValueError:
                self.root.after(0, self.label_transcription.config, 
                               {"text": "❌ Impossible de comprendre"})
            except Exception as e:
                print(f"Erreur : {e}")
    
    def traiter_etape1(self, original, normalise):
        """Traite l'étape 1 : catégorie + joueur(s)"""
        self.label_transcription.config(text=f'"{original}"')
        
        mots = normalise.split()
        if not mots:
            return
        
        # DÉTECTION COMMANDE COMPLÈTE EN 1 FOIS (catégorie + joueur + coup)
        coup_detecte = self.extraire_coup(normalise)
        commande_complete_detectee = (coup_detecte != 'NON SPÉCIFIÉ')
        
        # Identifier la catégorie
        if 'faute provoquée' in normalise:
            # Chercher 2 joueurs
            joueurs_trouves = [j for j in self.joueurs if j.lower() in normalise]
            if len(joueurs_trouves) >= 2:
                self.commande_partielle = {
                    'type': 'faute_provoquee',
                    'categorie': 'FAUTE PROVOQUÉE',
                    'joueur1': joueurs_trouves[0],
                    'joueur2': joueurs_trouves[1],
                    'couleur': '#ff6b35',
                    'icon': '⚡'
                }
                self.label_partielle.config(
                    text=f"⚡ FAUTE PROVOQUÉE : {joueurs_trouves[0]} → {joueurs_trouves[1]}",
                    fg="#ff6b35"
                )
                
                # Si coup détecté dans la même phrase, terminer directement
                if commande_complete_detectee:
                    self.commande_partielle['coup'] = coup_detecte
                    self.finaliser_commande()
                else:
                    self.etape = 2
                    self.mettre_a_jour_etape_visuelle()
                    self.canvas.delete("all")
                    self.canvas.create_text(450, 250, text=f"⚡ {joueurs_trouves[0]} → {joueurs_trouves[1]}\n\nDites le type de coup...", 
                                           font=("Arial", 24, "bold"), fill="#ff6b35")
        
        elif mots[0] == 'faute':
            joueur = self.trouver_joueur(normalise)
            if joueur:
                self.commande_partielle = {
                    'type': 'faute',
                    'categorie': 'FAUTE',
                    'joueur': joueur,
                    'couleur': '#ff0000',
                    'icon': '❌'
                }
                self.label_partielle.config(
                    text=f"❌ FAUTE : {joueur}",
                    fg="#ff0000"
                )
                
                # Si coup détecté dans la même phrase, terminer directement
                if commande_complete_detectee:
                    self.commande_partielle['coup'] = coup_detecte
                    self.finaliser_commande()
                else:
                    self.etape = 2
                    self.mettre_a_jour_etape_visuelle()
                    self.canvas.delete("all")
                    self.canvas.create_text(450, 250, text=f"❌ FAUTE {joueur}\n\nDites le type de coup...", 
                                           font=("Arial", 24, "bold"), fill="#ff0000")
        
        elif mots[0] == 'point':
            joueur = self.trouver_joueur(normalise)
            if joueur:
                self.commande_partielle = {
                    'type': 'point',
                    'categorie': 'POINT',
                    'joueur': joueur,
                    'couleur': '#00ff00',
                    'icon': '✓'
                }
                self.label_partielle.config(
                    text=f"✓ POINT : {joueur}",
                    fg="#00ff00"
                )
                
                # Si coup détecté dans la même phrase, terminer directement
                if commande_complete_detectee:
                    self.commande_partielle['coup'] = coup_detecte
                    self.finaliser_commande()
                else:
                    self.etape = 2
                    self.mettre_a_jour_etape_visuelle()
                    self.canvas.delete("all")
                    self.canvas.create_text(450, 250, text=f"✓ POINT {joueur}\n\nDites le type de coup...", 
                                           font=("Arial", 24, "bold"), fill="#00ff00")
    
    def finaliser_commande(self):
        """Finalise la commande après détection complète"""
        if not self.commande_partielle or 'coup' not in self.commande_partielle:
            return
        
        # Afficher la commande finale
        if self.commande_partielle['type'] == 'faute_provoquee':
            texte_final = f"⚡ {self.commande_partielle['categorie']} : {self.commande_partielle['joueur1']} → {self.commande_partielle['joueur2']} | {self.commande_partielle['coup']}"
        else:
            texte_final = f"{self.commande_partielle['icon']} {self.commande_partielle['categorie']} : {self.commande_partielle['joueur']} | {self.commande_partielle['coup']}"
        
        self.label_finale.config(
            text=texte_final,
            fg=self.commande_partielle['couleur']
        )
        
        # Mettre à jour stats
        self.stats[self.commande_partielle['type']] += 1
        self.stats['total'] += 1
        self.label_stats.config(text=self.formater_stats())
        
        # ANIMATION !
        self.animer_commande_complete(self.commande_partielle)
        
        # Réinitialiser pour la prochaine commande
        self.etape = 1
        self.commande_partielle = None
        self.label_partielle.config(text="---", fg="#ff6b00")
        self.mettre_a_jour_etape_visuelle()
    
    def traiter_etape2(self, original, normalise):
        """Traite l'étape 2 : type de coup"""
        if not self.commande_partielle:
            return
        
        self.label_transcription.config(text=f'"{original}"')
        
        # Identifier le type de coup
        coup = self.extraire_coup(normalise)
        
        if coup != 'NON SPÉCIFIÉ':
            # Commande complète !
            self.commande_partielle['coup'] = coup
            self.finaliser_commande()
        else:
            self.label_transcription.config(text=f"⚠️ Type de coup non reconnu : {normalise}")
    
    def trouver_joueur(self, texte):
        """Trouve le joueur dans le texte"""
        for joueur in self.joueurs:
            if joueur.lower() in texte:
                return joueur
        return None
    
    def extraire_coup(self, texte):
        """Extrait le type de coup"""
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
    
    def animer_commande_complete(self, commande):
        """Anime la commande complète"""
        self.canvas.delete("all")
        
        couleur = commande['couleur']
        icon = commande['icon']
        
        # Grande balle qui rebondit
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
        
        # Info commande
        if commande['type'] == 'faute_provoquee':
            info = f"{commande['categorie']}\n{commande['joueur1']} → {commande['joueur2']}\n{commande['coup']}"
        else:
            info = f"{commande['categorie']}\n{commande['joueur']}\n{commande['coup']}"
        
        self.canvas.create_text(
            450, 450,
            text=info,
            font=("Arial", 22, "bold"),
            fill=couleur
        )
        
        self.rebondir(balle, texte_balle, x, y, random.uniform(-4, 4), 0, 0)
    
    def rebondir(self, balle, texte, x, y, vx, vy, etape):
        """Animation rebond"""
        if etape > 50:
            return
        
        vy += 0.6
        x += vx
        y += vy
        
        if y > 450:
            y = 450
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
    app = TestVocal2Etapes(root)
    root.mainloop()


if __name__ == "__main__":
    print("=" * 70)
    print("🎤 TEST VOCAL EN 2 ÉTAPES - PADEL STAT")
    print("=" * 70)
    print()
    print("📋 WORKFLOW :")
    print("  ÉTAPE 1 : Dites 'point Pierre' ou 'faute Lucas'")
    print("  ÉTAPE 2 : Dites 'volée coup droit' ou 'service'")
    print()
    print("👥 JOUEURS CONFIGURÉS :")
    print("  Joueur 1 : Pierre")
    print("  Joueur 2 : Lucas")
    print("  Joueur 3 : Marie")
    print("  Joueur 4 : Sophie")
    print()
    print("=" * 70)
    print()
    
    main()
