"""
Optimized Biomech Core - Cascade Code Implementation
Module de traitement optimisé avec cascade de données parallélisée
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import json
import time
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple, Any
import numpy as np
import cv2
from collections import deque
import threading
from queue import Queue
import csv


@dataclass
class FrameData:
    """Structure optimisée pour les données de frame"""
    frame_index: int
    timestamp: float
    image: np.ndarray
    detections: List[Dict] = None
    tracking_data: List[Dict] = None
    analysis_data: Dict = None


@dataclass
class ProcessingStats:
    """Statistiques de traitement avec métriques de performance"""
    processed_frames: int = 0
    detection_fps: float = 0.0
    tracking_fps: float = 0.0
    analysis_fps: float = 0.0
    total_fps: float = 0.0
    memory_usage_mb: float = 0.0


class OptimizedTracker:
    """Tracker optimisé avec partitionnement spatial"""
    
    def __init__(self, max_age: int = 15, grid_size: int = 100):
        self.max_age = max_age
        self.tracks = []
        self.next_id = 1
        self.grid_size = grid_size
        self.spatial_grid = {}  # Partitionnement spatial
        
    def _get_grid_key(self, point: Tuple[float, float]) -> Tuple[int, int]:
        """Calcule la clé de grille pour partitionnement spatial"""
        return (int(point[0] // self.grid_size), int(point[1] // self.grid_size))
    
    def _update_spatial_grid(self):
        """Met à jour la grille spatiale pour optimisation"""
        self.spatial_grid.clear()
        for track in self.tracks:
            center = track["center"]
            grid_key = self._get_grid_key(center)
            if grid_key not in self.spatial_grid:
                self.spatial_grid[grid_key] = []
            self.spatial_grid[grid_key].append(track)
    
    def _get_nearby_tracks(self, point: Tuple[float, float]) -> List[Dict]:
        """Récupère les pistes proches via grille spatiale"""
        grid_key = self._get_grid_key(point)
        nearby_tracks = []
        
        # Vérifier les 9 cellules adjacentes
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                check_key = (grid_key[0] + dx, grid_key[1] + dy)
                if check_key in self.spatial_grid:
                    nearby_tracks.extend(self.spatial_grid[check_key])
        
        return nearby_tracks
    
    def update(self, detections: List[Dict], frame_index: int) -> List[Optional[int]]:
        """Mise à jour optimisée avec partitionnement spatial"""
        self._update_spatial_grid()
        
        assigned_det = set()
        assigned_track = set()
        det_to_track = [None] * len(detections)
        
        # Association optimisée
        for di, det in enumerate(detections):
            bbox = det.get("bbox_xyxy")
            if not bbox:
                continue
                
            center = ((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0)
            nearby_tracks = self._get_nearby_tracks(center)
            
            best_track = None
            best_distance = float('inf')
            
            for track in nearby_tracks:
                if track["id"] in assigned_track:
                    continue
                    
                dist = ((center[0] - track["center"][0])**2 + 
                       (center[1] - track["center"][1])**2)**0.5
                
                if dist < best_distance and dist < 100:  # Seuil adaptatif
                    best_distance = dist
                    best_track = track
            
            if best_track:
                assigned_track.add(best_track["id"])
                assigned_det.add(di)
                best_track.update({
                    "bbox": bbox,
                    "center": center,
                    "last_seen": frame_index,
                    "misses": 0,
                })
                det_to_track[di] = best_track["id"]
        
        # Nettoyage des pistes anciennes
        self.tracks = [t for t in self.tracks if t["misses"] <= self.max_age]
        
        # Nouvelles pistes
        for di, det in enumerate(detections):
            if di not in assigned_det:
                bbox = det.get("bbox_xyxy")
                if bbox:
                    center = ((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0)
                    new_track = {
                        "id": self.next_id,
                        "bbox": bbox,
                        "center": center,
                        "last_seen": frame_index,
                        "misses": 0,
                    }
                    self.next_id += 1
                    self.tracks.append(new_track)
                    det_to_track[di] = new_track["id"]
        
        return det_to_track


class BatchProcessor:
    """Processeur par lots pour optimiser les traitements"""
    
    def __init__(self, batch_size: int = 8, max_workers: int = 4):
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
    
    def process_batch(self, frames: List[FrameData], model, device: str, fp16: bool) -> List[FrameData]:
        """Traite un lot de frames en parallèle"""
        def process_single(frame_data):
            try:
                results = model.predict(
                    frame_data.image,
                    device=device,
                    half=fp16,
                    verbose=False
                )
                frame_data.detections = self._extract_detections(results[0])
                return frame_data
            except Exception as e:
                print(f"Erreur traitement frame {frame_data.frame_index}: {e}")
                return frame_data
        
        # Traitement parallèle du lot
        futures = [self.executor.submit(process_single, frame) for frame in frames]
        processed_frames = []
        
        for future in concurrent.futures.as_completed(futures):
            try:
                processed_frames.append(future.result())
            except Exception as e:
                print(f"Erreur future: {e}")
        
        return processed_frames
    
    def _extract_detections(self, results) -> List[Dict]:
        """Extrait les détections des résultats YOLO"""
        detections = []
        
        keypoints = results.keypoints
        boxes = results.boxes
        
        if keypoints is not None and getattr(keypoints, "xy", None) is not None:
            kp_xy = keypoints.xy.cpu().numpy()
            kp_conf = getattr(keypoints, "conf", None)
            if kp_conf is not None:
                kp_conf = kp_conf.cpu().numpy()
            
            box_xyxy = None
            box_conf = None
            if boxes is not None and getattr(boxes, "xyxy", None) is not None:
                box_xyxy = boxes.xyxy.cpu().numpy()
                box_conf = boxes.conf.cpu().numpy()
            
            for i in range(kp_xy.shape[0]):
                det = {
                    "person_index": i,
                    "keypoints_xy": kp_xy[i].tolist(),
                    "keypoints_conf": kp_conf[i].tolist() if kp_conf is not None else None,
                }
                
                if box_xyxy is not None and i < box_xyxy.shape[0]:
                    det["bbox_xyxy"] = box_xyxy[i].tolist()
                    det["bbox_conf"] = float(box_conf[i]) if box_conf is not None else None
                
                detections.append(det)
        
        return detections


class CascadeProcessor:
    """Implémentation du principe Cascade Code optimisée"""
    
    def __init__(self, model_name: str = "yolov8n-pose.pt", device: str = "auto"):
        self.model_name = model_name
        self.device = device
        self.model = None
        self.tracker = OptimizedTracker()
        self.batch_processor = BatchProcessor()
        self.frame_buffer = deque(maxlen=32)  # Buffer circulaire
        self.stats = ProcessingStats()
        
    async def initialize(self):
        """Initialisation asynchrone du modèle"""
        try:
            from ultralytics import YOLO
            self.model = YOLO(self.model_name)
            print(f"Modèle {self.model_name} chargé sur {self.device}")
        except Exception as e:
            raise Exception(f"Erreur chargement modèle: {e}")
    
    async def process_video_stream(self, video_path: str, max_frames: int = 300, 
                                 stride: int = 1) -> List[FrameData]:
        """Flux de traitement en cascade optimisé"""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise Exception("Impossible d'ouvrir la vidéo")
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        
        processed_frames = []
        frame_batch = []
        frame_index = 0
        
        start_time = time.time()
        
        try:
            while cap.isOpened() and frame_index < max_frames:
                ret, frame = cap.read()
                if not ret:
                    break
                
                if frame_index % stride == 0:
                    frame_data = FrameData(
                        frame_index=frame_index,
                        timestamp=frame_index / fps,
                        image=frame
                    )
                    frame_batch.append(frame_data)
                    
                    # Traitement par lot
                    if len(frame_batch) >= self.batch_processor.batch_size:
                        batch_results = await self._process_batch_async(frame_batch)
                        processed_frames.extend(batch_results)
                        frame_batch = []
                
                frame_index += 1
            
            # Traiter le dernier lot
            if frame_batch:
                batch_results = await self._process_batch_async(frame_batch)
                processed_frames.extend(batch_results)
            
        finally:
            cap.release()
        
        # Calcul des statistiques
        processing_time = time.time() - start_time
        self.stats.processed_frames = len(processed_frames)
        self.stats.total_fps = len(processed_frames) / processing_time
        
        return processed_frames
    
    async def _process_batch_async(self, frame_batch: List[FrameData]) -> List[FrameData]:
        """Traitement asynchrone d'un lot"""
        loop = asyncio.get_event_loop()
        
        # Exécuter le traitement CPU dans un thread séparé
        processed_batch = await loop.run_in_executor(
            None,
            self.batch_processor.process_batch,
            frame_batch,
            self.model,
            self.device,
            False  # fp16
        )
        
        # Tracking et analyse
        for frame_data in processed_batch:
            if frame_data.detections:
                frame_data.tracking_data = self._apply_tracking(frame_data.detections, frame_data.frame_index)
                frame_data.analysis_data = self._analyze_frame(frame_data)
        
        return processed_batch
    
    def _apply_tracking(self, detections: List[Dict], frame_index: int) -> List[Dict]:
        """Applique le tracking aux détections"""
        det_to_track = self.tracker.update(detections, frame_index)
        
        for i, det in enumerate(detections):
            det["track_id"] = det_to_track[i]
        
        return detections
    
    def _analyze_frame(self, frame_data: FrameData) -> Dict:
        """Analyse biomécanique de la frame"""
        analysis = {
            "person_count": len(frame_data.detections) if frame_data.detections else 0,
            "avg_keypoint_conf": 0.0,
            "swing_events": []
        }
        
        if frame_data.detections:
            confidences = []
            for det in frame_data.detections:
                kp_conf = det.get("keypoints_conf")
                if kp_conf:
                    confidences.extend([c for c in kp_conf if c > 0])
            
            if confidences:
                analysis["avg_keypoint_conf"] = np.mean(confidences)
        
        return analysis
    
    def export_optimized_json(self, frames: List[FrameData], output_path: str):
        """Export JSON optimisé avec streaming"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('{"frames": [')
            
            for i, frame in enumerate(frames):
                if i > 0:
                    f.write(',')
                
                frame_dict = {
                    "frame_index": frame.frame_index,
                    "timestamp": frame.timestamp,
                    "person_count": len(frame.detections) if frame.detections else 0,
                    "detections": frame.detections or [],
                    "analysis": frame.analysis_data or {}
                }
                
                json.dump(frame_dict, f, separators=(',', ':'))
            
            f.write(']}')
    
    def get_performance_stats(self) -> ProcessingStats:
        """Retourne les statistiques de performance"""
        return self.stats


# Exemple d'utilisation
async def main():
    processor = CascadeProcessor()
    await processor.initialize()
    
    frames = await processor.process_video_stream("video.mp4", max_frames=100)
    processor.export_optimized_json(frames, "output.json")
    
    stats = processor.get_performance_stats()
    print(f"FPS: {stats.total_fps:.2f}, Frames: {stats.processed_frames}")


if __name__ == "__main__":
    asyncio.run(main())
