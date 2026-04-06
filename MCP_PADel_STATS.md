# MCP Padel Stats

Serveur MCP metier pour piloter facilement la mise en place des stats padel.

## Lancement

```bat
start_mcp_server.bat
```

Ou:

```bash
python padel_stats_mcp.py
```

## Tools exposes

- `padel_reset_session(data_folder, match_name)`
- `padel_set_players(players)`
- `padel_set_video(video_path)`
- `padel_set_capture_context(timestamp, frame)`
- `padel_parse_stat_command(text)`
- `padel_apply_stat_command(text, timestamp, frame)`
- `padel_add_stat(type_point, joueur, defenseur, type_coup, timestamp, frame)`
- `padel_remove_last_stat()`
- `padel_save_session()`
- `padel_export_json(output_path)`
- `padel_generate_html_report(output_path)`
- `padel_get_stats()`
- `padel_get_session_state()`

## Workflow recommande

1. `padel_reset_session`
2. `padel_set_players(["Arnaud", "Pierre", "Thomas", "Lucas"])`
3. `padel_set_capture_context(timestamp=125.4, frame=3120)` si besoin
4. `padel_apply_stat_command("faute directe Arnaud")`
5. `padel_apply_stat_command("point gagnant Pierre smash")`
6. `padel_save_session`
7. `padel_generate_html_report`

## Exemples de commandes naturelles

- `faute directe Arnaud`
- `point gagnant Pierre service`
- `point gagnant Thomas volee coup droit`
- `faute provoquee Lucas Arnaud`
- `annuler`
- `sauvegarder`

## Notes

- Le serveur MCP gere le metier des stats, pas le micro.
- La capture vocale reste mieux dans l'application locale.
- Les annotations sont stockees via `AnnotationManager`.
