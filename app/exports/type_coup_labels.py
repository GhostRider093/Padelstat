"""
Mapping et labels pour les types de coups V2 (structure détaillée)
Centralise tous les labels d'affichage pour les rapports HTML
"""

# Mapping complet des types de coups V2
TYPE_COUP_LABELS_V2 = {
    # Service
    'service': '🎾 Service',
    
    # Fond de court - Coup Droit
    'fond_de_court_CD': '⚡ Fond de court CD',
    
    # Fond de court - Revers
    'fond_de_court_R': '⚡ Fond de court Revers',
    
    # Fond de court - Balle Haute + coups
    'fond_de_court_BH_vibora': '⚡ Fond BH → 🐍 Víbora',
    'fond_de_court_BH_bandeja': '⚡ Fond BH → 🔥 Bandeja',
    'fond_de_court_BH_smash': '⚡ Fond BH → 💥 Smash',
    
    # Volée - Coup Droit
    'volee_CD': '🏐 Volée CD',
    
    # Volée - Revers
    'volee_R': '🏐 Volée Revers',
    
    # Volée - Balle Haute + coups
    'volee_BH_vibora': '🏐 Volée BH → 🐍 Víbora',
    'volee_BH_bandeja': '🏐 Volée BH → 🔥 Bandeja',
    'volee_BH_smash': '🏐 Volée BH → 💥 Smash',
    
    # Anciens formats (rétrocompatibilité)
    'volee_coup_droit': '🏐 Volée CD',
    'volee_revers': '🏐 Volée Rev',
    'volee_balle_haute': '🏐 Volée BH',
    'fond_de_court_coup_droit': '⚡ Fond CD',
    'fond_de_court_revers': '⚡ Fond Rev',
    'fond_de_court_balle_haute': '⚡ Fond BH',
    'fond_de_court': '⚡ Fond de court',
    'smash': '💥 Smash',
    'amorti': '🎯 Amorti',
    'bandeja': '🔥 Bandeja',
    'vibora': '🐍 Víbora',
    'autre': '❓ Autre'
}

# Regroupements pour graphiques
COUP_CATEGORIES = {
    'service': ['service'],
    'fond_de_court': [
        'fond_de_court_CD', 'fond_de_court_R',
        'fond_de_court_BH_vibora', 'fond_de_court_BH_bandeja', 'fond_de_court_BH_smash',
        'fond_de_court_coup_droit', 'fond_de_court_revers', 
        'fond_de_court_balle_haute',
        'fond_de_court'
    ],
    'volee': [
        'volee_CD', 'volee_R',
        'volee_BH_vibora', 'volee_BH_bandeja', 'volee_BH_smash',
        'volee_coup_droit', 'volee_revers', 'volee_balle_haute'
    ],
    'smash': ['smash', 'fond_de_court_BH_smash', 'volee_BH_smash'],
    'vibora': ['vibora', 'fond_de_court_BH_vibora', 'volee_BH_vibora'],
    'bandeja': ['bandeja', 'fond_de_court_BH_bandeja', 'volee_BH_bandeja'],
    'amorti': ['amorti']
}

# Labels simplifiés pour graphiques
COUP_LABELS_SIMPLE = {
    'service': '🎾 Service',
    'fond_de_court': '⚡ Fond de court',
    'volee': '🏐 Volée',
    'smash': '💥 Smash',
    'vibora': '🐍 Víbora',
    'bandeja': '🔥 Bandeja',
    'amorti': '🎯 Amorti'
}


def get_coup_label(type_coup: str) -> str:
    """
    Retourne le label d'affichage pour un type de coup
    
    Args:
        type_coup: Type de coup (ex: 'fond_de_court_CD')
        
    Returns:
        Label formaté avec emoji
    """
    return TYPE_COUP_LABELS_V2.get(type_coup, f"❓ {type_coup}")


def get_coup_category(type_coup: str) -> str:
    """
    Retourne la catégorie d'un coup pour regroupement
    
    Args:
        type_coup: Type de coup détaillé
        
    Returns:
        Catégorie ('service', 'fond_de_court', 'volee', etc.)
    """
    for category, types in COUP_CATEGORIES.items():
        if type_coup in types:
            return category
    return 'autre'


def normalize_type_coup(type_coup: str) -> str:
    """
    Normalise les anciens types vers les nouveaux
    
    Args:
        type_coup: Type ancien ou nouveau
        
    Returns:
        Type normalisé
    """
    # Mapping anciens → nouveaux
    mappings = {
        'volee_coup_droit': 'volee_CD',
        'volee_revers': 'volee_R',
        'volee_balle_haute': 'volee_BH',
        'fond_de_court_coup_droit': 'fond_de_court_CD',
        'fond_de_court_revers': 'fond_de_court_R',
        'fond_de_court_balle_haute': 'fond_de_court_BH'
    }
    
    return mappings.get(type_coup, type_coup)


# Export pour utilisation dans html_generator.py
__all__ = [
    'TYPE_COUP_LABELS_V2',
    'COUP_CATEGORIES',
    'COUP_LABELS_SIMPLE',
    'get_coup_label',
    'get_coup_category',
    'normalize_type_coup'
]
