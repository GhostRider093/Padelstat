"""
Cache Manager pour optimiser les calculs répétitifs
Implémentation de cache LRU et cache de calculs
"""

import time
import hashlib
import pickle
from typing import Any, Dict, Optional, Tuple
from collections import OrderedDict
import threading
import numpy as np


class LRUCache:
    """Cache LRU thread-safe avec TTL"""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache = OrderedDict()
        self.timestamps = {}
        self.lock = threading.RLock()
    
    def _is_expired(self, key: str) -> bool:
        """Vérifie si une entrée est expirée"""
        if key not in self.timestamps:
            return True
        return time.time() - self.timestamps[key] > self.ttl_seconds
    
    def get(self, key: str) -> Optional[Any]:
        """Récupère une valeur du cache"""
        with self.lock:
            if key in self.cache and not self._is_expired(key):
                # Déplacer à la fin (récent)
                self.cache.move_to_end(key)
                return self.cache[key]
            elif key in self.cache:
                # Supprimer l'entrée expirée
                del self.cache[key]
                del self.timestamps[key]
            return None
    
    def put(self, key: str, value: Any):
        """Ajoute une valeur au cache"""
        with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
            else:
                if len(self.cache) >= self.max_size:
                    # Supprimer le plus ancien
                    oldest_key = next(iter(self.cache))
                    del self.cache[oldest_key]
                    del self.timestamps[oldest_key]
            
            self.cache[key] = value
            self.timestamps[key] = time.time()
    
    def clear(self):
        """Vide le cache"""
        with self.lock:
            self.cache.clear()
            self.timestamps.clear()
    
    def size(self) -> int:
        """Retourne la taille actuelle du cache"""
        return len(self.cache)


class ComputationCache:
    """Cache pour les calculs coûteux (transformations, détections)"""
    
    def __init__(self, max_size: int = 500):
        self.detection_cache = LRUCache(max_size, ttl_seconds=1800)  # 30 min
        self.transformation_cache = LRUCache(max_size, ttl_seconds=3600)  # 1 heure
        self.keypoint_cache = LRUCache(max_size, ttl_seconds=900)  # 15 min
    
    def _generate_frame_hash(self, frame: np.ndarray, frame_index: int) -> str:
        """Génère un hash unique pour une frame"""
        # Échantillonner la frame pour réduire le coût de hashage
        sample = frame[::10, ::10].flatten()[:100]  # Prendre 100 pixels échantillonnés
        frame_bytes = sample.tobytes() + str(frame_index).encode()
        return hashlib.md5(frame_bytes).hexdigest()
    
    def get_cached_detection(self, frame: np.ndarray, frame_index: int, 
                           model_name: str, device: str) -> Optional[Any]:
        """Récupère les détections en cache"""
        cache_key = f"detection_{model_name}_{device}_{self._generate_frame_hash(frame, frame_index)}"
        return self.detection_cache.get(cache_key)
    
    def cache_detection(self, frame: np.ndarray, frame_index: int, 
                       model_name: str, device: str, detection_result: Any):
        """Met en cache les détections"""
        cache_key = f"detection_{model_name}_{device}_{self._generate_frame_hash(frame, frame_index)}"
        self.detection_cache.put(cache_key, detection_result)
    
    def get_cached_transformation(self, points: np.ndarray, 
                                matrix_shape: Tuple[int, ...]) -> Optional[np.ndarray]:
        """Récupère les transformations en cache"""
        points_hash = hashlib.md5(points.tobytes()).hexdigest()
        cache_key = f"transform_{points_hash}_{matrix_shape}"
        result = self.transformation_cache.get(cache_key)
        return np.array(result) if result is not None else None
    
    def cache_transformation(self, points: np.ndarray, matrix_shape: Tuple[int, ...], 
                           result: np.ndarray):
        """Met en cache les transformations"""
        points_hash = hashlib.md5(points.tobytes()).hexdigest()
        cache_key = f"transform_{points_hash}_{matrix_shape}"
        self.transformation_cache.put(cache_key, result.tolist())
    
    def get_cached_keypoints_analysis(self, keypoints: np.ndarray, 
                                    analysis_type: str) -> Optional[Dict]:
        """Récupère l'analyse de keypoints en cache"""
        keypoints_hash = hashlib.md5(keypoints.tobytes()).hexdigest()
        cache_key = f"keypoints_{analysis_type}_{keypoints_hash}"
        return self.keypoint_cache.get(cache_key)
    
    def cache_keypoints_analysis(self, keypoints: np.ndarray, 
                               analysis_type: str, result: Dict):
        """Met en cache l'analyse de keypoints"""
        keypoints_hash = hashlib.md5(keypoints.tobytes()).hexdigest()
        cache_key = f"keypoints_{analysis_type}_{keypoints_hash}"
        self.keypoint_cache.put(cache_key, result)
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Retourne les statistiques des caches"""
        return {
            "detections": self.detection_cache.size(),
            "transformations": self.transformation_cache.size(),
            "keypoints_analysis": self.keypoint_cache.size()
        }


class OptimizedHomography:
    """Calculs d'homographie optimisés avec cache"""
    
    def __init__(self, cache_manager: ComputationCache):
        self.cache = cache_manager
    
    def compute_perspective_transform(self, points: np.ndarray, 
                                     H: np.ndarray) -> np.ndarray:
        """Calcule la transformation perspective avec cache"""
        # Vérifier le cache
        cached_result = self.cache.get_cached_transformation(
            points, H.shape
        )
        if cached_result is not None:
            return cached_result
        
        # Calculer et mettre en cache
        pts = points.reshape(-1, 1, 2).astype(np.float32)
        result = cv2.perspectiveTransform(pts, H)
        
        self.cache.cache_transformation(points, H.shape, result.reshape(points.shape))
        return result.reshape(points.shape)


class SwingDetectionOptimizer:
    """Optimisation pour la détection de swings avec cache"""
    
    def __init__(self, cache_manager: ComputationCache):
        self.cache = cache_manager
        self.speed_thresholds = {
            "metres": 4.0,
            "pixels": 300.0
        }
    
    def analyze_swing_cached(self, keypoints: np.ndarray, 
                           previous_position: Optional[Tuple[float, float]],
                           units: str = "pixels") -> Dict:
        """Analyse de swing avec cache"""
        # Créer une clé de cache
        analysis_data = {
            "keypoints": keypoints,
            "previous_position": previous_position,
            "units": units
        }
        
        # Hash pour le cache
        data_bytes = pickle.dumps(analysis_data, protocol=pickle.HIGHEST_PROTOCOL)
        cache_key = hashlib.md5(data_bytes).hexdigest()
        
        # Vérifier le cache
        cached_result = self.cache.get_cached_keypoints_analysis(
            keypoints, f"swing_{cache_key}"
        )
        if cached_result is not None:
            return cached_result
        
        # Calculer l'analyse
        result = self._compute_swing_analysis(keypoints, previous_position, units)
        
        # Mettre en cache
        self.cache.cache_keypoints_analysis(keypoints, f"swing_{cache_key}", result)
        
        return result
    
    def _compute_swing_analysis(self, keypoints: np.ndarray, 
                              previous_position: Optional[Tuple[float, float]],
                              units: str) -> Dict:
        """Calcule l'analyse de swing"""
        if len(keypoints) < 13:  # Pas assez de keypoints
            return {"swing_detected": False, "speed": 0.0, "side": None}
        
        # Index COCO pour le poignet droit
        idx_rw = 10
        if idx_rw >= len(keypoints):
            return {"swing_detected": False, "speed": 0.0, "side": None}
        
        wrist_pos = keypoints[idx_rw]
        
        if previous_position is None:
            return {
                "swing_detected": False,
                "speed": 0.0,
                "side": None,
                "current_position": wrist_pos.tolist()
            }
        
        # Calculer la vitesse
        dx = wrist_pos[0] - previous_position[0]
        dy = wrist_pos[1] - previous_position[1]
        speed = (dx * dx + dy * dy) ** 0.5
        
        threshold = self.speed_thresholds.get(units, 300.0)
        swing_detected = speed > threshold
        
        # Déterminer le côté (simplifié)
        side = "forehand" if wrist_pos[0] > previous_position[0] else "backhand"
        
        return {
            "swing_detected": swing_detected,
            "speed": speed,
            "side": side if swing_detected else None,
            "current_position": wrist_pos.tolist()
        }


# Cache global singleton
_cache_manager = None

def get_cache_manager() -> ComputationCache:
    """Retourne l'instance singleton du cache manager"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = ComputationCache()
    return _cache_manager


def clear_all_caches():
    """Vide tous les caches"""
    cache_manager = get_cache_manager()
    cache_manager.detection_cache.clear()
    cache_manager.transformation_cache.clear()
    cache_manager.keypoint_cache.clear()


# Exemple d'utilisation
if __name__ == "__main__":
    # Test du cache
    cache = ComputationCache()
    
    # Test de cache LRU
    cache.detection_cache.put("test_key", {"data": "test_value"})
    result = cache.detection_cache.get("test_key")
    print(f"Résultat du cache: {result}")
    
    # Statistiques
    stats = cache.get_cache_stats()
    print(f"Statistiques du cache: {stats}")
