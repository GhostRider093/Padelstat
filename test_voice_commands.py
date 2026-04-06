"""
Tests unitaires pour les commandes vocales - Padel Stats
Test toutes les commandes vocales disponibles dans le système
"""

import pytest
from app.voice.command_parser import CommandParser


class TestVoiceCommands:
    """Tests pour toutes les commandes vocales"""
    
    @classmethod
    def setup_class(cls):
        """Initialisation du parser pour tous les tests"""
        cls.parser = CommandParser()
    
    # ============================================================
    # TESTS DES COMMANDES SIMPLES
    # ============================================================
    
    def test_commande_lecture(self):
        """Test: OK lecture"""
        result = self.parser.parse("ok lecture")
        assert result is not None
        assert result['action'] == 'lecture'
    
    def test_commande_pause(self):
        """Test: OK pause"""
        result = self.parser.parse("ok pause")
        assert result is not None
        assert result['action'] == 'pause'
    
    def test_commande_annuler(self):
        """Test: OK annuler"""
        result = self.parser.parse("ok annuler")
        assert result is not None
        assert result['action'] == 'annuler'
    
    def test_commande_supprimer(self):
        """Test: OK supprimer"""
        result = self.parser.parse("ok supprimer")
        assert result is not None
        assert result['action'] == 'annuler'  # supprimer est mappé à annuler
    
    def test_commande_sauvegarder(self):
        """Test: OK sauvegarder"""
        result = self.parser.parse("ok sauvegarder")
        assert result is not None
        assert result['action'] == 'sauvegarder'
    
    def test_commande_rapport(self):
        """Test: OK générer rapport"""
        result = self.parser.parse("ok générer rapport")
        assert result is not None
        assert result['action'] == 'rapport'
    
    # ============================================================
    # TESTS DES FAUTES DIRECTES
    # ============================================================
    
    def test_faute_directe_arnaud(self):
        """Test: OK faute directe Arnaud"""
        result = self.parser.parse("ok faute directe arnaud")
        assert result is not None
        assert result['type_point'] == 'faute_directe'
        assert result['joueur'] == 'Arnaud'
        
        # Validation stricte
        validation = self.parser.validate_command(result)
        assert validation[0] is True  # validate_command retourne un tuple (bool, list)
    
    def test_faute_directe_pierre(self):
        """Test: OK faute directe Pierre"""
        result = self.parser.parse("ok faute directe pierre")
        assert result is not None
        assert result['type_point'] == 'faute_directe'
        assert result['joueur'] == 'Pierre'
    
    def test_faute_directe_thomas(self):
        """Test: OK faute directe Thomas"""
        result = self.parser.parse("ok faute directe thomas")
        assert result is not None
        assert result['joueur'] == 'Thomas'
    
    def test_faute_directe_lucas(self):
        """Test: OK faute directe Lucas"""
        result = self.parser.parse("ok faute directe lucas")
        assert result is not None
        assert result['joueur'] == 'Lucas'
    
    # ============================================================
    # TESTS DES POINTS GAGNANTS - SERVICE
    # ============================================================
    
    def test_point_gagnant_service_arnaud(self):
        """Test: OK point gagnant Arnaud service"""
        result = self.parser.parse("ok point gagnant arnaud service")
        assert result is not None
        assert result['type'] == 'point_gagnant'
        assert result['joueur'] == 'Arnaud'
        assert result['type_coup'] == 'service'
        
        validation = self.parser.validate_command(result)
        assert validation['valid'] is True
    
    def test_point_gagnant_service_pierre(self):
        """Test: OK point gagnant Pierre service"""
        result = self.parser.parse("ok point gagnant pierre service")
        assert result is not None
        assert result['joueur'] == 'Pierre'
        assert result['type_coup'] == 'service'
    
    # ============================================================
    # TESTS DES POINTS GAGNANTS - VOLLÉES
    # ============================================================
    
    def test_point_gagnant_vollee_coup_droit(self):
        """Test: OK point gagnant Thomas volée coup droit"""
        result = self.parser.parse("ok point gagnant thomas volée coup droit")
        assert result is not None
        assert result['joueur'] == 'Thomas'
        assert result['type_coup'] == 'volée coup droit'
        
        validation = self.parser.validate_command(result)
        assert validation['valid'] is True
    
    def test_point_gagnant_vollee_revers(self):
        """Test: OK point gagnant Lucas volée revers"""
        result = self.parser.parse("ok point gagnant lucas volée revers")
        assert result is not None
        assert result['joueur'] == 'Lucas'
        assert result['type_coup'] == 'volée revers'
    
    def test_point_gagnant_vollee_balle_haute(self):
        """Test: OK point gagnant Arnaud volée balle haute"""
        result = self.parser.parse("ok point gagnant arnaud volée balle haute")
        assert result is not None
        assert result['joueur'] == 'Arnaud'
        assert result['type_coup'] == 'volée balle haute'
    
    # ============================================================
    # TESTS DES POINTS GAGNANTS - FOND DE COURT
    # ============================================================
    
    def test_point_gagnant_fond_coup_droit(self):
        """Test: OK point gagnant Pierre fond de court coup droit"""
        result = self.parser.parse("ok point gagnant pierre fond de court coup droit")
        assert result is not None
        assert result['joueur'] == 'Pierre'
        assert result['type_coup'] == 'fond de court coup droit'
        
        validation = self.parser.validate_command(result)
        assert validation['valid'] is True
    
    def test_point_gagnant_fond_revers(self):
        """Test: OK point gagnant Thomas fond de court revers"""
        result = self.parser.parse("ok point gagnant thomas fond de court revers")
        assert result is not None
        assert result['joueur'] == 'Thomas'
        assert result['type_coup'] == 'fond de court revers'
    
    def test_point_gagnant_fond_balle_haute(self):
        """Test: OK point gagnant Lucas fond de court balle haute"""
        result = self.parser.parse("ok point gagnant lucas fond de court balle haute")
        assert result is not None
        assert result['joueur'] == 'Lucas'
        assert result['type_coup'] == 'fond de court balle haute'
    
    # ============================================================
    # TESTS DES POINTS GAGNANTS - BALLE HAUTE (avec sous-types)
    # ============================================================
    
    def test_point_gagnant_balle_haute_smash(self):
        """Test: OK point gagnant Arnaud balle haute smash"""
        result = self.parser.parse("ok point gagnant arnaud balle haute smash")
        assert result is not None
        assert result['joueur'] == 'Arnaud'
        assert result['type_coup'] == 'balle haute'
        assert result['sous_type'] == 'smash'
        
        validation = self.parser.validate_command(result)
        assert validation['valid'] is True
    
    def test_point_gagnant_balle_haute_bandeja(self):
        """Test: OK point gagnant Pierre balle haute bandeja"""
        result = self.parser.parse("ok point gagnant pierre balle haute bandeja")
        assert result is not None
        assert result['joueur'] == 'Pierre'
        assert result['type_coup'] == 'balle haute'
        assert result['sous_type'] == 'bandeja'
    
    def test_point_gagnant_balle_haute_vibora(self):
        """Test: OK point gagnant Thomas balle haute víbora"""
        result = self.parser.parse("ok point gagnant thomas balle haute víbora")
        assert result is not None
        assert result['joueur'] == 'Thomas'
        assert result['type_coup'] == 'balle haute'
        assert result['sous_type'] == 'víbora'
    
    # ============================================================
    # TESTS DES POINTS GAGNANTS - LOB
    # ============================================================
    
    def test_point_gagnant_lob_arnaud(self):
        """Test: OK point gagnant Arnaud lob"""
        result = self.parser.parse("ok point gagnant arnaud lob")
        assert result is not None
        assert result['joueur'] == 'Arnaud'
        assert result['type_coup'] == 'lob'
        
        validation = self.parser.validate_command(result)
        assert validation['valid'] is True
    
    def test_point_gagnant_lob_pierre(self):
        """Test: OK point gagnant Pierre lob"""
        result = self.parser.parse("ok point gagnant pierre lob")
        assert result is not None
        assert result['joueur'] == 'Pierre'
        assert result['type_coup'] == 'lob'
    
    # ============================================================
    # TESTS DES POINTS GAGNANTS - AMORTI
    # ============================================================
    
    def test_point_gagnant_amorti_thomas(self):
        """Test: OK point gagnant Thomas amorti"""
        result = self.parser.parse("ok point gagnant thomas amorti")
        assert result is not None
        assert result['joueur'] == 'Thomas'
        assert result['type_coup'] == 'amorti'
        
        validation = self.parser.validate_command(result)
        assert validation['valid'] is True
    
    def test_point_gagnant_amorti_lucas(self):
        """Test: OK point gagnant Lucas amorti"""
        result = self.parser.parse("ok point gagnant lucas amorti")
        assert result is not None
        assert result['joueur'] == 'Lucas'
        assert result['type_coup'] == 'amorti'
    
    # ============================================================
    # TESTS DES FAUTES PROVOQUÉES
    # ============================================================
    
    def test_faute_provoquee_arnaud_pierre(self):
        """Test: OK faute provoquée Arnaud Pierre"""
        result = self.parser.parse("ok faute provoquée arnaud pierre")
        assert result is not None
        assert result['type'] == 'faute_provoquee'
        assert result['joueur'] == 'Arnaud'
        assert result['defenseur'] == 'Pierre'
        
        validation = self.parser.validate_command(result)
        assert validation['valid'] is True
    
    def test_faute_provoquee_thomas_lucas(self):
        """Test: OK faute provoquée Thomas Lucas"""
        result = self.parser.parse("ok faute provoquée thomas lucas")
        assert result is not None
        assert result['joueur'] == 'Thomas'
        assert result['defenseur'] == 'Lucas'
    
    def test_faute_provoquee_pierre_arnaud(self):
        """Test: OK faute provoquée Pierre Arnaud"""
        result = self.parser.parse("ok faute provoquée pierre arnaud")
        assert result is not None
        assert result['joueur'] == 'Pierre'
        assert result['defenseur'] == 'Arnaud'
    
    # ============================================================
    # TESTS DE VALIDATION STRICTE (commandes incomplètes)
    # ============================================================
    
    def test_validation_point_incomplet_sans_coup(self):
        """Test: OK point gagnant Arnaud (MANQUE type de coup)"""
        result = self.parser.parse("ok point gagnant arnaud")
        assert result is not None
        
        validation = self.parser.validate_command(result)
        assert validation['valid'] is False
        assert 'type_coup' in validation['missing_fields']
    
    def test_validation_point_incomplet_sans_joueur(self):
        """Test: OK point gagnant service (MANQUE joueur)"""
        result = self.parser.parse("ok point gagnant service")
        assert result is not None
        
        validation = self.parser.validate_command(result)
        assert validation['valid'] is False
        assert 'joueur' in validation['missing_fields']
    
    def test_validation_balle_haute_sans_sous_type(self):
        """Test: OK point gagnant Arnaud balle haute (MANQUE sous-type)"""
        result = self.parser.parse("ok point gagnant arnaud balle haute")
        assert result is not None
        
        validation = self.parser.validate_command(result)
        assert validation['valid'] is False
        assert 'sous_type' in validation['missing_fields']
    
    def test_validation_faute_provoquee_sans_defenseur(self):
        """Test: OK faute provoquée Arnaud (MANQUE défenseur)"""
        result = self.parser.parse("ok faute provoquée arnaud")
        assert result is not None
        
        validation = self.parser.validate_command(result)
        assert validation['valid'] is False
        assert 'defenseur' in validation['missing_fields']
    
    def test_validation_faute_directe_sans_joueur(self):
        """Test: OK faute directe (MANQUE joueur)"""
        result = self.parser.parse("ok faute directe")
        assert result is not None
        
        validation = self.parser.validate_command(result)
        assert validation['valid'] is False
        assert 'joueur' in validation['missing_fields']
    
    # ============================================================
    # TESTS DE RECONNAISSANCE DE NOMS (variantes orthographiques)
    # ============================================================
    
    def test_reconnaissance_nom_avec_majuscules(self):
        """Test que les noms sont reconnus avec majuscules"""
        result = self.parser.parse("ok faute directe ARNAUD")
        assert result is not None
        assert result['joueur'] in ['Arnaud', 'ARNAUD', 'arnaud']
    
    def test_reconnaissance_vollee_avec_accents(self):
        """Test variantes de 'volée' (avec/sans accent)"""
        result1 = self.parser.parse("ok point gagnant arnaud volée coup droit")
        result2 = self.parser.parse("ok point gagnant arnaud vollée coup droit")
        
        assert result1 is not None
        assert result2 is not None
        assert result1['type_coup'] == 'volée coup droit'
        assert result2['type_coup'] == 'volée coup droit'
    
    def test_reconnaissance_vibora_avec_sans_accent(self):
        """Test variantes de 'víbora' (avec/sans accent)"""
        result1 = self.parser.parse("ok point gagnant pierre balle haute víbora")
        result2 = self.parser.parse("ok point gagnant pierre balle haute vibora")
        
        assert result1 is not None
        assert result2 is not None
        assert result1['sous_type'] in ['víbora', 'vibora']
        assert result2['sous_type'] in ['víbora', 'vibora']
    
    # ============================================================
    # TESTS DE ROBUSTESSE
    # ============================================================
    
    def test_commande_vide(self):
        """Test avec chaîne vide"""
        result = self.parser.parse("")
        assert result is None or result == {}
    
    def test_commande_sans_ok(self):
        """Test commande sans mot-clé OK (doit être ignorée)"""
        result = self.parser.parse("point gagnant arnaud service")
        # La commande peut être parsée mais sans le OK initial
        # Comportement dépend de l'implémentation
    
    def test_commande_inconnue(self):
        """Test avec commande complètement invalide"""
        result = self.parser.parse("ok blabla xyz 123")
        # Doit retourner None ou un dict vide
        assert result is None or result.get('action') is None
    
    # ============================================================
    # TESTS DE COUVERTURE COMPLÈTE
    # ============================================================
    
    def test_toutes_commandes_simples(self):
        """Test rapide de toutes les commandes simples"""
        commandes_simples = [
            ("ok lecture", "play"),
            ("ok pause", "pause"),
            ("ok annuler", "undo"),
            ("ok supprimer", "delete"),
            ("ok sauvegarder", "save"),
            ("ok générer rapport", "report")
        ]
        
        for cmd, action_expected in commandes_simples:
            result = self.parser.parse(cmd)
            assert result is not None, f"Échec pour: {cmd}"
            assert result['action'] == action_expected, f"Action incorrecte pour: {cmd}"
    
    def test_tous_types_coups_validables(self):
        """Test que tous les types de coups créent des commandes valides"""
        types_coups = [
            "service",
            "volée coup droit",
            "volée revers",
            "volée balle haute",
            "fond de court coup droit",
            "fond de court revers",
            "fond de court balle haute",
            "lob",
            "amorti"
        ]
        
        for type_coup in types_coups:
            cmd = f"ok point gagnant arnaud {type_coup}"
            result = self.parser.parse(cmd)
            assert result is not None, f"Parsing échoué pour: {type_coup}"
            
            validation = self.parser.validate_command(result)
            assert validation['valid'] is True, f"Validation échouée pour: {type_coup}"
    
    def test_tous_sous_types_balle_haute(self):
        """Test que tous les sous-types de balle haute sont validés"""
        sous_types = ["smash", "bandeja", "víbora", "vibora"]
        
        for sous_type in sous_types:
            cmd = f"ok point gagnant pierre balle haute {sous_type}"
            result = self.parser.parse(cmd)
            assert result is not None, f"Parsing échoué pour: {sous_type}"
            assert result['type_coup'] == 'balle haute'
            
            validation = self.parser.validate_command(result)
            assert validation['valid'] is True, f"Validation échouée pour: {sous_type}"


if __name__ == "__main__":
    # Exécution des tests avec pytest
    import sys
    
    # Affichage verbeux
    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
