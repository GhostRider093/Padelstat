"""
Test rapide du système push-to-talk batch
"""

print("=== Test VoiceBatchRecorder ===\n")

# Test 1: Import
print("[1] Test import...")
try:
    from app.voice.voice_batch_recorder import VoiceBatchRecorder
    print("✓ Import OK")
except Exception as e:
    print(f"✗ Erreur import: {e}")
    exit(1)

# Test 2: Initialisation
print("\n[2] Test initialisation...")
try:
    recorder = VoiceBatchRecorder(data_dir="data/test_voice")
    print("✓ Initialisation OK")
except Exception as e:
    print(f"✗ Erreur init: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Test 3: Démarrage session
print("\n[3] Test démarrage session...")
try:
    recorder.start_session("test_video.mp4")
    print("✓ Session démarrée")
    print(f"   - Session ID: {recorder.session_data['session_id']}")
    print(f"   - Fichier: {recorder.session_file}")
except Exception as e:
    print(f"✗ Erreur session: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Test 4: Simulation capture (sans audio réel)
print("\n[4] Test simulation capture...")
try:
    # Simuler une capture manuelle
    import json
    capture = {
        "id": 1,
        "video_timestamp": "00:01:23.456",
        "capture_time": "2025-12-28T15:30:00.000",
        "audio_text": "faute directe arnaud service",
        "processed": False,
        "status": "pending"
    }
    recorder.session_data["captures"].append(capture)
    recorder._save_session()
    print("✓ Capture simulée ajoutée")
except Exception as e:
    print(f"✗ Erreur capture: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Test 5: Lecture pending captures
print("\n[5] Test récupération pending...")
try:
    pending = recorder.get_pending_captures()
    print(f"✓ {len(pending)} capture(s) en attente")
    for cap in pending:
        print(f"   - #{cap['id']}: {cap['audio_text']}")
except Exception as e:
    print(f"✗ Erreur pending: {e}")
    exit(1)

# Test 6: Marquer comme processé
print("\n[6] Test mark_as_processed...")
try:
    recorder.mark_as_processed(1, success=False)
    unrecognized = recorder.get_unrecognized()
    print(f"✓ Marqué comme non reconnu")
    print(f"   - {len(unrecognized)} non reconnue(s)")
except Exception as e:
    print(f"✗ Erreur processing: {e}")
    exit(1)

# Test 7: Vérification fichier JSON
print("\n[7] Test fichier JSON...")
try:
    import os
    if os.path.exists(recorder.session_file):
        with open(recorder.session_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print("✓ Fichier JSON valide")
        print(f"   - Captures: {len(data['captures'])}")
        print(f"   - Non reconnues: {len(data['unrecognized'])}")
    else:
        print("✗ Fichier non trouvé")
except Exception as e:
    print(f"✗ Erreur JSON: {e}")

print("\n=== Tests terminés ===")
print("\n📝 Prochain test: Intégration UI avec touche Entrée")
print("   1. Lancer l'app: python main.py")
print("   2. Charger une vidéo")
print("   3. Appuyer/relâcher Entrée pour tester push-to-talk")
print("   4. Cliquer 'Rapport rapide' pour parser les captures")
