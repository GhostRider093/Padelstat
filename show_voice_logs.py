"""
Utilitaire pour afficher les logs de commandes vocales
"""

import os
import sys
from datetime import datetime

LOG_FILE = "data/voice_commands.log"

def show_logs(last_n: int = None, search: str = None):
    """
    Affiche les logs de commandes vocales
    
    Args:
        last_n: Afficher les N dernières commandes
        search: Rechercher un mot dans les logs
    """
    if not os.path.exists(LOG_FILE):
        print(f"❌ Fichier de log non trouvé: {LOG_FILE}")
        print("   Lancez l'application avec les commandes vocales activées pour créer des logs.")
        return
    
    print("\n" + "=" * 80)
    print("📋 LOGS DES COMMANDES VOCALES - PADEL STAT")
    print("=" * 80)
    
    with open(LOG_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Compter les commandes
    command_count = content.count("COMMANDE #")
    
    print(f"\n📊 Total: {command_count} commandes enregistrées")
    print(f"📁 Fichier: {LOG_FILE}")
    print(f"📏 Taille: {len(content)} caractères\n")
    
    if search:
        print(f"🔍 Recherche: '{search}'")
        print("=" * 80)
        
        # Filtrer les lignes contenant le terme
        lines = content.split('\n')
        found = False
        for i, line in enumerate(lines):
            if search.lower() in line.lower():
                found = True
                # Afficher 3 lignes avant et après pour le contexte
                start = max(0, i - 3)
                end = min(len(lines), i + 4)
                for j in range(start, end):
                    if j == i:
                        print(f">>> {lines[j]}")
                    else:
                        print(f"    {lines[j]}")
                print("-" * 80)
        
        if not found:
            print(f"❌ Aucun résultat trouvé pour '{search}'")
    
    elif last_n:
        print(f"📜 Affichage des {last_n} dernières commandes:")
        print("=" * 80)
        
        # Découper en blocs de commandes
        commands = content.split("COMMANDE #")[1:]  # Ignorer le header
        
        # Prendre les N dernières
        to_show = commands[-last_n:] if len(commands) > last_n else commands
        
        for i, cmd in enumerate(to_show, start=max(1, command_count - last_n + 1)):
            print(f"COMMANDE #{i}{cmd}")
            print("")
    
    else:
        # Afficher tout
        print("📜 Affichage complet:")
        print("=" * 80)
        print(content)
    
    print("\n" + "=" * 80)
    print("✅ Fin des logs")
    print("=" * 80 + "\n")


def clear_logs():
    """Efface les logs"""
    if os.path.exists(LOG_FILE):
        backup = LOG_FILE + f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        os.rename(LOG_FILE, backup)
        print(f"✅ Logs déplacés vers: {backup}")
        print(f"💡 Nouveau fichier sera créé au prochain lancement")
    else:
        print(f"❌ Aucun fichier de log à effacer")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Afficher les logs de commandes vocales")
    parser.add_argument("-n", "--last", type=int, help="Afficher les N dernières commandes")
    parser.add_argument("-s", "--search", type=str, help="Rechercher un mot dans les logs")
    parser.add_argument("-c", "--clear", action="store_true", help="Effacer les logs (backup automatique)")
    
    args = parser.parse_args()
    
    if args.clear:
        clear_logs()
    else:
        show_logs(last_n=args.last, search=args.search)
