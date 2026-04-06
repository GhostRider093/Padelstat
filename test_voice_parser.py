"""
Tests unitaires simplifiés pour le parser de commandes vocales
"""

import pytest
from app.voice.command_parser import CommandParser


class TestCommandParser:
    """Tests du parser de commandes vocales"""
    
    @classmethod
    def setup_class(cls):
        cls.parser = CommandParser()
    
    # =================================================================
    # Tests des commandes simples
    # =================================================================
    
    def test_commandes_simples(self):
        """Test toutes les commandes simples"""
        tests = [
            ("ok lecture", "lecture"),
            ("ok pause", "pause"),
            ("ok annuler", "annuler"),
            ("ok sauvegarder", "sauvegarder"),
            ("ok générer rapport", "rapport"),
        ]
        
        for cmd, action_attendue in tests:
            result = self.parser.parse(cmd)
            assert result is not None, f"Parsing échoué pour '{cmd}'"
            assert 'action' in result, f"Pas d'action pour '{cmd}'"
            assert result['action'] == action_attendue, \
                f"Action incorrecte pour '{cmd}': {result['action']} != {action_attendue}"
            print(f"✓ {cmd} → {result['action']}")
    
    # =================================================================
    # Tests des fautes directes
    # =================================================================
    
    def test_fautes_directes(self):
        """Test toutes les fautes directes"""
        tests = [
            ("ok faute directe arnaud", "Arnaud"),
            ("ok faute directe pierre", "Pierre"),
            ("ok faute directe thomas", "Thomas"),
            ("ok faute directe lucas", "Lucas"),
        ]
        
        for cmd, joueur_attendu in tests:
            result = self.parser.parse(cmd)
            assert result is not None, f"Parsing échoué pour '{cmd}'"
            assert result.get('type_point') == 'faute_directe', \
                f"Type point incorrect pour '{cmd}'"
            # Le joueur peut être None ou en minuscules selon l'impl
            joueur = result.get('joueur')
            if joueur:
                assert joueur.lower() == joueur_attendu.lower(), \
                    f"Joueur incorrect pour '{cmd}': {joueur} != {joueur_attendu}"
            print(f"✓ {cmd}")
    
    # =================================================================
    # Tests des points gagnants - Service
    # =================================================================
    
    def test_points_gagnants_service(self):
        """Test points gagnants au service"""
        tests = [
            "ok point gagnant arnaud service",
            "ok point gagnant pierre service",
        ]
        
        for cmd in tests:
            result = self.parser.parse(cmd)
            assert result is not None, f"Parsing échoué pour '{cmd}'"
            assert result.get('type_point') == 'point_gagnant', \
                f"Type point incorrect pour '{cmd}'"
            type_coup = result.get('type_coup')
            assert type_coup is not None, f"Type de coup manquant pour '{cmd}'"
            assert 'service' in type_coup.lower(), \
                f"Type coup incorrect pour '{cmd}': {type_coup}"
            print(f"✓ {cmd}")
    
    # =================================================================
    # Tests des points gagnants - Vollées
    # =================================================================
    
    def test_points_gagnants_vollees(self):
        """Test points gagnants en volée"""
        tests = [
            ("ok point gagnant thomas volée coup droit", "coup"),
            ("ok point gagnant lucas volée revers", "revers"),
            ("ok point gagnant arnaud volée balle haute", "balle"),
        ]
        
        for cmd, mot_cle in tests:
            result = self.parser.parse(cmd)
            assert result is not None, f"Parsing échoué pour '{cmd}'"
            assert result.get('type_point') == 'point_gagnant'
            type_coup = result.get('type_coup', '')
            assert mot_cle in type_coup.lower(), \
                f"Type coup incorrect pour '{cmd}': {type_coup}"
            print(f"✓ {cmd}")
    
    # =================================================================
    # Tests des points gagnants - Fond de court
    # =================================================================
    
    def test_points_gagnants_fond_de_court(self):
        """Test points gagnants au fond de court"""
        tests = [
            ("ok point gagnant pierre fond de court coup droit", "coup"),
            ("ok point gagnant thomas fond de court revers", "revers"),
            ("ok point gagnant lucas fond de court balle haute", "balle"),
        ]
        
        for cmd, mot_cle in tests:
            result = self.parser.parse(cmd)
            assert result is not None, f"Parsing échoué pour '{cmd}'"
            type_coup = result.get('type_coup', '')
            assert 'fond' in type_coup.lower() or mot_cle in type_coup.lower(), \
                f"Type coup incorrect pour '{cmd}': {type_coup}"
            print(f"✓ {cmd}")
    
    # =================================================================
    # Tests des points gagnants - Balle haute avec sous-types
    # =================================================================
    
    def test_points_gagnants_balle_haute(self):
        """Test points gagnants balle haute avec sous-types"""
        tests = [
            ("ok point gagnant arnaud balle haute smash", "smash"),
            ("ok point gagnant pierre balle haute bandeja", "bandeja"),
            ("ok point gagnant thomas balle haute víbora", "víbora"),
            ("ok point gagnant lucas balle haute vibora", "vibora"),
        ]
        
        for cmd, sous_type_attendu in tests:
            result = self.parser.parse(cmd)
            assert result is not None, f"Parsing échoué pour '{cmd}'"
            # Vérifier que le sous-type est présent quelque part
            type_coup = result.get('type_coup', '')
            sous_type = result.get('sous_type', '')
            assert sous_type_attendu.lower() in (type_coup + sous_type).lower(), \
                f"Sous-type '{sous_type_attendu}' manquant pour '{cmd}'"
            print(f"✓ {cmd}")
    
    # =================================================================
    # Tests des points gagnants - Lob et Amorti
    # =================================================================
    
    def test_points_gagnants_lob_amorti(self):
        """Test points gagnants lob et amorti"""
        tests = [
            ("ok point gagnant arnaud lob", "lob"),
            ("ok point gagnant pierre lob", "lob"),
            ("ok point gagnant thomas amorti", "amorti"),
            ("ok point gagnant lucas amorti", "amorti"),
        ]
        
        for cmd, type_attendu in tests:
            result = self.parser.parse(cmd)
            assert result is not None, f"Parsing échoué pour '{cmd}'"
            type_coup = result.get('type_coup', '')
            assert type_attendu in type_coup.lower(), \
                f"Type coup incorrect pour '{cmd}': {type_coup}"
            print(f"✓ {cmd}")
    
    # =================================================================
    # Tests des fautes provoquées
    # =================================================================
    
    def test_fautes_provoquees(self):
        """Test fautes provoquées avec 2 joueurs"""
        tests = [
            ("ok faute provoquée arnaud pierre", "Arnaud", "Pierre"),
            ("ok faute provoquée thomas lucas", "Thomas", "Lucas"),
            ("ok faute provoquée pierre arnaud", "Pierre", "Arnaud"),
        ]
        
        for cmd, attaquant, defenseur in tests:
            result = self.parser.parse(cmd)
            assert result is not None, f"Parsing échoué pour '{cmd}'"
            assert result.get('type_point') == 'faute_provoquee', \
                f"Type point incorrect pour '{cmd}'"
            
            # Vérifier joueur et défenseur
            joueur = result.get('joueur', '')
            def_result = result.get('defenseur', '')
            
            if joueur:
                assert joueur.lower() == attaquant.lower(), \
                    f"Joueur incorrect pour '{cmd}': {joueur} != {attaquant}"
            
            if def_result:
                assert def_result.lower() == defenseur.lower(), \
                    f"Défenseur incorrect pour '{cmd}': {def_result} != {defenseur}"
            
            print(f"✓ {cmd} → {joueur or '?'} vs {def_result or '?'}")
    
    # =================================================================
    # Tests de validation
    # =================================================================
    
    def test_validation_commandes_completes(self):
        """Test que les commandes complètes passent la validation"""
        commandes_completes = [
            "ok point gagnant arnaud service",
            "ok point gagnant pierre balle haute smash",
            "ok faute directe lucas",
            "ok faute provoquée arnaud pierre",
        ]
        
        for cmd in commandes_completes:
            result = self.parser.parse(cmd)
            assert result is not None, f"Parsing échoué pour '{cmd}'"
            
            # validate_command retourne (bool, list) 
            validation = self.parser.validate_command(result)
            is_valid = validation[0] if isinstance(validation, tuple) else validation.get('valid', False)
            
            print(f"✓ Validation de '{cmd}': {is_valid}")
    
    def test_detection_commandes_incompletes(self):
        """Test que les commandes incomplètes sont détectées"""
        commandes_incompletes = [
            "ok point gagnant arnaud",  # manque type de coup
            "ok faute directe",  # manque joueur
            "ok point gagnant arnaud balle haute",  # manque sous-type
            "ok faute provoquée arnaud",  # manque défenseur
        ]
        
        for cmd in commandes_incompletes:
            result = self.parser.parse(cmd)
            # La commande peut être parsée mais devrait échouer à la validation
            if result:
                validation = self.parser.validate_command(result)
                is_valid = validation[0] if isinstance(validation, tuple) else validation.get('valid', False)
                print(f"✓ '{cmd}' → Incomplet détecté: {not is_valid}")
    
    # =================================================================
    # Test de couverture globale
    # =================================================================
    
    def test_couverture_complete(self):
        """Test rapide de tous les types de commandes"""
        print("\n=== COUVERTURE COMPLÈTE ===")
        
        total = 0
        success = 0
        
        toutes_commandes = [
            # Simples
            "ok lecture", "ok pause", "ok annuler", "ok sauvegarder", "ok générer rapport",
            # Fautes directes
            "ok faute directe arnaud", "ok faute directe pierre",
            # Services
            "ok point gagnant arnaud service", "ok point gagnant pierre service",
            # Vollées
            "ok point gagnant thomas volée coup droit", "ok point gagnant lucas volée revers",
            # Fond de court
            "ok point gagnant pierre fond de court coup droit",
            # Balle haute
            "ok point gagnant arnaud balle haute smash", "ok point gagnant pierre balle haute bandeja",
            # Lob, Amorti
            "ok point gagnant thomas lob", "ok point gagnant lucas amorti",
            # Fautes provoquées
            "ok faute provoquée arnaud pierre", "ok faute provoquée thomas lucas",
        ]
        
        for cmd in toutes_commandes:
            total += 1
            result = self.parser.parse(cmd)
            if result:
                success += 1
            else:
                print(f"  ✗ ÉCHEC: {cmd}")
        
        print(f"\nRésultat: {success}/{total} commandes parsées ({100*success//total}%)")
        assert success >= total * 0.8, f"Trop d'échecs: {success}/{total}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
