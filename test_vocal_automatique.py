"""
Script de test interactif pour les commandes vocales
Utilise Windows Speech Recognition pour tester automatiquement
"""

import speech_recognition as sr
import webbrowser
import os
import json
from pathlib import Path

# Liste des commandes à tester
JOUEURS = ['joueur1', 'joueur2']
TYPES_COUPS = [
    'service',
    'volée coup droit',
    'volée revers',
    'volée balle haute',
    'fond de court coup droit',
    'fond de court revers',
    'fond de court balle haute',
    'lob'
]

def generer_commandes():
    """Génère toutes les commandes à tester"""
    commandes = {
        'point': [],
        'faute': [],
        'faute_provoquee': []
    }
    
    # POINT
    for joueur in JOUEURS:
        for coup in TYPES_COUPS:
            commandes['point'].append(f"point {joueur} {coup}")
    
    # FAUTE
    for joueur in JOUEURS:
        for coup in TYPES_COUPS:
            commandes['faute'].append(f"faute {joueur} {coup}")
    
    # FAUTE PROVOQUÉE
    for provoquant in JOUEURS:
        for subit in JOUEURS:
            if provoquant != subit:
                for coup in TYPES_COUPS:
                    commandes['faute_provoquee'].append(f"faute provoquée {provoquant} {subit} {coup}")
    
    return commandes

def normaliser_texte(texte):
    """Normalise le texte pour comparaison - accepte TOUTES les variantes réelles"""
    texte = texte.lower().strip()
    
    # === CATÉGORIES PRINCIPALES ===
    # "point" et toutes ses variantes
    texte = texte.replace('points', 'point')
    texte = texte.replace('foot', 'point')
    texte = texte.replace('ford', 'point')
    texte = texte.replace('photos', 'point')
    
    # "faute" et toutes ses variantes
    texte = texte.replace('fautes', 'faute')
    texte = texte.replace('faut', 'faute')
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
    texte = texte.replace('joueur à un', 'joueur2')
    
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
    texte = texte.replace('coup', 'coup droit')  # Si isolé après volée/fond
    
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
    # Supprimer les mots parasites en fin
    texte = texte.replace(' à l\'autre', '')
    texte = texte.replace(' de', '')
    
    # Supprimer les déterminants inutiles
    texte = texte.replace('faute toujours un', 'faute joueur1')
    texte = texte.replace('faute dire', 'faute')
    texte = texte.replace('point genre', 'point')
    
    # Nettoyer les espaces multiples
    while '  ' in texte:
        texte = texte.replace('  ', ' ')
    
    return texte.strip()

def mode_enregistrement():
    """Mode spécial : enregistre TOUTES les transcriptions pour analyse"""
    
    print("\n" + "=" * 70)
    print("📝 MODE ENREGISTREMENT - Collecte des transcriptions")
    print("=" * 70)
    print("\n💡 Testez toutes les commandes que vous voulez")
    print("💡 Toutes les transcriptions seront sauvegardées")
    print("💡 À la fin, on adaptera la normalisation\n")
    
    # Initialiser le recognizer
    r = sr.Recognizer()
    
    print("📊 Calibrage du microphone...")
    with sr.Microphone() as source:
        r.adjust_for_ambient_noise(source, duration=1)
    print("✅ Calibrage terminé\n")
    
    transcriptions = []
    
    print("🎯 Appuyez sur [Entrée] pour enregistrer une commande")
    print("🎯 Tapez 'fin' pour terminer et sauvegarder\n")
    
    compteur = 0
    
    while True:
        choix = input(f"\n[{compteur+1}] ➤ [Entrée=enregistrer / fin]: ").strip().lower()
        
        if choix == 'fin':
            break
        
        print(f"\n🎤 [{compteur+1}] En écoute...")
        
        with sr.Microphone() as source:
            try:
                audio = r.listen(source, timeout=5, phrase_time_limit=10)
                print("🔄 Transcription...")
                
                try:
                    texte = r.recognize_google(audio, language="fr-FR")
                    texte_normalise = normaliser_texte(texte)
                    
                    print(f"\n✅ ORIGINAL    : '{texte}'")
                    print(f"✅ NORMALISÉ   : '{texte_normalise}'")
                    
                    transcriptions.append({
                        'numero': compteur + 1,
                        'original': texte,
                        'normalise': texte_normalise
                    })
                    
                    compteur += 1
                    
                except sr.UnknownValueError:
                    print("❌ Impossible de comprendre")
                except sr.RequestError as e:
                    print(f"❌ Erreur: {e}")
                    
            except sr.WaitTimeoutError:
                print("⏱️ Timeout")
            except Exception as e:
                print(f"❌ Erreur: {e}")
    
    # Sauvegarder et afficher
    print("\n" + "=" * 70)
    print(f"📊 RÉSUMÉ - {len(transcriptions)} transcriptions enregistrées")
    print("=" * 70)
    
    for t in transcriptions:
        print(f"\n[{t['numero']}]")
        print(f"  ORIGINAL    : {t['original']}")
        print(f"  NORMALISÉ   : {t['normalise']}")
    
    # Sauvegarder
    fichier = Path("data") / "transcriptions_collecte.json"
    fichier.parent.mkdir(exist_ok=True)
    
    with open(fichier, 'w', encoding='utf-8') as f:
        json.dump(transcriptions, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Transcriptions sauvegardées dans {fichier}")
    print("\n📋 Copiez maintenant toute la sortie et dites-moi quelles sont bonnes !")
    
    return transcriptions

def test_reconnaissance_vocale():
    """Test interactif de reconnaissance vocale"""
    
    print("\n" + "=" * 70)
    print("🎤 TEST INTERACTIF DES COMMANDES VOCALES")
    print("=" * 70)
    
    # Générer les commandes
    commandes = generer_commandes()
    total = sum(len(cmds) for cmds in commandes.values())
    
    print(f"\n📊 Total de commandes à tester : {total}")
    print(f"   - POINT : {len(commandes['point'])}")
    print(f"   - FAUTE : {len(commandes['faute'])}")
    print(f"   - FAUTE PROVOQUÉE : {len(commandes['faute_provoquee'])}")
    
    # Initialiser le recognizer
    r = sr.Recognizer()
    
    print("\n📊 Calibrage du microphone...")
    with sr.Microphone() as source:
        r.adjust_for_ambient_noise(source, duration=1)
    print("✅ Calibrage terminé\n")
    
    # Ouvrir le HTML
    html_path = Path(__file__).parent / "test_vocal_interactif.html"
    if html_path.exists():
        print(f"🌐 Ouverture de {html_path.name}...")
        webbrowser.open(f"file://{html_path.absolute()}")
    
    # Statistiques
    stats = {
        'total_testes': 0,
        'reussis': 0,
        'echecs': 0,
        'resultats': []
    }
    
    print("\n" + "=" * 70)
    print("🎯 MODE TEST - Dites vos commandes !")
    print("=" * 70)
    print("\nFormat attendu :")
    print("  - point joueur1 service")
    print("  - faute joueur2 volée coup droit")
    print("  - faute provoquée joueur1 joueur2 lob")
    print("\n💡 Appuyez sur [Entrée] pour commencer un test")
    print("💡 Tapez 'stats' pour voir les statistiques")
    print("💡 Tapez 'q' pour quitter\n")
    
    while True:
        choix = input("➤ [Entrée=tester / stats / q]: ").strip().lower()
        
        if choix == 'q':
            break
        
        if choix == 'stats':
            afficher_stats(stats)
            continue
        
        # Lancer un test
        print("\n🎤 En écoute... Dites votre commande !")
        
        with sr.Microphone() as source:
            try:
                audio = r.listen(source, timeout=5, phrase_time_limit=10)
                print("🔄 Transcription...")
                
                # Essayer Google (meilleur en français)
                try:
                    texte = r.recognize_google(audio, language="fr-FR")
                    texte_normalise = normaliser_texte(texte)
                    
                    print("\n" + "=" * 70)
                    print("✅ RECONNU:")
                    print("=" * 70)
                    print(f"  '{texte}'")
                    print("=" * 70)
                    
                    # Vérifier si c'est une commande valide
                    valide = False
                    categorie = None
                    
                    for cat, cmds in commandes.items():
                        for cmd in cmds:
                            if normaliser_texte(cmd) == texte_normalise:
                                valide = True
                                categorie = cat
                                break
                        if valide:
                            break
                    
                    if valide:
                        print(f"✅ Commande VALIDE ({categorie.upper()})")
                        stats['reussis'] += 1
                    else:
                        print("⚠️ Commande NON RECONNUE dans la liste")
                        print(f"💡 Suggestion : Vérifiez l'orthographe")
                        stats['echecs'] += 1
                    
                    stats['total_testes'] += 1
                    stats['resultats'].append({
                        'texte': texte,
                        'valide': valide,
                        'categorie': categorie
                    })
                    
                except sr.UnknownValueError:
                    print("❌ Impossible de comprendre l'audio")
                    stats['echecs'] += 1
                    stats['total_testes'] += 1
                    
                except sr.RequestError as e:
                    print(f"❌ Erreur service Google: {e}")
                    
            except sr.WaitTimeoutError:
                print("⏱️ Timeout - rien détecté")
            except Exception as e:
                print(f"❌ Erreur: {e}")
    
    # Afficher les stats finales
    print("\n" + "=" * 70)
    print("📊 STATISTIQUES FINALES")
    print("=" * 70)
    afficher_stats(stats)
    
    # Sauvegarder les résultats
    sauvegarder_resultats(stats)

def afficher_stats(stats):
    """Affiche les statistiques"""
    if stats['total_testes'] == 0:
        print("\n❌ Aucun test effectué")
        return
    
    taux_reussite = (stats['reussis'] / stats['total_testes']) * 100
    
    print(f"\n  Total testés    : {stats['total_testes']}")
    print(f"  ✅ Réussis      : {stats['reussis']}")
    print(f"  ❌ Échecs       : {stats['echecs']}")
    print(f"  📊 Taux réussite: {taux_reussite:.1f}%")
    
    if stats['resultats']:
        print("\n📝 Derniers résultats :")
        for i, res in enumerate(stats['resultats'][-5:], 1):
            statut = "✅" if res['valide'] else "❌"
            cat = f" ({res['categorie']})" if res['valide'] else ""
            print(f"  {i}. {statut} {res['texte']}{cat}")

def sauvegarder_resultats(stats):
    """Sauvegarde les résultats dans un fichier JSON"""
    if stats['total_testes'] == 0:
        return
    
    fichier = Path("data") / "test_vocal_resultats.json"
    fichier.parent.mkdir(exist_ok=True)
    
    with open(fichier, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Résultats sauvegardés dans {fichier}")

if __name__ == "__main__":
    try:
        print("\n🔍 Vérification des dépendances...")
        import speech_recognition as sr
        print("✅ speech_recognition installé")
        
        print("\n" + "=" * 70)
        print("Choisissez le mode :")
        print("=" * 70)
        print("1. Mode ENREGISTREMENT (collecte toutes les transcriptions)")
        print("2. Mode TEST (test interactif avec validation)")
        print("=" * 70)
        
        choix = input("\n➤ Votre choix [1/2] : ").strip()
        
        if choix == "1":
            mode_enregistrement()
        else:
            test_reconnaissance_vocale()
        
    except ImportError:
        print("\n❌ Module 'speech_recognition' manquant")
        print("\n📦 Installation requise:")
        print("   pip install SpeechRecognition pyaudio")
    except KeyboardInterrupt:
        print("\n\n👋 Test interrompu par l'utilisateur")
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
