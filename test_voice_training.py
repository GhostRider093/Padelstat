"""
Test et entraînement de reconnaissance vocale
Vérification micro + test Whisper en temps réel
"""

import pyaudio
import wave
import numpy as np
import threading
import time
from pathlib import Path
import csv
import json
import datetime
from difflib import SequenceMatcher

# Vérifier Whisper
try:
    from faster_whisper import WhisperModel
    WHISPER_TYPE = "faster"
    print("✅ faster-whisper disponible")
except ImportError:
    try:
        import whisper
        WHISPER_TYPE = "openai"
        print("✅ openai-whisper disponible")
    except ImportError:
        print("❌ Whisper non disponible")
        exit(1)


class VoiceTrainer:
    """Outil simple de test vocal"""
    
    def __init__(self):
        self.sample_rate = 16000
        self.chunk_size = 1024
        self.channels = 1
        self.recording = False
        self.audio_data = []
        
        # Charger Whisper
        print("\n🔄 Chargement du modèle Whisper (tiny)... ", end='', flush=True)
        print("\n💡 Note: Le modèle 'tiny' est rapide mais moins précis")
        print("   Pour de meilleurs résultats, utilisez 'base' (option dans le menu)\n")
        if WHISPER_TYPE == "faster":
            self.model = WhisperModel("tiny", device="cpu", compute_type="int8")
        else:
            self.model = whisper.load_model("tiny")
        print("✅\n")

    @staticmethod
    def _similarity(a: str, b: str) -> float:
        a = (a or "").strip().lower()
        b = (b or "").strip().lower()
        if not a and not b:
            return 1.0
        return SequenceMatcher(None, a, b).ratio()

    def transcribe_file(self, wav_file: str) -> str:
        """Transcrit un fichier WAV avec Whisper."""
        try:
            if WHISPER_TYPE == "faster":
                segments, _info = self.model.transcribe(wav_file, language="fr", beam_size=1)
                return " ".join([seg.text for seg in segments]).strip()
            result = self.model.transcribe(wav_file, language="fr", fp16=False)
            return (result.get("text") or "").strip()
        except Exception as e:
            print(f"❌ Erreur transcription: {e}")
            return ""

    def _record_to_file(self, duration: int, output_file: Path):
        """Enregistre l'audio micro dans un WAV cible et retourne (max_volume, duration_s)."""
        p = pyaudio.PyAudio()
        stream = p.open(
            format=pyaudio.paInt16,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk_size
        )

        frames = []
        max_volume = 0
        total_chunks = int(self.sample_rate / self.chunk_size * duration)

        for i in range(total_chunks):
            data = stream.read(self.chunk_size, exception_on_overflow=False)
            frames.append(data)

            audio_array = np.frombuffer(data, dtype=np.int16)
            volume = np.abs(audio_array).mean()
            max_volume = max(max_volume, volume)

            elapsed = (i + 1) * self.chunk_size / self.sample_rate
            bars = int(volume / 50)
            print(
                f"\r  ⏱️  {elapsed:.1f}s / {duration}s  |  Volume: {'█' * min(bars, 30)}{' ' * (30 - min(bars, 30))} {int(volume)}",
                end='',
                flush=True,
            )

        stream.stop_stream()
        stream.close()

        wf = wave.open(str(output_file), 'wb')
        wf.setnchannels(self.channels)
        wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
        wf.setframerate(self.sample_rate)
        wf.writeframes(b''.join(frames))
        wf.close()

        p.terminate()
        print("\n✅ Enregistrement terminé")
        return float(max_volume), float(duration)
        
    def test_microphone(self):
        """Teste si le micro fonctionne"""
        print("=" * 60)
        print("🎤 TEST DU MICROPHONE")
        print("=" * 60)
        
        p = pyaudio.PyAudio()
        
        # Lister les devices
        print("\n📋 Devices audio disponibles:")
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                print(f"  [{i}] {info['name']} (Input: {info['maxInputChannels']} canaux)")
        
        # Ouvrir le micro par défaut
        try:
            stream = p.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )
            
            print("\n✅ Micro ouvert avec succès")
            print("🔊 Test du niveau sonore pendant 3 secondes...")
            print("   Parlez dans le micro!\n")
            
            max_level = 0
            for _ in range(int(3 * self.sample_rate / self.chunk_size)):
                data = stream.read(self.chunk_size, exception_on_overflow=False)
                audio_array = np.frombuffer(data, dtype=np.int16)
                level = np.abs(audio_array).mean()
                max_level = max(max_level, level)
                
                # Afficher niveau
                bars = int(level / 100)
                print(f"\r  Volume: {'█' * bars}{' ' * (50 - bars)} {int(level)}", end='', flush=True)
                time.sleep(0.1)
            
            print(f"\n\n  Niveau maximum détecté: {int(max_level)}")
            if max_level < 100:
                print("  ⚠️  Niveau faible - parlez plus fort ou rapprochez le micro")
            else:
                print("  ✅ Niveau bon")
            
            stream.stop_stream()
            stream.close()
            
        except Exception as e:
            print(f"\n❌ Erreur micro: {e}")
            return False
        
        finally:
            p.terminate()
        
        return True
    
    def record_and_transcribe(self, duration=5):
        """Enregistre et transcrit en temps réel"""
        print("\n" + "=" * 60)
        print(f"🎙️  ENREGISTREMENT ({duration}s)")
        print("=" * 60)
        print("Parlez maintenant...\n")
        
        p = pyaudio.PyAudio()
        stream = p.open(
            format=pyaudio.paInt16,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk_size
        )
        
        frames = []
        max_volume = 0
        
        # Enregistrer avec affichage du temps et volume
        for i in range(int(self.sample_rate / self.chunk_size * duration)):
            data = stream.read(self.chunk_size, exception_on_overflow=False)
            frames.append(data)
            
            # Mesurer le volume
            audio_array = np.frombuffer(data, dtype=np.int16)
            volume = np.abs(audio_array).mean()
            max_volume = max(max_volume, volume)
            
            elapsed = (i + 1) * self.chunk_size / self.sample_rate
            bars = int(volume / 50)
            print(f"\r  ⏱️  {elapsed:.1f}s / {duration}s  |  Volume: {'█' * min(bars, 30)}{' ' * (30 - min(bars, 30))} {int(volume)}", end='', flush=True)
        
        print(f"\n\n✅ Enregistrement terminé (volume max: {int(max_volume)})")
        
        if max_volume < 100:
            print("⚠️  ATTENTION: Volume très faible! Parlez plus fort ou rapprochez le micro")
        
        stream.stop_stream()
        stream.close()
        p.terminate()
        
        # Sauvegarder avec timestamp pour garder l'historique
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        saved_file = f"voice_test_{timestamp}.wav"
        
        wf = wave.open(saved_file, 'wb')
        wf.setnchannels(self.channels)
        wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
        wf.setframerate(self.sample_rate)
        wf.writeframes(b''.join(frames))
        wf.close()
        
        print(f"💾 Audio sauvegardé: {saved_file}")
        
        # Transcrire
        print("🔄 Transcription avec Whisper... ", end='', flush=True)
        
        try:
            if WHISPER_TYPE == "faster":
                segments, info = self.model.transcribe(saved_file, language="fr", beam_size=1)
                text = " ".join([seg.text for seg in segments])
                print(f"✅ (langue détectée: {info.language}, prob: {info.language_probability:.2f})\n")
            else:
                result = self.model.transcribe(saved_file, language="fr", fp16=False)
                text = result["text"]
                print("✅\n")
        except Exception as e:
            print(f"❌ Erreur: {e}\n")
            text = ""
        
        print("=" * 60)
        print("📝 RÉSULTAT:")
        print("=" * 60)
        if text.strip():
            print(f"  '{text.strip()}'")
        else:
            print("  ❌ AUCUN TEXTE DÉTECTÉ")
            print("  Causes possibles:")
            print("  - Volume trop faible (parlez plus fort)")
            print("  - Micro mal configuré")
            print("  - Trop de bruit ambiant")
        print("=" * 60 + "\n")
        
        return text.strip()

    def fine_tuning_dataset_mode(self):
        """Mode guidé: collecte dataset audio/texte pour adaptation/fine-tuning."""
        print("\n" + "=" * 60)
        print("🧠 MODE DATASET FINE-TUNING (GUIDÉ)")
        print("=" * 60)

        base_commands = [
            "stat pause à toi",
            "stat lecture à toi",
            "stat annuler à toi",
            "stat sauvegarder à toi",
            "stat rapport à toi",
            "stat retour à toi",
            "stat avance à toi",
            "stat faute directe Arnaud à toi",
            "stat point gagnant Pierre service à toi",
            "stat faute provoquée Thomas volée Lucas à toi",
            "stat point gagnant Lucas balle haute smash à toi",
            "stat point gagnant Arnaud fond de court revers à toi",
        ]

        custom = input("\n➤ Ajouter vos propres commandes (séparées par ';') ? [Entrée = non] : ").strip()
        if custom:
            extras = [c.strip() for c in custom.split(";") if c.strip()]
            base_commands.extend(extras)

        try:
            repetitions = int(input("➤ Nombre de répétitions par commande [3]: ").strip() or "3")
            if repetitions < 1:
                repetitions = 1
        except Exception:
            repetitions = 3

        try:
            duration = int(input("➤ Durée d'enregistrement par essai en secondes [4]: ").strip() or "4")
            if duration < 2:
                duration = 2
        except Exception:
            duration = 4

        run_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = Path("data") / "voice_finetune" / run_id
        wav_dir = out_dir / "wav"
        out_dir.mkdir(parents=True, exist_ok=True)
        wav_dir.mkdir(parents=True, exist_ok=True)

        print("\n📁 Sortie dataset:", out_dir)
        print(f"📝 {len(base_commands)} commandes × {repetitions} répétitions = {len(base_commands) * repetitions} enregistrements")
        print("\nConsigne: lisez EXACTEMENT la phrase affichée.")
        print("Appuyez sur Entrée pour chaque prise (ou tapez 's' pour sauter).\n")

        rows = []
        idx = 0
        total = len(base_commands) * repetitions

        for expected in base_commands:
            for rep in range(1, repetitions + 1):
                idx += 1
                print("\n" + "-" * 60)
                print(f"🎯 [{idx}/{total}] Phrase ({rep}/{repetitions}): {expected}")
                action = input("   Entrée = enregistrer / s = sauter / q = quitter: ").strip().lower()
                if action == "q":
                    print("\n⏹️ Arrêt demandé.")
                    break
                if action == "s":
                    rows.append({
                        "id": idx,
                        "expected": expected,
                        "recognized": "",
                        "similarity": 0.0,
                        "match": False,
                        "wav": "",
                        "max_volume": 0.0,
                        "duration_s": 0.0,
                        "status": "skipped",
                    })
                    continue

                wav_name = f"sample_{idx:04d}_r{rep}.wav"
                wav_path = wav_dir / wav_name

                max_vol, dur_s = self._record_to_file(duration=duration, output_file=wav_path)
                print("🔄 Transcription en cours...")
                recognized = self.transcribe_file(str(wav_path))

                similarity = self._similarity(expected, recognized)
                match = similarity >= 0.75

                print(f"📝 Reconnu : {recognized or '[vide]'}")
                print(f"📊 Similarité: {similarity:.2f} {'✅' if match else '❌'}")

                rows.append({
                    "id": idx,
                    "expected": expected,
                    "recognized": recognized,
                    "similarity": round(similarity, 4),
                    "match": match,
                    "wav": str(wav_path).replace('\\\\', '/'),
                    "max_volume": round(max_vol, 2),
                    "duration_s": round(dur_s, 2),
                    "status": "ok",
                })

            else:
                continue
            break

        # Exports
        csv_path = out_dir / "dataset.csv"
        jsonl_path = out_dir / "dataset.jsonl"
        summary_path = out_dir / "summary.json"

        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "id", "expected", "recognized", "similarity", "match", "wav", "max_volume", "duration_s", "status"
            ])
            writer.writeheader()
            writer.writerows(rows)

        with open(jsonl_path, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

        valid_rows = [r for r in rows if r.get("status") == "ok"]
        matches = sum(1 for r in valid_rows if r.get("match"))
        total_valid = len(valid_rows)
        avg_similarity = (sum(float(r.get("similarity", 0.0)) for r in valid_rows) / total_valid) if total_valid else 0.0

        summary = {
            "run_id": run_id,
            "total_rows": len(rows),
            "valid_rows": total_valid,
            "match_count": matches,
            "match_rate": (matches / total_valid) if total_valid else 0.0,
            "avg_similarity": avg_similarity,
            "csv": str(csv_path).replace('\\\\', '/'),
            "jsonl": str(jsonl_path).replace('\\\\', '/'),
        }

        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        print("\n" + "=" * 60)
        print("✅ DATASET TERMINÉ")
        print("=" * 60)
        print(f"📁 Dossier: {out_dir}")
        print(f"🧾 CSV   : {csv_path}")
        print(f"🧾 JSONL : {jsonl_path}")
        print(f"📊 Match : {matches}/{total_valid} ({(summary['match_rate'] * 100):.1f}%)")
        print(f"📈 Similarité moyenne: {avg_similarity:.2f}")
        print("\nTu peux réutiliser ce dataset pour affiner les variantes parser/modèle.")
    
    def quick_test(self):
        """Test rapide - dites ce que vous voulez"""
        print("\n" + "=" * 60)
        print("🎯 TEST LIBRE")
        print("=" * 60)
        print("\nDites n'importe quoi, on verra ce que Whisper comprend!")
        print("Durée: 3 secondes\n")
        
        input("Appuyez sur Entrée pour commencer...")
        
        recognized = self.record_and_transcribe(duration=3)
        
        print("\n💡 Astuce: Notez les variantes que Whisper comprend")
        print("   pour adapter les commandes vocales!\n")
    
    def training_mode(self):
        """Mode entraînement avec phrases à répéter"""
        print("\n" + "=" * 60)
        print("🎯 MODE ENTRAÎNEMENT")
        print("=" * 60)
        
        phrases = [
            "OK lecture",
            "OK pause",
            "OK annuler",
            "OK sauvegarder",
            "OK rapport"
        ]
        
        print("\n📋 Phrases d'entraînement:")
        for i, phrase in enumerate(phrases, 1):
            print(f"  {i}. {phrase}")
        
        print("\n" + "-" * 60)
        print("Vous allez répéter chaque phrase 2 fois")
        print("Appuyez sur Entrée pour commencer chaque enregistrement")
        print("-" * 60 + "\n")
        
        results = []
        
        for phrase in phrases:
            for attempt in [1, 2]:
                print(f"\n🎯 Phrase à dire: \"{phrase}\" (essai {attempt}/2)")
                input("  Appuyez sur Entrée quand vous êtes prêt...")
                
                recognized = self.record_and_transcribe(duration=4)
                results.append({
                    'attendu': phrase,
                    'reconnu': recognized,
                    'match': phrase.lower() in recognized.lower()
                })
                
                if results[-1]['match']:
                    print("  ✅ Reconnu correctement!")
                else:
                    print("  ⚠️  Différent de l'attendu")
        
        # Résumé
        print("\n" + "=" * 60)
        print("📊 RÉSUMÉ DE L'ENTRAÎNEMENT")
        print("=" * 60)
        
        matches = sum(1 for r in results if r['match'])
        total = len(results)
        
        print(f"\nTaux de reconnaissance: {matches}/{total} ({matches/total*100:.0f}%)\n")
        
        for r in results:
            status = "✅" if r['match'] else "❌"
            print(f"{status} Attendu: '{r['attendu']}'")
            print(f"   Reconnu: '{r['reconnu']}'")
            print()
    
    def interactive_mode(self):
        """Mode interactif continu"""
        print("\n" + "=" * 60)
        print("🎤 MODE INTERACTIF")
        print("=" * 60)
        print("\nAppuyez sur Entrée pour enregistrer (3s)")
        print("Tapez 'q' pour quitter\n")
        
        while True:
            choice = input("➤ [Entrée = enregistrer / q = quitter]: ").strip().lower()
            
            if choice == 'q':
                break
            
            self.record_and_transcribe(duration=3)


def main():
    """Menu principal"""
    print("\n" + "=" * 60)
    print("🎤 TEST ET ENTRAÎNEMENT VOCAL")
    print("=" * 60)
    
    trainer = VoiceTrainer()
    
    while True:
        print("\n📋 MENU:")
        print("  1. Tester le microphone")
        print("  2. Test rapide (dites ce que vous voulez)")
        print("  3. Enregistrement simple (5s)")
        print("  4. Mode entraînement (phrases à répéter)")
        print("  5. Mode interactif (enregistrements multiples)")
        print("  6. Mode dataset fine-tuning (guidé)")
        print("  q. Quitter")
        
        choice = input("\n➤ Votre choix: ").strip().lower()
        
        if choice == '1':
            trainer.test_microphone()
        elif choice == '2':
            trainer.quick_test()
        elif choice == '3':
            trainer.record_and_transcribe(duration=5)
        elif choice == '4':
            trainer.training_mode()
        elif choice == '5':
            trainer.interactive_mode()
        elif choice == '6':
            trainer.fine_tuning_dataset_mode()
        elif choice == 'q':
            print("\n👋 Au revoir!")
            break
        else:
            print("\n❌ Choix invalide")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Arrêté par l'utilisateur")
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
