"""Génère une version HTML (jolie) de COMMANDES_VOCALES_COMPLETES.md.

- Pas de dépendances externes.
- Conversion Markdown simple: titres, listes, code fences, blockquotes, liens, gras, code inline.
- Ajoute une table des matières + recherche + bouton copier sur les blocs de code.

Usage:
  python scripts/render_commandes_vocales_completes_html.py
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple


ROOT = Path(__file__).resolve().parents[1]
MD_PATH = ROOT / "COMMANDES_VOCALES_COMPLETES.md"
HTML_PATH = ROOT / "COMMANDES_VOCALES_COMPLETES.html"


_slug_invalid_re = re.compile(r"[^a-z0-9\-\s]+", re.IGNORECASE)
_slug_spaces_re = re.compile(r"\s+")


def slugify(text: str) -> str:
    value = text.strip().lower()
    value = _slug_invalid_re.sub("", value)
    value = value.replace("—", "-").replace("–", "-")
    value = _slug_spaces_re.sub("-", value)
    value = value.strip("-")
    return value or "section"


def _format_inline(text: str) -> str:
    """Formate une ligne (inline) en HTML: code ``, **gras**, liens [t](u)."""
    # Gestion des liens Markdown [texte](url)
    # On traite d'abord les segments hors code inline.
    parts: List[str] = []
    tokens = re.split(r"(`[^`]+`)", text)

    for tok in tokens:
        if tok.startswith("`") and tok.endswith("`") and len(tok) >= 2:
            code = tok[1:-1]
            parts.append(f"<code>{html.escape(code)}</code>")
            continue

        escaped = html.escape(tok)

        # Liens [text](url)
        def repl_link(m: re.Match[str]) -> str:
            label = html.escape(m.group(1))
            url = html.escape(m.group(2), quote=True)
            return f'<a href="{url}" target="_blank" rel="noopener noreferrer">{label}</a>'

        escaped = re.sub(r"\[([^\]]+)\]\(([^\)]+)\)", repl_link, escaped)

        # Gras **text**
        escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)

        # Italique *text* (simple; évite les puces)
        escaped = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", escaped)

        parts.append(escaped)

    return "".join(parts)


@dataclass
class Heading:
    level: int
    title: str
    id: str


def _parse_markdown(md_lines: Iterable[str]) -> Tuple[str, List[Heading]]:
    """Convertit un Markdown simple en HTML."""
    out: List[str] = []
    toc: List[Heading] = []

    in_code = False
    code_lang: Optional[str] = None

    in_ul = False
    in_ol = False
    in_blockquote = False
    paragraph_buf: List[str] = []

    used_ids: dict[str, int] = {}

    def flush_paragraph() -> None:
        nonlocal paragraph_buf
        if paragraph_buf:
            joined = " ".join(s.strip() for s in paragraph_buf if s.strip())
            if joined:
                out.append(f"<p>{_format_inline(joined)}</p>")
        paragraph_buf = []

    def close_lists() -> None:
        nonlocal in_ul, in_ol
        if in_ul:
            out.append("</ul>")
            in_ul = False
        if in_ol:
            out.append("</ol>")
            in_ol = False

    def close_blockquote() -> None:
        nonlocal in_blockquote
        if in_blockquote:
            out.append("</blockquote>")
            in_blockquote = False

    def unique_id(base: str) -> str:
        base_id = slugify(base)
        n = used_ids.get(base_id, 0)
        used_ids[base_id] = n + 1
        if n == 0:
            return base_id
        return f"{base_id}-{n+1}"

    for raw in md_lines:
        line = raw.rstrip("\n")

        # Code fence
        m_fence = re.match(r"^```\s*([a-zA-Z0-9_-]+)?\s*$", line)
        if m_fence:
            if not in_code:
                flush_paragraph()
                close_lists()
                close_blockquote()
                in_code = True
                code_lang = m_fence.group(1)
                cls = f" language-{code_lang}" if code_lang else ""
                out.append(f"<pre class=\"codeblock\"><code class=\"{cls.strip()}\">")
            else:
                out.append("</code></pre>")
                in_code = False
                code_lang = None
            continue

        if in_code:
            out.append(html.escape(line) + "\n")
            continue

        # Horizontal rule
        if line.strip() == "---":
            flush_paragraph()
            close_lists()
            close_blockquote()
            out.append("<hr>")
            continue

        # Headings
        m_head = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m_head:
            flush_paragraph()
            close_lists()
            close_blockquote()
            level = len(m_head.group(1))
            title = m_head.group(2).strip()
            hid = unique_id(title)
            toc.append(Heading(level=level, title=title, id=hid))
            out.append(f"<h{level} id=\"{hid}\">{_format_inline(title)}</h{level}>")
            continue

        # Blockquote
        if line.lstrip().startswith(">"):
            flush_paragraph()
            close_lists()
            if not in_blockquote:
                out.append("<blockquote>")
                in_blockquote = True
            content = line.lstrip()[1:].lstrip()
            if content:
                out.append(f"<p>{_format_inline(content)}</p>")
            continue
        else:
            close_blockquote()

        # Lists
        m_ul = re.match(r"^\s*[-*]\s+(.*)$", line)
        m_ol = re.match(r"^\s*\d+[\.)]\s+(.*)$", line)
        if m_ul:
            flush_paragraph()
            if in_ol:
                out.append("</ol>")
                in_ol = False
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            out.append(f"<li>{_format_inline(m_ul.group(1).strip())}</li>")
            continue
        if m_ol:
            flush_paragraph()
            if in_ul:
                out.append("</ul>")
                in_ul = False
            if not in_ol:
                out.append("<ol>")
                in_ol = True
            out.append(f"<li>{_format_inline(m_ol.group(1).strip())}</li>")
            continue

        # Blank line
        if not line.strip():
            flush_paragraph()
            close_lists()
            continue

        # Paragraph text
        paragraph_buf.append(line)

    flush_paragraph()
    close_lists()
    close_blockquote()

    return "\n".join(out), toc


def _render_toc(toc: List[Heading]) -> str:
    items: List[str] = []
    for h in toc:
        if h.level <= 1:
            continue
        # Indentation légère visuelle
        indent = "&nbsp;" * (max(0, h.level - 2) * 2)
        items.append(f"<a class=\"toc-item level-{h.level}\" href=\"#{h.id}\">{indent}{html.escape(h.title)}</a>")
    return "\n".join(items)


def build_html(body_html: str, toc: List[Heading]) -> str:
    title = "Commandes vocales (PTT) — NanoApp Stat Padel"
    toc_html = _render_toc(toc)

    return f"""<!doctype html>
<html lang=\"fr\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>{html.escape(title)}</title>
  <style>
    :root {{
      --bg0: #0b1220;
      --bg1: #0f172a;
      --card: rgba(255,255,255,.06);
      --card2: rgba(255,255,255,.08);
      --text: #e5e7eb;
      --muted: #9ca3af;
      --border: rgba(255,255,255,.12);
      --primary: #22c55e;
      --warn: #f59e0b;
      --danger: #ef4444;
      --violet: #a855f7;
      --codebg: rgba(0,0,0,.35);
    }}

    * {{ box-sizing: border-box; }}
    html, body {{ height: 100%; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", system-ui, -apple-system, Arial, sans-serif;
      background: radial-gradient(1200px 800px at 20% 10%, rgba(34,197,94,.15), transparent 50%),
                  radial-gradient(900px 650px at 80% 15%, rgba(168,85,247,.15), transparent 50%),
                  linear-gradient(180deg, var(--bg0), var(--bg1));
      color: var(--text);
      line-height: 1.6;
    }}

    a {{ color: #93c5fd; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}

    .wrap {{ max-width: 1280px; margin: 0 auto; padding: 24px; }}

    header {{
      border: 1px solid var(--border);
      background: linear-gradient(180deg, var(--card2), var(--card));
      border-radius: 18px;
      padding: 22px 22px;
      box-shadow: 0 12px 40px rgba(0,0,0,.35);
    }}

    .title {{
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 16px;
      flex-wrap: wrap;
    }}

    h1 {{
      margin: 0;
      font-size: 28px;
      letter-spacing: -0.02em;
    }}

    .subtitle {{ color: var(--muted); font-weight: 500; margin-top: 6px; }}

    .pills {{ display: flex; gap: 10px; flex-wrap: wrap; margin-top: 14px; }}
    .pill {{
      border: 1px solid var(--border);
      background: rgba(255,255,255,.04);
      border-radius: 999px;
      padding: 7px 10px;
      font-size: 13px;
      color: var(--text);
    }}

    .grid {{
      display: grid;
      grid-template-columns: 320px 1fr;
      gap: 18px;
      margin-top: 18px;
    }}

    @media (max-width: 980px) {{
      .grid {{ grid-template-columns: 1fr; }}
      .toc {{ position: relative !important; top: 0 !important; }}
    }}

    .toc {{
      position: sticky;
      top: 18px;
      align-self: start;
      border: 1px solid var(--border);
      background: linear-gradient(180deg, rgba(255,255,255,.06), rgba(255,255,255,.04));
      border-radius: 16px;
      padding: 14px;
    }}

    .toc h2 {{ margin: 0 0 10px 0; font-size: 14px; color: var(--muted); text-transform: uppercase; letter-spacing: .08em; }}

    .search {{
      width: 100%;
      padding: 10px 12px;
      border-radius: 12px;
      border: 1px solid var(--border);
      background: rgba(0,0,0,.25);
      color: var(--text);
      outline: none;
    }}

    .toc-items {{ margin-top: 10px; max-height: 70vh; overflow: auto; padding-right: 6px; }}
    .toc-item {{ display: block; padding: 7px 8px; border-radius: 10px; color: var(--text); }}
    .toc-item:hover {{ background: rgba(255,255,255,.06); text-decoration: none; }}

    main {{
      border: 1px solid var(--border);
      background: rgba(255,255,255,.04);
      border-radius: 16px;
      padding: 22px;
      overflow: hidden;
    }}

    main h2, main h3, main h4 {{ scroll-margin-top: 20px; }}

    hr {{ border: none; border-top: 1px solid var(--border); margin: 20px 0; }}

    blockquote {{
      margin: 14px 0;
      padding: 12px 14px;
      border-left: 4px solid rgba(147,197,253,.8);
      background: rgba(147,197,253,.06);
      border-radius: 12px;
      color: var(--text);
    }}

    code {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace;
      background: rgba(0,0,0,.35);
      border: 1px solid rgba(255,255,255,.10);
      padding: 1px 6px;
      border-radius: 8px;
      font-size: 0.95em;
    }}

    .codeblock {{
      position: relative;
      margin: 14px 0;
      padding: 14px;
      border-radius: 14px;
      background: var(--codebg);
      border: 1px solid rgba(255,255,255,.12);
      overflow: auto;
    }}

    pre code {{
      display: block;
      background: transparent;
      border: none;
      padding: 0;
      white-space: pre;
    }}

    .copybtn {{
      position: absolute;
      top: 10px;
      right: 10px;
      border: 1px solid rgba(255,255,255,.18);
      background: rgba(0,0,0,.35);
      color: var(--text);
      border-radius: 10px;
      padding: 6px 10px;
      cursor: pointer;
      font-size: 12px;
    }}

    .copybtn:hover {{ background: rgba(255,255,255,.08); }}

    ul, ol {{ padding-left: 22px; }}
    li {{ margin: 6px 0; }}

    .footer {{ color: var(--muted); font-size: 13px; margin-top: 18px; }}
  </style>
</head>
<body>
  <div class=\"wrap\">
    <header>
      <div class=\"title\">
        <h1>🎤 Commandes Vocales Complètes (PTT)</h1>
        <div class=\"pill\">Fichier source: COMMANDES_VOCALES_COMPLETES.md</div>
      </div>
      <div class=\"subtitle\">
        Push-to-Talk (touche <code>V</code>) • drapeau 🟩/🟥 • review + écoute WAV • marqueurs violets
      </div>
      <div class=\"pills\">
        <div class=\"pill\">PTT: <strong>V</strong> = start/stop</div>
        <div class=\"pill\">Audio: <strong>data/voice_audio</strong></div>
        <div class=\"pill\">Review: vidéo + WAV + correction</div>
        <div class=\"pill\">Timeline: triangles <span style=\"color: var(--violet)\">violets</span> (non reconnues)</div>
      </div>
    </header>

    <div class=\"grid\">
      <aside class=\"toc\">
        <h2>Sommaire</h2>
        <input class=\"search\" id=\"search\" placeholder=\"Rechercher (ex: faute directe, smash, review)…\" />
        <div class=\"toc-items\" id=\"toc\">
          {toc_html}
        </div>
      </aside>

      <main id=\"content\">
        {body_html}
        <div class=\"footer\">Généré automatiquement depuis le Markdown. Astuce: <code>Ctrl+F</code> fonctionne aussi.</div>
      </main>
    </div>
  </div>

  <script>
    // Filtre TOC + contenu (simple)
    const search = document.getElementById('search');
    const toc = document.getElementById('toc');
    const content = document.getElementById('content');

    function normalize(s) {{
      // Supprime les accents après normalisation NFD.
      return (s || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
    }}

    function applyFilter(q) {{
      const query = normalize(q);
      const tocItems = toc.querySelectorAll('a.toc-item');
      tocItems.forEach(a => {{
        const show = normalize(a.textContent).includes(query);
        a.style.display = show ? 'block' : 'none';
      }});

      // Highlight léger dans le contenu (sans modifier le DOM lourdement)
      const marks = content.querySelectorAll('mark.__hit');
      marks.forEach(m => {{
        const parent = m.parentNode;
        parent.replaceChild(document.createTextNode(m.textContent), m);
        parent.normalize();
      }});

      if (!query) return;

      // Marquage naïf des occurrences dans les paragraphes + listes
      const nodes = content.querySelectorAll('p, li, h2, h3, h4');
      nodes.forEach(n => {{
        const text = n.textContent;
        const idx = normalize(text).indexOf(query);
        if (idx >= 0) {{
          // Remplace uniquement la première occurrence pour rester léger
          const before = text.slice(0, idx);
          const hit = text.slice(idx, idx + q.length);
          const after = text.slice(idx + q.length);
          n.innerHTML = '';
          n.appendChild(document.createTextNode(before));
          const mark = document.createElement('mark');
          mark.className = '__hit';
          mark.style.background = 'rgba(245, 158, 11, .25)';
          mark.style.color = 'inherit';
          mark.style.borderRadius = '8px';
          mark.style.padding = '0 4px';
          mark.textContent = hit;
          n.appendChild(mark);
          n.appendChild(document.createTextNode(after));
        }}
      }});
    }}

    search.addEventListener('input', (e) => applyFilter(e.target.value));

    // Boutons copier sur les blocs de code
    document.querySelectorAll('pre.codeblock').forEach(pre => {{
      const btn = document.createElement('button');
      btn.className = 'copybtn';
      btn.textContent = 'Copier';
      btn.addEventListener('click', async () => {{
        const code = pre.querySelector('code');
        const text = code ? code.textContent : '';
        try {{
          await navigator.clipboard.writeText(text);
          btn.textContent = 'Copié ✓';
          setTimeout(() => btn.textContent = 'Copier', 1200);
        }} catch (err) {{
          btn.textContent = 'Erreur';
          setTimeout(() => btn.textContent = 'Copier', 1200);
        }}
      }});
      pre.appendChild(btn);
    }});
  </script>
</body>
</html>
"""


def main() -> int:
    if not MD_PATH.exists():
        raise SystemExit(f"Markdown introuvable: {MD_PATH}")

    md_text = MD_PATH.read_text(encoding="utf-8")
    body_html, toc = _parse_markdown(md_text.splitlines())

    html_text = build_html(body_html, toc)
    HTML_PATH.write_text(html_text, encoding="utf-8")

    print(f"[OK] Généré: {HTML_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
