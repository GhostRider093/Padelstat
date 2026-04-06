import argparse
import json
import os
import tempfile
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from difflib import SequenceMatcher
from typing import Callable, Dict, List, Optional, Tuple


DEFAULT_PHRASES: List[str] = [
    "OK point Arnaud service OK",
    "OK point Pierre volée coup droit OK",
    "OK point Thomas volée revers OK",
    "OK point Lucas fond de court coup droit OK",
    "OK point Arnaud fond de court revers OK",
    "OK point Pierre fond de court balle haute bandeja OK",
    "OK point Thomas fond de court balle haute vibora OK",
    "OK point Lucas fond de court balle haute smash OK",
    "OK faute directe Pierre OK",
    "OK faute provoquée Arnaud volée revers Thomas OK",
    "OK sauvegarder OK",
    "OK rapport OK",
    "OK supprimer OK",
]


def now_tag() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def normalize_for_scoring(text: str) -> str:
    # Normalisation light: lower + trim + collapse spaces.
    # On réutilise aussi la normalisation du CommandParser si dispo.
    text = (text or "").strip()
    if not text:
        return ""

    try:
        from app.voice.command_parser import CommandParser

        return CommandParser().normaliser_texte(text)
    except Exception:
        lowered = text.lower().strip()
        while "  " in lowered:
            lowered = lowered.replace("  ", " ")
        return lowered


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(a=a, b=b).ratio() if a or b else 0.0


@dataclass
class BenchItem:
    expected: str
    recognized: str
    recognized_norm: str
    expected_norm: str
    exact: bool
    similarity: float
    latency_s: float
    error: Optional[str] = None


@dataclass
class BenchResult:
    engine: str
    started_at: str
    items: List[BenchItem]

    def summary(self) -> Dict:
        total = len(self.items)
        exact = sum(1 for i in self.items if i.exact)
        ok_items = [i for i in self.items if not i.error]
        avg_sim = sum(i.similarity for i in ok_items) / len(ok_items) if ok_items else 0.0
        avg_lat = sum(i.latency_s for i in ok_items) / len(ok_items) if ok_items else 0.0
        errors = sum(1 for i in self.items if i.error)
        return {
            "engine": self.engine,
            "total": total,
            "exact": exact,
            "exact_pct": round(100.0 * exact / total, 1) if total else 0.0,
            "avg_similarity": round(avg_sim, 3),
            "avg_latency_s": round(avg_lat, 3),
            "errors": errors,
        }


def print_summary_table(summaries: List[Dict]) -> None:
    if not summaries:
        return

    headers = ["engine", "total", "exact", "exact_pct", "avg_similarity", "avg_latency_s", "errors"]
    col_widths = {h: max(len(h), max(len(str(s.get(h, ""))) for s in summaries)) for h in headers}

    def fmt_row(row: Dict) -> str:
        return "  ".join(str(row.get(h, "")).ljust(col_widths[h]) for h in headers)

    print("\n=== RÉSUMÉ ===")
    print(fmt_row({h: h for h in headers}))
    print("  ".join("-" * col_widths[h] for h in headers))
    for s in summaries:
        print(fmt_row(s))


def read_phrases(path: Optional[str]) -> List[str]:
    if not path:
        return DEFAULT_PHRASES
    with open(path, "r", encoding="utf-8") as f:
        lines = [ln.strip() for ln in f.readlines()]
    return [ln for ln in lines if ln and not ln.startswith("#")]


# ----------------------------
# Engines
# ----------------------------

def bench_windows_sapi(phrases: List[str], timeout_s: float, language: str) -> BenchResult:
    from app.voice.voice_commander_windows import WindowsVoiceCommander

    started_at = datetime.now().isoformat(timespec="seconds")
    items: List[BenchItem] = []

    commander = WindowsVoiceCommander(callback=None, language=language)
    if not commander.initialize():
        raise RuntimeError("Windows SAPI indisponible (pywin32/SAPI).")

    print("\n[Windows SAPI] Mode one-shot. Parle juste après le message 'Parlez maintenant'.")

    for idx, expected in enumerate(phrases, start=1):
        expected_norm = normalize_for_scoring(expected)
        input(f"\n({idx}/{len(phrases)}) À dire: {expected}\nAppuie sur Entrée puis parle... ")

        start = time.perf_counter()
        error: Optional[str] = None
        try:
            recognized = commander.recognize_once(timeout=timeout_s) or ""
        except Exception as e:
            recognized = ""
            error = str(e)
        latency = time.perf_counter() - start

        if not error and not recognized.strip():
            error = "no_result"

        recognized_norm = normalize_for_scoring(recognized)
        is_exact = recognized_norm == expected_norm and recognized_norm != ""
        sim = similarity(expected_norm, recognized_norm)

        if recognized.strip():
            print(f"Reconnu: {recognized!r}")
        else:
            print("Reconnu: (aucun texte)")

        items.append(
            BenchItem(
                expected=expected,
                expected_norm=expected_norm,
                recognized=recognized,
                recognized_norm=recognized_norm,
                exact=is_exact,
                similarity=sim,
                latency_s=latency,
                error=error,
            )
        )

    return BenchResult(engine="windows_sapi", started_at=started_at, items=items)


def bench_google(phrases: List[str], timeout_s: float, phrase_time_limit_s: float, language: str) -> BenchResult:
    import speech_recognition as sr

    started_at = datetime.now().isoformat(timespec="seconds")
    items: List[BenchItem] = []

    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    print("\n[Google] Calibration bruit ambiant...")
    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.7)

    for idx, expected in enumerate(phrases, start=1):
        expected_norm = normalize_for_scoring(expected)
        input(f"\n({idx}/{len(phrases)}) À dire: {expected}\nAppuie sur Entrée puis parle... ")

        error: Optional[str] = None
        recognized = ""
        start = time.perf_counter()

        try:
            with mic as source:
                audio = recognizer.listen(source, timeout=timeout_s, phrase_time_limit=phrase_time_limit_s)
            recognized = recognizer.recognize_google(audio, language=language)
        except sr.WaitTimeoutError:
            error = f"timeout (>{timeout_s}s)"
        except sr.UnknownValueError:
            error = "incompréhensible"
        except sr.RequestError as e:
            error = f"google_request_error: {e}"
        except Exception as e:
            error = str(e)

        latency = time.perf_counter() - start

        if not error and not recognized.strip():
            error = "no_result"

        recognized_norm = normalize_for_scoring(recognized)
        is_exact = recognized_norm == expected_norm and recognized_norm != ""
        sim = similarity(expected_norm, recognized_norm)

        if recognized.strip():
            print(f"Reconnu: {recognized!r}")
        else:
            print("Reconnu: (aucun texte)")

        items.append(
            BenchItem(
                expected=expected,
                expected_norm=expected_norm,
                recognized=recognized,
                recognized_norm=recognized_norm,
                exact=is_exact,
                similarity=sim,
                latency_s=latency,
                error=error,
            )
        )

    return BenchResult(engine="google_speech", started_at=started_at, items=items)


def bench_whisper(phrases: List[str], timeout_s: float, phrase_time_limit_s: float, language: str, model_size: str) -> BenchResult:
    import speech_recognition as sr
    from faster_whisper import WhisperModel

    started_at = datetime.now().isoformat(timespec="seconds")
    items: List[BenchItem] = []

    print(f"\n[Whisper] Chargement du modèle: {model_size} (CPU/int8)...")
    model = WhisperModel(model_size, device="cpu", compute_type="int8")

    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    print("[Whisper] Calibration bruit ambiant...")
    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.7)

    for idx, expected in enumerate(phrases, start=1):
        expected_norm = normalize_for_scoring(expected)
        input(f"\n({idx}/{len(phrases)}) À dire: {expected}\nAppuie sur Entrée puis parle... ")

        error: Optional[str] = None
        recognized = ""
        start = time.perf_counter()

        tmp_path = None
        try:
            with mic as source:
                audio = recognizer.listen(source, timeout=timeout_s, phrase_time_limit=phrase_time_limit_s)

            wav_bytes = audio.get_wav_data(convert_rate=16000, convert_width=2)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                tmp.write(wav_bytes)
                tmp_path = tmp.name

            segments, _info = model.transcribe(tmp_path, language=language.split("-")[0])
            recognized = " ".join(seg.text.strip() for seg in segments if seg.text).strip()

        except sr.WaitTimeoutError:
            error = f"timeout (>{timeout_s}s)"
        except Exception as e:
            error = str(e)
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

        latency = time.perf_counter() - start

        if not error and not recognized.strip():
            error = "no_result"

        recognized_norm = normalize_for_scoring(recognized)
        is_exact = recognized_norm == expected_norm and recognized_norm != ""
        sim = similarity(expected_norm, recognized_norm)

        if recognized.strip():
            print(f"Reconnu: {recognized!r}")
        else:
            print("Reconnu: (aucun texte)")

        items.append(
            BenchItem(
                expected=expected,
                expected_norm=expected_norm,
                recognized=recognized,
                recognized_norm=recognized_norm,
                exact=is_exact,
                similarity=sim,
                latency_s=latency,
                error=error,
            )
        )

    return BenchResult(engine=f"whisper_{model_size}", started_at=started_at, items=items)


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark interactif moteurs STT (Windows SAPI / Google / Whisper).")
    parser.add_argument("--engine", choices=["all", "windows", "google", "whisper"], default="all")
    parser.add_argument("--phrases", help="Fichier .txt des phrases à prononcer (1 par ligne)")
    parser.add_argument("--language", default="fr-FR")
    parser.add_argument("--timeout", type=float, default=6.0, help="Timeout d'attente début de parole")
    parser.add_argument("--phrase-time-limit", type=float, default=4.0, help="Durée max capturée par phrase")
    parser.add_argument("--whisper-model", default="tiny", help="Whisper model (tiny/base/small/...)")
    parser.add_argument("--out", default=None, help="Chemin de sortie JSON (sinon data/voice_engine_bench_*.json)")

    args = parser.parse_args()

    phrases = read_phrases(args.phrases)
    if not phrases:
        raise SystemExit("Aucune phrase à tester.")

    results: List[BenchResult] = []

    if args.engine in ("all", "windows"):
        try:
            results.append(bench_windows_sapi(phrases, timeout_s=args.timeout, language=args.language))
        except Exception as e:
            print(f"\n[Windows SAPI] SKIP: {e}")

    if args.engine in ("all", "google"):
        try:
            results.append(
                bench_google(
                    phrases,
                    timeout_s=args.timeout,
                    phrase_time_limit_s=args.phrase_time_limit,
                    language=args.language,
                )
            )
        except Exception as e:
            print(f"\n[Google] SKIP: {e}")

    if args.engine in ("all", "whisper"):
        try:
            results.append(
                bench_whisper(
                    phrases,
                    timeout_s=args.timeout,
                    phrase_time_limit_s=args.phrase_time_limit,
                    language=args.language,
                    model_size=args.whisper_model,
                )
            )
        except Exception as e:
            print(f"\n[Whisper] SKIP: {e}")

    summaries = [r.summary() for r in results]
    print_summary_table(summaries)

    out_path = args.out
    if not out_path:
        os.makedirs("data", exist_ok=True)
        out_path = os.path.join("data", f"voice_engine_bench_{now_tag()}.json")

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "language": args.language,
        "timeout": args.timeout,
        "phrase_time_limit": args.phrase_time_limit,
        "phrases": phrases,
        "summaries": summaries,
        "results": [
            {
                "engine": r.engine,
                "started_at": r.started_at,
                "items": [asdict(i) for i in r.items],
            }
            for r in results
        ],
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Résultats sauvegardés: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
