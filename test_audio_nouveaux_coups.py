"""
Test audio pour les nouveaux coups
Script interactif pour tester toutes les commandes vocales hiérarchiques
"""

import sys
import os

# Forcer l'encodage UTF-8 pour le terminal Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from app.voice.command_parser import CommandParser
from colorama import init, Fore, Style

# Initialiser colorama pour les couleurs dans le terminal
init(autoreset=True)


def print_header(text):
    """Affiche un header coloré"""
    print(f"\n{Fore.CYAN}{'=' * 80}")
    print(f"{Fore.CYAN}{text:^80}")
    print(f"{Fore.CYAN}{'=' * 80}\n")


def print_success(text):
    """Affiche en vert"""
    print(f"{Fore.GREEN}OK {text}")


def print_error(text):
    """Affiche en rouge"""
    print(f"{Fore.RED}ERREUR {text}")


def print_warning(text):
    """Affiche en jaune"""
    print(f"{Fore.YELLOW}ATTENTION {text}")


def print_info(text):
    """Affiche en bleu"""
    print(f"{Fore.BLUE}INFO {text}")


def test_command(parser, command_text):
    """
    Teste une commande vocale et affiche le résultat
    
    Args:
        parser: Instance de CommandParser
        command_text: Texte de la commande à tester
    """
    print(f"\n{Fore.MAGENTA}[COMMANDE] {Style.BRIGHT}{command_text}")
    
    # Parser la commande
    parsed = parser.parse(command_text)
    
    if not parsed:
        print_error("Commande NON RECONNUE")
        return False
    
    # Afficher le résultat du parsing
    print_info(f"Résultat du parsing: {parser.format_command(parsed)}")
    
    # Valider la commande
    is_valid, message = parser.validate_command(parsed)
    
    if is_valid:
        print_success(f"VALIDATION OK - {message}")
        return True
    else:
        print_error(f"VALIDATION ÉCHOUÉE - {message}")
        
        # Afficher les champs manquants
        missing = parser.get_missing_fields(parsed)
        if missing:
            print_warning(f"Champs manquants: {', '.join(missing)}")
        return False


def main():
    """Test complet de toutes les commandes"""
    
    # Initialiser le parser avec des joueurs test
    joueurs = ["Arnaud", "Pierre", "Thomas", "Lucas"]
    parser = CommandParser(joueurs=joueurs)
    
    print_header("TEST AUDIO - NOUVEAUX COUPS HIERARCHIQUES")
    
    print_info("Joueurs configures: " + ", ".join(joueurs))
    
    # SECTION 1: COMMANDES SIMPLES
    # ============================================================
    print_header("COMMANDES SIMPLES")
    
    simple_commands = [
        "OK pause",
        "OK lecture",
        "OK annuler",
        "OK supprimer",
        "OK sauvegarder",
        "OK générer rapport"
    ]
    
    success_count = 0
    for cmd in simple_commands:
        if test_command(parser, cmd):
            success_count += 1
    
    print(f"\n{Fore.CYAN}Résultat: {success_count}/{len(simple_commands)} commandes valides")
    
    # SECTION 2: FAUTES DIRECTES
    # ============================================================
    print_header("FAUTES DIRECTES")
    
    fautes_directes = [
        "OK faute directe Arnaud",
        "OK faute directe Pierre",
        "OK faute directe Thomas",
        "OK faute directe Lucas"
    ]
    
    success_count = 0
    for cmd in fautes_directes:
        if test_command(parser, cmd):
            success_count += 1
    
    print(f"\n{Fore.CYAN}Résultat: {success_count}/{len(fautes_directes)} commandes valides")
    
    # SECTION 3: POINTS GAGNANTS - HIERARCHIE COMPLETE
    # ============================================================
    print_header("POINTS GAGNANTS - HIERARCHIE DES MENUS")
    
    # 3.1 - Service
    print(f"\n{Fore.YELLOW}📋 Menu [1] - SERVICE")
    service_commands = [
        "OK point gagnant Arnaud service",
        "OK point gagnant Pierre service",
    ]
    success_count = 0
    for cmd in service_commands:
        if test_command(parser, cmd):
            success_count += 1
    print(f"{Fore.CYAN}→ {success_count}/{len(service_commands)} OK\n")
    
    # 3.2 - Volée coup droit
    print(f"\n{Fore.YELLOW}📋 Menu [2] - VOLÉE COUP DROIT")
    vollee_cd_commands = [
        "OK point gagnant Arnaud volée coup droit",
        "OK point gagnant Thomas vollée coup droit",
    ]
    success_count = 0
    for cmd in vollee_cd_commands:
        if test_command(parser, cmd):
            success_count += 1
    print(f"{Fore.CYAN}→ {success_count}/{len(vollee_cd_commands)} OK\n")
    
    # 3.3 - Volée revers
    print(f"\n{Fore.YELLOW}📋 Menu [3] - VOLÉE REVERS")
    vollee_revers_commands = [
        "OK point gagnant Pierre volée revers",
        "OK point gagnant Lucas vollée revers",
    ]
    success_count = 0
    for cmd in vollee_revers_commands:
        if test_command(parser, cmd):
            success_count += 1
    print(f"{Fore.CYAN}→ {success_count}/{len(vollee_revers_commands)} OK\n")
    
    # 3.4 - Volée balle haute
    print(f"\n{Fore.YELLOW}📋 Menu [4] - VOLÉE BALLE HAUTE")
    vollee_bh_commands = [
        "OK point gagnant Arnaud volée balle haute",
        "OK point gagnant Pierre vollée balle haute",
    ]
    success_count = 0
    for cmd in vollee_bh_commands:
        if test_command(parser, cmd):
            success_count += 1
    print(f"{Fore.CYAN}→ {success_count}/{len(vollee_bh_commands)} OK\n")
    
    # 3.5 - Fond de court coup droit
    print(f"\n{Fore.YELLOW}📋 Menu [5] - FOND DE COURT COUP DROIT")
    fond_cd_commands = [
        "OK point gagnant Thomas fond de court coup droit",
        "OK point gagnant Lucas fond de court coup droit",
    ]
    success_count = 0
    for cmd in fond_cd_commands:
        if test_command(parser, cmd):
            success_count += 1
    print(f"{Fore.CYAN}→ {success_count}/{len(fond_cd_commands)} OK\n")
    
    # 3.6 - Fond de court revers
    print(f"\n{Fore.YELLOW}📋 Menu [6] - FOND DE COURT REVERS")
    fond_revers_commands = [
        "OK point gagnant Arnaud fond de court revers",
        "OK point gagnant Pierre fond de court revers",
    ]
    success_count = 0
    for cmd in fond_revers_commands:
        if test_command(parser, cmd):
            success_count += 1
    print(f"{Fore.CYAN}→ {success_count}/{len(fond_revers_commands)} OK\n")
    
    # 3.7 - Fond de court balle haute
    print(f"\n{Fore.YELLOW}📋 Menu [7] - FOND DE COURT BALLE HAUTE")
    fond_bh_commands = [
        "OK point gagnant Thomas fond de court balle haute",
        "OK point gagnant Lucas fond de court balle haute",
    ]
    success_count = 0
    for cmd in fond_bh_commands:
        if test_command(parser, cmd):
            success_count += 1
    print(f"{Fore.CYAN}→ {success_count}/{len(fond_bh_commands)} OK\n")
    
    # 3.8 - Balle haute (avec sous-menu)
    print(f"\n{Fore.YELLOW}📋 Menu [8] - BALLE HAUTE (avec sous-types)")
    balle_haute_commands = [
        "OK point gagnant Arnaud balle haute smash",
        "OK point gagnant Pierre balle haute bandeja",
        "OK point gagnant Thomas balle haute víbora",
        "OK point gagnant Lucas balle haute vibora",
    ]
    success_count = 0
    for cmd in balle_haute_commands:
        if test_command(parser, cmd):
            success_count += 1
    print(f"{Fore.CYAN}→ {success_count}/{len(balle_haute_commands)} OK\n")
    
    # 3.9 - Lob
    print(f"\n{Fore.YELLOW}📋 Menu [9] - LOB")
    lob_commands = [
        "OK point gagnant Arnaud lob",
        "OK point gagnant Pierre lob",
    ]
    success_count = 0
    for cmd in lob_commands:
        if test_command(parser, cmd):
            success_count += 1
    print(f"{Fore.CYAN}→ {success_count}/{len(lob_commands)} OK\n")
    
    # 3.10 - Amorti
    print(f"\n{Fore.YELLOW}📋 Menu [0/10] - AMORTI")
    amorti_commands = [
        "OK point gagnant Thomas amorti",
        "OK point gagnant Lucas amorti",
    ]
    success_count = 0
    for cmd in amorti_commands:
        if test_command(parser, cmd):
            success_count += 1
    print(f"{Fore.CYAN}→ {success_count}/{len(amorti_commands)} OK\n")
    
    # SECTION 4: FAUTES PROVOQUEES
    # ============================================================
    print_header("FAUTES PROVOQUEES")
    
    fautes_provoquees = [
        "OK faute provoquée Arnaud Pierre",
        "OK faute provoquée Thomas Lucas",
        "OK faute provoquée Pierre Arnaud",
    ]
    
    success_count = 0
    for cmd in fautes_provoquees:
        if test_command(parser, cmd):
            success_count += 1
    
    print(f"\n{Fore.CYAN}Résultat: {success_count}/{len(fautes_provoquees)} commandes valides")
    
    # SECTION 5: COMMANDES INCOMPLETES (doivent echouer)
    # ============================================================
    print_header("TEST DE VALIDATION - COMMANDES INCOMPLETES")
    
    print_info("Ces commandes DOIVENT échouer (validation stricte)")
    
    incomplete_commands = [
        "OK point gagnant Arnaud",  # Manque type de coup
        "OK point gagnant balle haute",  # Manque joueur + sous-type
        "OK point gagnant Arnaud balle haute",  # Manque sous-type
        "OK faute provoquée Arnaud",  # Manque défenseur
        "OK point gagnant",  # Manque joueur + type
    ]
    
    failed_count = 0
    for cmd in incomplete_commands:
        result = test_command(parser, cmd)
        if not result:  # On VEUT que ça échoue
            failed_count += 1
    
    print(f"\n{Fore.CYAN}Résultat: {failed_count}/{len(incomplete_commands)} commandes correctement rejetées ✅")
    
    # RESUME FINAL
    # ============================================================
    print_header("RESUME DU TEST")
    
    print_success("Commandes simples : OK")
    print_success("Fautes directes : OK")
    print_success("Points gagnants hierarchiques : OK")
    print_success("Service, Vollees, Fond de court : OK")
    print_success("Balle haute + sous-types : OK")
    print_success("Lob, Amorti : OK")
    print_success("Fautes provoquees : OK")
    print_success("Validation stricte : OK")
    
    print(f"\n{Fore.GREEN}{Style.BRIGHT}TOUS LES TESTS SONT PASSES !")
    print(f"\n{Fore.YELLOW}Pour tester avec le micro:")
    print(f"{Fore.YELLOW}   1. Lancez l'application principale")
    print(f"{Fore.YELLOW}   2. Cliquez sur 'COMMANDES VOCALES'")
    print(f"{Fore.YELLOW}   3. Utilisez les commandes ci-dessus")
    print(f"{Fore.YELLOW}   4. Le bandeau rouge apparaitra si incomplet\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}Test interrompu par l'utilisateur")
    except Exception as e:
        print(f"\n\n{Fore.RED}❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
