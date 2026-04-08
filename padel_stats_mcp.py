from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from typing import Any

from mcp.server.fastmcp import FastMCP

from app.annotations.annotation_manager import AnnotationManager
from app.exports.html_generator import HTMLGenerator
from app.exports.json_exporter import JSONExporter
from export_voice_module.padel_voice.command_parser import CommandParser


mcp = FastMCP("padel-stats")


@dataclass
class SessionContext:
    data_folder: str = "data"
    match_name: str = "Match padel"
    players: list[str] = field(default_factory=list)
    video_path: str | None = None
    timestamp: float = 0.0
    frame: int = 0


class PadelStatsSession:
    def __init__(self) -> None:
        self.context = SessionContext()
        self.manager = AnnotationManager(data_folder=self.context.data_folder, enable_background_ai=False)
        self.parser = CommandParser(joueurs=self.context.players)
        self.json_exporter = JSONExporter()
        self.html_generator = HTMLGenerator()

    def reset(self, data_folder: str = "data", match_name: str = "Match padel") -> dict[str, Any]:
        self.context = SessionContext(data_folder=data_folder, match_name=match_name)
        self.manager = AnnotationManager(data_folder=data_folder, enable_background_ai=False)
        self.parser = CommandParser(joueurs=[])
        self.json_exporter = JSONExporter()
        self.html_generator = HTMLGenerator()
        return self.get_state()

    def set_players(self, players: list[str]) -> dict[str, Any]:
        self.context.players = players
        self.manager.set_players(players)
        self.parser.set_joueurs(players)
        return self.get_state()

    def set_video(self, video_path: str) -> dict[str, Any]:
        self.context.video_path = video_path
        self.manager.set_video(video_path)
        return self.get_state()

    def set_capture_context(self, timestamp: float | None = None, frame: int | None = None) -> dict[str, Any]:
        if timestamp is not None:
          self.context.timestamp = float(timestamp)
        if frame is not None:
          self.context.frame = int(frame)
        return self.get_state()

    def parse_command(self, text: str) -> dict[str, Any]:
        parsed = self.parser.parse(text)
        if not parsed:
            return {
                "ok": False,
                "status": "unrecognized",
                "message": "Commande non reconnue",
                "text": text,
            }

        valid, message = self.parser.validate_command(parsed)
        missing = self.parser.get_missing_fields(parsed)
        return {
            "ok": valid,
            "status": "ready" if valid else "incomplete",
            "message": message,
            "missing_fields": missing,
            "parsed": parsed,
            "formatted": self.parser.format_command(parsed),
        }

    def apply_parsed(self, parsed: dict[str, Any], timestamp: float | None = None, frame: int | None = None) -> dict[str, Any]:
        valid, message = self.parser.validate_command(parsed)
        if not valid:
            return {
                "ok": False,
                "status": "incomplete",
                "message": message,
                "missing_fields": self.parser.get_missing_fields(parsed),
                "parsed": parsed,
            }

        action = parsed.get("action")
        ts = self.context.timestamp if timestamp is None else float(timestamp)
        fr = self.context.frame if frame is None else int(frame)

        if action == "annuler":
            removed = self.manager.remove_last_annotation()
            return {
                "ok": removed is not None,
                "status": "applied" if removed else "noop",
                "message": "Derniere annotation supprimee" if removed else "Aucune annotation a supprimer",
                "removed": removed,
            }

        if action == "sauvegarder":
            ok = self.manager.autosave()
            return {
                "ok": ok,
                "status": "applied" if ok else "error",
                "message": "Session sauvegardee" if ok else "Echec sauvegarde",
                "autosave_file": self.manager.autosave_file,
            }

        if action != "nouveau_point":
            return {
                "ok": True,
                "status": "noop",
                "message": f"Action reconnue mais non appliquee cote stats: {action}",
                "parsed": parsed,
            }

        point_type = parsed.get("type_point")
        annotation: dict[str, Any] | None = None

        if point_type == "faute_directe":
            annotation = self.manager.add_faute_directe(
                joueur=parsed.get("joueur"),
                timestamp=ts,
                frame=fr,
                type_coup=parsed.get("type_coup"),
            )
        elif point_type == "point_gagnant":
            annotation = self.manager.add_point_gagnant(
                joueur=parsed.get("joueur"),
                timestamp=ts,
                frame=fr,
                type_coup=parsed.get("type_coup"),
            )
        elif point_type == "faute_provoquee":
            annotation = self.manager.add_faute_provoquee(
                attaquant=parsed.get("joueur"),
                defenseur=parsed.get("defenseur"),
                timestamp=ts,
                frame=fr,
                type_coup_attaquant=parsed.get("type_coup"),
                type_coup_defenseur=None,
            )
        else:
            return {
                "ok": False,
                "status": "error",
                "message": f"Type de point non supporte: {point_type}",
                "parsed": parsed,
            }

        return {
            "ok": True,
            "status": "applied",
            "message": "Annotation ajoutee",
            "annotation": annotation,
            "stats": self.manager.get_stats(),
            "point_count": len(self.manager.get_all_annotations()),
        }

    def apply_text(self, text: str, timestamp: float | None = None, frame: int | None = None) -> dict[str, Any]:
        parsed_result = self.parse_command(text)
        parsed = parsed_result.get("parsed")
        if not parsed:
            return parsed_result
        applied = self.apply_parsed(parsed, timestamp=timestamp, frame=frame)
        applied["parse"] = parsed_result
        return applied

    def export_json(self, output_path: str | None = None) -> dict[str, Any]:
        path = self.json_exporter.export(self.manager, output_path=output_path)
        return {"ok": True, "output_path": path}

    def export_html(self, output_path: str | None = None) -> dict[str, Any]:
        path = self.html_generator.generate_report(self.manager, output_path=output_path, video_player=None, fast_mode=True)
        return {"ok": True, "output_path": path}

    def get_state(self) -> dict[str, Any]:
        annotations = self.manager.get_all_annotations()
        return {
            "context": asdict(self.context),
            "point_count": len(annotations),
            "current_point_id": self.manager.current_point_id,
            "last_annotation": annotations[-1] if annotations else None,
            "autosave_file": self.manager.autosave_file,
        }


SESSION = PadelStatsSession()


@mcp.tool()
def padel_reset_session(data_folder: str = "data", match_name: str = "Match padel") -> dict[str, Any]:
    """Reinitialise la session de stats padel."""
    return SESSION.reset(data_folder=data_folder, match_name=match_name)


@mcp.tool()
def padel_set_players(players: list[str]) -> dict[str, Any]:
    """Definit les joueurs du match dans l'ordre voulu."""
    return SESSION.set_players(players)


@mcp.tool()
def padel_set_video(video_path: str) -> dict[str, Any]:
    """Associe une video a la session de stats."""
    return SESSION.set_video(video_path)


@mcp.tool()
def padel_set_capture_context(timestamp: float | None = None, frame: int | None = None) -> dict[str, Any]:
    """Definit le contexte courant (timestamp/frame) utilise lors des annotations."""
    return SESSION.set_capture_context(timestamp=timestamp, frame=frame)


@mcp.tool()
def padel_parse_stat_command(text: str) -> dict[str, Any]:
    """Parse une commande en langage naturel pour les stats padel."""
    return SESSION.parse_command(text)


@mcp.tool()
def padel_apply_stat_command(text: str, timestamp: float | None = None, frame: int | None = None) -> dict[str, Any]:
    """Parse puis applique une commande de stats padel."""
    return SESSION.apply_text(text, timestamp=timestamp, frame=frame)


@mcp.tool()
def padel_add_stat(
    type_point: str,
    joueur: str,
    defenseur: str | None = None,
    type_coup: str | None = None,
    timestamp: float | None = None,
    frame: int | None = None,
) -> dict[str, Any]:
    """Ajoute directement une annotation structuree."""
    parsed = {
        "action": "nouveau_point",
        "joueur": joueur,
        "defenseur": defenseur,
        "type_point": type_point,
        "type_coup": type_coup,
    }
    return SESSION.apply_parsed(parsed, timestamp=timestamp, frame=frame)


@mcp.tool()
def padel_remove_last_stat() -> dict[str, Any]:
    """Supprime la derniere annotation."""
    return SESSION.apply_parsed({"action": "annuler"})


@mcp.tool()
def padel_save_session() -> dict[str, Any]:
    """Declenche une sauvegarde de la session."""
    return SESSION.apply_parsed({"action": "sauvegarder"})


@mcp.tool()
def padel_export_json(output_path: str | None = None) -> dict[str, Any]:
    """Exporte la session courante au format JSON."""
    return SESSION.export_json(output_path=output_path)


@mcp.tool()
def padel_generate_html_report(output_path: str | None = None) -> dict[str, Any]:
    """Genere un rapport HTML rapide de la session courante."""
    return SESSION.export_html(output_path=output_path)


@mcp.tool()
def padel_get_stats() -> dict[str, Any]:
    """Retourne les statistiques courantes avec le classement des meilleurs et pires coups par joueur."""
    return {
        "ok": True,
        "stats": SESSION.manager.get_stats(),
        "shot_rankings": SESSION.manager.get_shot_rankings(),
        "point_count": len(SESSION.manager.get_all_annotations()),
    }


@mcp.tool()
def padel_get_shot_rankings(min_total: int = 2) -> dict[str, Any]:
    """
    Retourne le classement des meilleurs et pires coups par joueur.

    Pour chaque joueur :
    - meilleurs_coups : triés par score_offensif = (gagnants + fp_generees) / total
    - pires_coups     : triés par score_erreurs  = (fautes + fp_subies) / total

    Seuls les coups joués au moins min_total fois sont inclus (défaut : 2).
    """
    rankings = SESSION.manager.get_shot_rankings(min_total=min_total)
    return {
        "ok": True,
        "rankings": rankings,
        "point_count": len(SESSION.manager.get_all_annotations()),
    }


@mcp.tool()
def padel_get_session_state() -> dict[str, Any]:
    """Retourne l'etat courant de la session MCP."""
    return SESSION.get_state()


if __name__ == "__main__":
    mcp.run()
