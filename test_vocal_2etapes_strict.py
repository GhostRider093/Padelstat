#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEST VOCAL 2 ÉTAPES STRICT - PADEL STAT
Ordre strict : 1) Catégorie+Joueur  2) Localisation+Direction
"""

import tkinter as tk
from tkinter import ttk
import speech_recognition as sr
import threading
import random
from datetime import datetime

class TestVocal2EtapesStrict:
    def __init__(self, root):
        self.root = root
        self.root.title("🎤 TEST VOCAL 2 ÉTAPES - PADEL STAT")
        self.root.geometry("1400x900")
        self.root.configure(bg="#1e1e1e")
        
        # Configuration joueurs
        self.joueurs = ["Pierre", "Lucas", "Marie", "Sophie"]
        
        # État du workflow
        self.etape = 1  # 1 ou 2
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
        texte = texte.replace('genre un', self.joueurs[0].lower())
        texte = texte.replace('joueur de', self.joueurs[1].lower())
        texte = texte.replace('joueur deux', self.joueurs[1].lower())
        texte = texte.replace('joueurs de', self.joueurs[1].lower())
        
        # LOCALISATIONS
        texte = texte.replace('services', 'service')
        texte = texte.replace('volley', 'volée')
        texte = texte.replace('volets', 'volée')
        texte = texte.replace('volet', 'volée')
        texte = texte.replace('lobs', 'lob')
        texte = texte.replace('lobes', 'lob')
        texte = texte.replace("l'aube", 'lob')
        texte = texte.replace('fond de cour', 'fond de court')
        texte = texte.replace('fond de cours', 'fond de court')
        texte = texte.replace('fin de cours', 'fond de court')
        texte = texte.replace('fond de courbe', 'fond de court')
        
        # DIRECTIONS
        texte = texte.replace('coup-droit', 'coup droit')
        texte = texte.replace('coudra', 'coup droit')
        texte = texte.replace('rêveur', 'revers')
        texte = texte.replace('rêve', 'revers')
        texte = texte.replace('rover', 'revers')
        texte = texte.replace('ball au', 'balle haute')
        texte = texte.replace('ballotte', 'balle haute')
        texte = texte.replace('ball hot', 'balle haute')
        
        while '  ' in texte:
            texte = texte.replace('  ', ' ')
        
        return texte.strip()
    
    def creer_interface(self):
        """Crée l'interface graphique"""
        
        # TITRE
        titre = tk.Label(
            self.root,
            text="🎤 TEST VOCAL 2 ÉTAPES",
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
        
        # WORKFLOW
        tk.Label(
            frame_gauche,
            text="━" * 40,
            font=("Arial", 10),
            bg="#1e1e1e",
            fg="#444444"
        ).pack(pady=10)
        
        # ÉTAPE 1
        self.label_etape1 = tk.Label(
            frame_gauche,
            text="ÉTAPE 1️⃣ : Catégorie + Joueur(s)",
            font=("Arial", 14, "bold"),
            bg="#1e1e1e",
            fg="#ffff00"
        )
        self.label_etape1.pack(pady=5)
        
        frame_ex1 = tk.Frame(frame_gauche, bg="#2d2d2d")
        frame_ex1.pack(fill="x", padx=10, pady=5)
        
        exemples1 = [
            "✓ 'point Pierre'",
            "✓ 'faute Lucas'",
            "✓ 'faute provoquée Pierre Lucas'"
        ]
        for ex in exemples1:
            tk.Label(
                frame_ex1,
                text=ex,
                font=("Courier", 10),
                bg="#2d2d2d",
                fg="#00ff00"
            ).pack(anchor="w", padx=10, pady=2)
        
        # ÉTAPE 2
        tk.Label(
            frame_gauche,
            text="━" * 40,
            font=("Arial", 10),
            bg="#1e1e1e",
            fg="#444444"
        ).pack(pady=10)
        
        self.label_etape2 = tk.Label(
            frame_gauche,
            text="ÉTAPE 2️⃣ : Localisation + Direction",
            font=("Arial", 14, "bold"),
            bg="#1e1e1e",
            fg="#666666"
        )
        self.label_etape2.pack(pady=5)
        
        frame_ex2 = tk.Frame(frame_gauche, bg="#2d2d2d")
        frame_ex2.pack(fill="x", padx=10, pady=5)
        
        exemples2 = [
            "✓ 'service'",
            "✓ 'volée coup droit'",
            "✓ 'fond de court revers'",
            "✓ 'lob'"
        ]
        for ex in exemples2:
            tk.Label(
                frame_ex2,
                text=ex,
                font=("Courier", 10),
                bg="#2d2d2d",
                fg="#888888"
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
        
        # === COLONNE DROITE ===
        frame_droite = tk.Frame(frame_principal, bg="#1e1e1e")
        frame_droite.pack(side="right", fill="both", expand=True)
        
        # CANVAS
        self.canvas = tk.Canvas(
            frame_droite,
            width=900,
            height=450,
            bg="#2d2d2d",
            highlightthickness=2,
            highlightbackground="#00ff00"
        )
        self.canvas.pack(pady=10)
        
        self.canvas_text = self.canvas.create_text(
            450, 225,
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
        
        # EN COURS
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
        
        # VALIDÉ
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
        if self.en_ecoute:
            self.arreter_ecoute()
        else:
            self.demarrer_ecoute()
    
    def demarrer_ecoute(self):
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
        self.en_ecoute = False
        self.bouton_ecoute.config(
            text="▶️ DÉMARRER L'ÉCOUTE",
            bg="#00ff00",
            fg="#000000"
        )
    
    def mettre_a_jour_etape_visuelle(self):
        """Met à jour l'affichage de l'étape"""
        if self.etape == 1:
            self.label_etape1.config(fg="#ffff00", font=("Arial", 14, "bold"))
            self.label_etape2.config(fg="#666666", font=("Arial", 14, "normal"))
        else:
            self.label_etape1.config(fg="#00ff00", font=("Arial", 14, "normal"))
            self.label_etape2.config(fg="#ffff00", font=("Arial", 14, "bold"))
    
    def ecoute_continue(self):
        while self.en_ecoute:
            try:
                with self.microphone as source:
                    self.root.after(0, self.label_transcription.config, 
                                   {"text": f"🎤 Écoute ÉTAPE {self.etape}..."})
                    
                    audio = self.recognizer.listen(source, timeout=None, phrase_time_limit=15)
                    
                    self.root.after(0, self.label_transcription.config, 
                                   {"text": "🔄 Transcription..."})
                    
                    texte_original = self.recognizer.recognize_google(audio, language="fr-FR")
                    texte_normalise = self.normaliser_texte(texte_original)
                    
                    # DEBUG
                    print(f"\n🔍 ÉTAPE {self.etape}")
                    print(f"   Original  : {texte_original}")
                    print(f"   Normalisé : {texte_normalise}")
                    
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
        """ÉTAPE 1 : Catégorie + Joueur(s)"""
        self.label_transcription.config(text=f'"{original}"')
        
        mots = normalise.split()
        if not mots:
            return
        
        # Identifier catégorie
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
                self.label_encours.config(
                    text=f"⚡ FAUTE PROVOQUÉE : {joueurs_trouves[0]} → {joueurs_trouves[1]}",
                    fg="#ff6b35"
                )
                print(f"   ✅ Détecté : FAUTE PROVOQUÉE {joueurs_trouves[0]} → {joueurs_trouves[1]}")
                self.passer_etape2(f"⚡ {joueurs_trouves[0]} → {joueurs_trouves[1]}\n\n➤ Dites le coup...", "#ff6b35")
            else:
                print(f"   ⚠️ FAUTE PROVOQUÉE mais pas assez de joueurs détectés")
                self.label_encours.config(text="⚠️ Il faut 2 joueurs pour faute provoquée", fg="#ff0000")
        
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
                self.label_encours.config(text=f"❌ FAUTE : {joueur}", fg="#ff0000")
                print(f"   ✅ Détecté : FAUTE {joueur}")
                self.passer_etape2(f"❌ FAUTE {joueur}\n\n➤ Dites le coup...", "#ff0000")
            else:
                print(f"   ⚠️ FAUTE mais joueur non détecté")
                self.label_encours.config(text="⚠️ Joueur non reconnu", fg="#ff0000")
        
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
                self.label_encours.config(text=f"✓ POINT : {joueur}", fg="#00ff00")
                print(f"   ✅ Détecté : POINT {joueur}")
                self.passer_etape2(f"✓ POINT {joueur}\n\n➤ Dites le coup...", "#00ff00")
            else:
                print(f"   ⚠️ POINT mais joueur non détecté")
                self.label_encours.config(text="⚠️ Joueur non reconnu", fg="#ff0000")
        else:
            print(f"   ⚠️ Catégorie non reconnue")
            self.label_encours.config(text="⚠️ Catégorie non reconnue (point/faute/faute provoquée)", fg="#ff0000")
    
    def passer_etape2(self, texte_canvas, couleur):
        """Passe à l'étape 2"""
        self.etape = 2
        self.mettre_a_jour_etape_visuelle()
        self.canvas.delete("all")
        self.canvas.create_text(
            450, 225,
            text=texte_canvas,
            font=("Arial", 24, "bold"),
            fill=couleur
        )
    
    def traiter_etape2(self, original, normalise):
        """ÉTAPE 2 : Localisation + Direction"""
        if not self.commande_partielle:
            print("   ⚠️ Pas de commande partielle !")
            return
        
        self.label_transcription.config(text=f'"{original}"')
        
        # Identifier localisation
        localisation = None
        direction = None
        
        if 'fond de court' in normalise:
            localisation = 'FOND DE COURT'
            if 'coup droit' in normalise:
                direction = 'COUP DROIT'
            elif 'revers' in normalise:
                direction = 'REVERS'
            elif 'balle haute' in normalise:
                direction = 'BALLE HAUTE'
        elif 'volée' in normalise:
            localisation = 'VOLÉE'
            if 'coup droit' in normalise:
                direction = 'COUP DROIT'
            elif 'revers' in normalise:
                direction = 'REVERS'
            elif 'balle haute' in normalise:
                direction = 'BALLE HAUTE'
        elif 'service' in normalise:
            localisation = 'SERVICE'
            direction = ''  # Pas de direction pour service
        elif 'lob' in normalise:
            localisation = 'LOB'
            direction = ''  # Pas de direction pour lob
        
        print(f"   Localisation : {localisation}")
        print(f"   Direction    : {direction}")
        
        if localisation:
            # Construire le coup complet
            if direction:
                coup_complet = f"{localisation} {direction}"
            else:
                coup_complet = localisation
            
            self.commande_partielle['coup'] = coup_complet
            
            # Afficher la commande finale
            if self.commande_partielle['type'] == 'faute_provoquee':
                texte_final = f"⚡ {self.commande_partielle['categorie']} : {self.commande_partielle['joueur1']} → {self.commande_partielle['joueur2']} | {coup_complet}"
            else:
                texte_final = f"{self.commande_partielle['icon']} {self.commande_partielle['categorie']} : {self.commande_partielle['joueur']} | {coup_complet}"
            
            self.label_valide.config(text=texte_final, fg=self.commande_partielle['couleur'])
            
            # Stats
            self.stats[self.commande_partielle['type']] += 1
            self.stats['total'] += 1
            self.label_stats.config(text=self.formater_stats())
            
            print(f"   ✅ COMMANDE COMPLÈTE : {texte_final}")
            
            # Animation
            self.animer_validation(self.commande_partielle, coup_complet)
            
            # Réinitialiser
            self.root.after(2000, self.reinitialiser)
        else:
            print(f"   ⚠️ Localisation non reconnue")
            self.label_encours.config(text="⚠️ Localisation non reconnue (service/volée/fond de court/lob)", fg="#ff0000")
    
    def trouver_joueur(self, texte):
        """Trouve le joueur dans le texte"""
        for joueur in self.joueurs:
            if joueur.lower() in texte:
                return joueur
        return None
    
    def animer_validation(self, commande, coup):
        """Anime la validation"""
        self.canvas.delete("all")
        
        x = random.randint(150, 750)
        y = 50
        
        balle = self.canvas.create_oval(
            x - 50, y - 50, x + 50, y + 50,
            fill=commande['couleur'], outline="#ffffff", width=4
        )
        
        texte_balle = self.canvas.create_text(
            x, y,
            text=commande['icon'],
            font=("Arial", 40, "bold"),
            fill="#ffffff"
        )
        
        if commande['type'] == 'faute_provoquee':
            info = f"{commande['categorie']}\n{commande['joueur1']} → {commande['joueur2']}\n{coup}"
        else:
            info = f"{commande['categorie']}\n{commande['joueur']}\n{coup}"
        
        self.canvas.create_text(
            450, 400,
            text=info,
            font=("Arial", 20, "bold"),
            fill=commande['couleur']
        )
        
        self.rebondir(balle, texte_balle, x, y, random.uniform(-4, 4), 0, 0)
    
    def rebondir(self, balle, texte, x, y, vx, vy, etape):
        if etape > 40:
            return
        
        vy += 0.6
        x += vx
        y += vy
        
        if y > 400:
            y = 400
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
    
    def reinitialiser(self):
        """Réinitialise pour la prochaine commande"""
        if self.en_ecoute:
            self.etape = 1
            self.commande_partielle = None
            self.label_encours.config(text="---")
            self.mettre_a_jour_etape_visuelle()
            self.canvas.delete("all")
            self.canvas.create_text(
                450, 225,
                text="En attente de la prochaine commande...",
                font=("Arial", 20),
                fill="#888888"
            )


def main():
    root = tk.Tk()
    app = TestVocal2EtapesStrict(root)
    root.mainloop()


if __name__ == "__main__":
    print("=" * 70)
    print("🎤 TEST VOCAL 2 ÉTAPES STRICT - PADEL STAT")
    print("=" * 70)
    print()
    print("📋 ORDRE STRICT :")
    print()
    print("  ÉTAPE 1 : Catégorie + Joueur(s)")
    print("    • 'point Pierre'")
    print("    • 'faute Lucas'")
    print("    • 'faute provoquée Pierre Lucas'")
    print()
    print("  ÉTAPE 2 : Localisation + Direction")
    print("    • 'service'")
    print("    • 'volée coup droit'")
    print("    • 'fond de court revers'")
    print("    • 'lob'")
    print()
    print("=" * 70)
    print()
    
    main()
