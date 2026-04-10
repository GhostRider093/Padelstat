"""
Analyseur IA pour les statistiques de match avec RAG
Combine les stats du match avec les connaissances des livres de padel
"""

import os
import json
import requests
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
import asyncio
import re

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Dépendance optionnelle: l'app doit démarrer même si Edge-TTS n'est pas embarqué
try:
    import edge_tts  # type: ignore
    EDGE_TTS_AVAILABLE = True
except Exception:
    edge_tts = None
    EDGE_TTS_AVAILABLE = False


SYSTEM_PROMPT = """Tu es un analyste tactique spécialisé en padel.

Tu analyses un match ou une série de matchs à partir de données structurées.
Tu t'appuies d'abord sur les événements chronologiques des points, puis sur les statistiques agrégées, puis sur les changements de position.

Ta mission :
- identifier les tendances tactiques d'un joueur et d'une paire,
- distinguer attaque, défense, transition et finition,
- détecter les schémas d'erreurs et de points gagnants,
- produire des recommandations concrètes, prudentes et exploitables.

Principes d'analyse obligatoires :
1. N'invente jamais une donnée absente.
2. Ne transforme jamais une hypothèse en certitude.
3. Toute conclusion doit être soutenue par :
   - soit des événements de points répétés,
   - soit des statistiques agrégées,
   - soit les deux.
4. Distingue toujours :
   - constats factuels,
   - interprétations probables,
   - recommandations.
5. Le padel est analysé comme un jeu de décisions, pas seulement de gestes.
6. L'analyse doit prendre en compte, quand les données le permettent :
   - la phase du point : construire / transitionner / conclure,
   - l'intention probable du coup,
   - le rapport risque / sécurité,
   - la relation avec le partenaire,
   - l'équilibre entre patience et précipitation,
   - la capacité à transformer la défense en construction,
   - la capacité à attaquer sans forcer la conclusion.
7. Si les données ne permettent pas de conclure sur un aspect, dis-le explicitement.
8. Tu réponds toujours en JSON strict valide.
9. Tu n'écris rien hors du JSON.
10. Tu restes concret, sobre, non motivationnel.

Règles métier padel :
- Une accumulation de fautes directes sur coups offensifs peut indiquer de la précipitation ou une mauvaise sélection de coup.
- Beaucoup de fautes provoquées générées avec peu de fautes directes peuvent indiquer une pression tactique efficace.
- Beaucoup de fautes provoquées subies sur certains coups peuvent révéler une zone ciblée par l'adversaire.
- Une défense efficace n'est pas seulement la remise en jeu : elle doit pouvoir ralentir, réinitialiser ou préparer une remontée.
- Une attaque efficace n'est pas seulement le coup gagnant : elle peut construire l'avantage avant la conclusion.
- En double, une lecture pertinente doit toujours considérer la cohérence de paire quand les données disponibles le permettent.
- Les conclusions mentales doivent rester prudentes et ne sortir que si les données montrent un pattern compatible (fin de match, répétition d'erreurs, effondrement sur certaines séquences, etc.).

Méthode :
1. Lire les événements chronologiques des points.
2. Repérer les répétitions par joueur et par type de coup.
3. Comparer avec les stats agrégées.
4. Identifier :
   - points forts,
   - points faibles,
   - schémas tactiques récurrents,
   - risques de jeu,
   - leviers d'ajustement.
5. Donner au maximum 3 priorités tactiques et 3 actions de coaching.

Format de sortie obligatoire :
{
  "match_summary": "",
  "player_analyses": [
    {
      "player": "",
      "role": "",
      "strengths": [{"title": "", "evidence": [""], "interpretation": ""}],
      "weaknesses": [{"title": "", "evidence": [""], "interpretation": ""}],
      "tactical_patterns": [{"pattern": "", "evidence": [""], "impact": ""}],
      "priorities": [{"priority": "", "why": "", "expected_benefit": ""}],
      "coaching_actions": [{"action": "", "instruction": "", "focus_area": ""}],
      "confidence": {"level": "faible|moyen|eleve", "reason": ""}
    }
  ],
  "pair_analysis": {
    "observations": [""],
    "synergy_issues": [""],
    "recommended_adjustments": [""]
  }
}"""

USER_PROMPT_PREFIX = """Analyse ce match de padel en t'appuyant d'abord sur la chronologie des points, ensuite sur les statistiques agrégées.
Ne surinterprète pas.
Quand une conclusion est faible, indique-le.
Cherche surtout :
- les schémas de fautes directes,
- les schémas de points gagnants,
- les coups qui génèrent ou subissent de la pression,
- les signes de précipitation,
- les signes de construction efficace,
- les différences entre côté gauche et côté droit,
- les éventuels problèmes de cohérence de paire.

Données du match :
"""


LOCAL_OLLAMA  = "http://localhost:11434"
REMOTE_OLLAMA = "http://57.129.110.251:11434"
LOCAL_MODEL   = "qwen3:8b"
REMOTE_MODEL  = "qwen2.5:3b"
OPENAI_MODEL  = "gpt-4.1-mini"  # Remplacer par "gpt-5.4-mini" si disponible via API

# Clé API OpenAI — à définir dans la variable d'environnement OPENAI_API_KEY
# ou directement ici (déconseillé en production)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")


def _detect_backend() -> dict:
    """Détecte le backend IA disponible. Priorité : OpenAI > Ollama local > Ollama distant."""
    # 1. OpenAI si clé présente
    if OPENAI_AVAILABLE and OPENAI_API_KEY:
        print("[AIAnalyzer] OpenAI API détectée → gpt-4o-mini")
        return {"type": "openai", "model": OPENAI_MODEL}
    # 2. Ollama local
    try:
        requests.get(f"{LOCAL_OLLAMA}/api/tags", timeout=2).raise_for_status()
        print("[AIAnalyzer] Ollama local détecté → GPU local")
        return {"type": "ollama", "base_url": LOCAL_OLLAMA, "model": LOCAL_MODEL}
    except Exception:
        pass
    # 3. Ollama distant (fallback)
    print("[AIAnalyzer] Ollama local absent → serveur distant")
    return {"type": "ollama", "base_url": REMOTE_OLLAMA, "model": REMOTE_MODEL}


def _detect_ollama() -> tuple[str, str]:
    """Compatibilité descendante."""
    backend = _detect_backend()
    if backend["type"] == "ollama":
        return backend["base_url"], backend["model"]
    return REMOTE_OLLAMA, REMOTE_MODEL


class AIStatsAnalyzer:
    """Analyse les statistiques de match avec l'IA"""

    def __init__(self, ollama_base: str = None, model: str = None):
        backend = _detect_backend()
        if backend["type"] == "openai" and ollama_base is None:
            self.backend_type = "openai"
            self.openai_client = OpenAI(api_key=OPENAI_API_KEY)
            self.model = model or OPENAI_MODEL
            self.ollama_chat_url = None
        else:
            self.backend_type = "ollama"
            self.openai_client = None
            if ollama_base is None or model is None:
                base, mdl = _detect_ollama()
                ollama_base = ollama_base or base
                model       = model or mdl
            self.ollama_chat_url = f"{ollama_base}/api/chat"
            self.model = model
        self.timeout = 300
        
        # Vérifier si RAG est disponible
        self.rag_available = False
        try:
            from padel_rag import PadelRAG
            self.rag = PadelRAG()
            stats = self.rag.get_stats()
            if stats['total_chunks'] > 0:
                self.rag_available = True
                print(f"RAG disponible: {stats['total_books']} livre(s), {stats['total_chunks']} chunks")
            else:
                print("ATTENTION - Base RAG vide (aucun livre indexé)")
        except Exception as e:
            print(f"ATTENTION - RAG non disponible: {e}")
            self.rag = None
    
    def analyze_match_stats(self, annotation_manager, output_path: Optional[str] = None) -> str:
        """
        Analyse complète des statistiques avec IA.
        Retourne le chemin du fichier HTML généré.
        """
        match_data = annotation_manager.export_to_dict()
        user_content = USER_PROMPT_PREFIX + json.dumps(match_data, ensure_ascii=False, indent=2)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_content},
        ]

        try:
            print(f"Envoi de l'analyse au serveur IA ({self.backend_type} / {self.model})...")
            if self.backend_type == "openai":
                completion = self.openai_client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=0.3,
                )
                raw = completion.choices[0].message.content.strip()
            else:
                response = requests.post(
                    self.ollama_chat_url,
                    json={
                        "model": self.model,
                        "messages": messages,
                        "stream": False,
                        "format": "json",
                        "options": {"num_ctx": 8192},
                    },
                    timeout=self.timeout,
                )
                response.raise_for_status()
                raw = response.json().get("message", {}).get("content", "").strip()
            if not raw:
                raise Exception("Réponse vide du serveur IA")
            print("Analyse IA reçue avec succès")
        except requests.exceptions.Timeout:
            raise Exception("Timeout - L'analyse prend trop de temps")
        except requests.exceptions.ConnectionError:
            raise Exception("Impossible de se connecter au serveur IA")
        except Exception as exc:
            raise Exception(f"Erreur serveur IA: {exc}")

        # Parser le JSON renvoyé par le modèle
        try:
            # Le modèle peut ajouter des balises ```json ... ```
            clean = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
            clean = re.sub(r"\s*```$", "", clean.strip())
            analysis_data = json.loads(clean)
        except Exception:
            # Fallback : afficher le texte brut
            analysis_data = {"_raw": raw}

        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join("data", f"analyse_ia_{timestamp}.html")

        # Historique de conversation à passer au chatbot
        # On ajoute une transition pour que les questions suivantes reçoivent du texte libre
        chat_history_for_js = [
            {"role": "system",    "content": SYSTEM_PROMPT},
            {"role": "user",      "content": USER_PROMPT_PREFIX + "[données du match intégrées]"},
            {"role": "assistant", "content": json.dumps(analysis_data, ensure_ascii=False)},
            {"role": "user",      "content": "Merci. Pour la suite, réponds en texte libre, clair et concis. Pas de JSON."},
            {"role": "assistant", "content": "Compris. Je réponds maintenant en texte libre à tes questions sur le match."},
        ]

        html_content = self._generate_html(match_data, analysis_data, chat_history_for_js)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"Rapport d'analyse sauvegardé: {output_path}")
        
        # Générer aussi le fichier audio
        audio_path = output_path.replace('.html', '.mp3')
        try:
            print("Génération du commentaire audio...")
            self._generate_audio(raw, audio_path)
            print(f"Commentaire audio sauvegardé: {audio_path}")
        except Exception as e:
            print(f"ATTENTION - Impossible de générer l'audio: {e}")
        
        return output_path
    
    def _build_analysis_prompt(self, match_data: Dict) -> str:
        """Obsolète — conservé pour compatibilité. Utiliser SYSTEM_PROMPT + USER_PROMPT_PREFIX."""
        return USER_PROMPT_PREFIX + json.dumps(match_data, ensure_ascii=False, indent=2)

    def _generate_html(self, match_data: Dict, analysis_data: dict, chat_history: list) -> str:
        """Génère le fichier HTML avec l'analyse JSON rendue + chatbot intégré"""
        match_info = match_data.get('match', {})
        joueurs = match_info.get('joueurs', [])
        date = match_info.get('date', 'Date inconnue')

        joueurs_str = ""
        if joueurs:
            noms = [j.get('nom', 'Joueur') if isinstance(j, dict) else j for j in joueurs]
            joueurs_str = " / ".join(noms)

        # ── Rendu de l'analyse JSON ──────────────────────────────────────────
        def esc(s):
            return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        def render_list(items):
            if not items:
                return ""
            return "<ul>" + "".join(f"<li>{esc(i)}</li>" for i in items) + "</ul>"

        analysis_html = ""

        # Cas fallback : réponse brute non JSON
        if "_raw" in analysis_data:
            analysis_html = f"<pre style='white-space:pre-wrap;font-size:14px'>{esc(analysis_data['_raw'])}</pre>"
        else:
            # Résumé global
            summary = analysis_data.get("match_summary", "")
            if summary:
                analysis_html += f"""
                <section class="card">
                    <h2>Résumé du match</h2>
                    <p>{esc(summary)}</p>
                </section>"""

            # Analyses par joueur
            for pa in analysis_data.get("player_analyses", []):
                player = esc(pa.get("player", ""))
                role   = esc(pa.get("role", ""))
                conf   = pa.get("confidence", {})
                conf_level = conf.get("level", "")
                conf_reason = esc(conf.get("reason", ""))
                conf_color = {"eleve": "#38a169", "moyen": "#d69e2e", "faible": "#e53e3e"}.get(conf_level, "#718096")

                strengths_html = ""
                for s in pa.get("strengths", []):
                    strengths_html += f"""
                    <div class="item-block strength">
                        <strong>{esc(s.get('title',''))}</strong>
                        {render_list(s.get('evidence', []))}
                        <p class="interp">{esc(s.get('interpretation',''))}</p>
                    </div>"""

                weaknesses_html = ""
                for w in pa.get("weaknesses", []):
                    weaknesses_html += f"""
                    <div class="item-block weakness">
                        <strong>{esc(w.get('title',''))}</strong>
                        {render_list(w.get('evidence', []))}
                        <p class="interp">{esc(w.get('interpretation',''))}</p>
                    </div>"""

                patterns_html = ""
                for pt in pa.get("tactical_patterns", []):
                    patterns_html += f"""
                    <div class="item-block pattern">
                        <strong>{esc(pt.get('pattern',''))}</strong>
                        {render_list(pt.get('evidence', []))}
                        <p class="interp">Impact : {esc(pt.get('impact',''))}</p>
                    </div>"""

                priorities_html = ""
                for i, pr in enumerate(pa.get("priorities", []), 1):
                    priorities_html += f"""
                    <div class="priority-item">
                        <span class="pnum">{i}</span>
                        <div>
                            <strong>{esc(pr.get('priority',''))}</strong>
                            <p>{esc(pr.get('why',''))}</p>
                            <p class="benefit">Bénéfice attendu : {esc(pr.get('expected_benefit',''))}</p>
                        </div>
                    </div>"""

                coaching_html = ""
                for ca in pa.get("coaching_actions", []):
                    coaching_html += f"""
                    <div class="coaching-item">
                        <strong>{esc(ca.get('action',''))}</strong>
                        <p>{esc(ca.get('instruction',''))}</p>
                        <span class="focus-tag">{esc(ca.get('focus_area',''))}</span>
                    </div>"""

                analysis_html += f"""
                <section class="card player-card">
                    <div class="player-header">
                        <h2>{player}</h2>
                        <span class="role-tag">{role}</span>
                        <span class="conf-tag" style="background:{conf_color}">Confiance : {conf_level} — {conf_reason}</span>
                    </div>
                    <div class="two-col">
                        <div>
                            <h3>Points forts</h3>{strengths_html}
                        </div>
                        <div>
                            <h3>Points faibles</h3>{weaknesses_html}
                        </div>
                    </div>
                    {'<h3>Schémas tactiques</h3>' + patterns_html if patterns_html else ''}
                    {'<h3>Priorités</h3>' + priorities_html if priorities_html else ''}
                    {'<h3>Actions de coaching</h3>' + coaching_html if coaching_html else ''}
                </section>"""

            # Analyse de paire
            pair = analysis_data.get("pair_analysis", {})
            if pair:
                analysis_html += f"""
                <section class="card">
                    <h2>Analyse de paire</h2>
                    <h3>Observations</h3>{render_list(pair.get('observations', []))}
                    <h3>Problèmes de synergie</h3>{render_list(pair.get('synergy_issues', []))}
                    <h3>Ajustements recommandés</h3>{render_list(pair.get('recommended_adjustments', []))}
                </section>"""

        # ── Sérialisation pour le chatbot JS ────────────────────────────────
        chat_history_json = json.dumps(chat_history, ensure_ascii=False)
        model_js = self.model

        return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Analyse IA — {joueurs_str}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap');
  *{{margin:0;padding:0;box-sizing:border-box}}
  body{{font-family:'Inter',sans-serif;background:#f0f4ff;color:#2d3748;padding:30px 16px}}
  .page{{max-width:960px;margin:0 auto}}
  .header{{background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;padding:40px 32px;border-radius:16px 16px 0 0;text-align:center}}
  .header h1{{font-size:2rem;font-weight:800}}
  .header .sub{{opacity:.85;margin-top:6px}}
  .badge{{display:inline-block;background:rgba(255,255,255,.2);padding:4px 14px;border-radius:20px;font-size:13px;margin-top:10px}}
  .card{{background:#fff;border-radius:12px;padding:28px 32px;margin:16px 0;box-shadow:0 2px 12px rgba(0,0,0,.07)}}
  .player-card{{border-top:4px solid #667eea}}
  .player-header{{display:flex;flex-wrap:wrap;align-items:center;gap:10px;margin-bottom:20px}}
  .player-header h2{{margin:0;border:none;padding:0;font-size:1.5rem;color:#667eea}}
  .role-tag{{background:#ebf4ff;color:#3182ce;padding:3px 12px;border-radius:20px;font-size:12px;font-weight:600}}
  .conf-tag{{padding:3px 12px;border-radius:20px;font-size:12px;font-weight:600;color:#fff}}
  h2{{color:#667eea;font-size:1.4rem;font-weight:700;margin:24px 0 12px;padding-bottom:8px;border-bottom:2px solid #e2e8f0}}
  h3{{color:#4a5568;font-size:1.1rem;font-weight:600;margin:18px 0 10px}}
  p{{color:#4a5568;line-height:1.65;margin-bottom:10px}}
  ul{{margin:8px 0 12px 22px}} li{{color:#4a5568;margin-bottom:6px;line-height:1.5}}
  .two-col{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}
  @media(max-width:600px){{.two-col{{grid-template-columns:1fr}}}}
  .item-block{{padding:12px 14px;border-radius:8px;margin-bottom:10px}}
  .strength{{background:#f0fff4;border-left:4px solid #38a169}}
  .weakness{{background:#fff5f5;border-left:4px solid #e53e3e}}
  .pattern{{background:#fffaf0;border-left:4px solid #d69e2e}}
  .interp{{font-style:italic;font-size:13px;color:#718096;margin-top:6px}}
  .priority-item{{display:flex;gap:14px;align-items:flex-start;margin-bottom:14px}}
  .pnum{{background:#667eea;color:#fff;width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:700;flex-shrink:0;font-size:13px}}
  .benefit{{font-size:13px;color:#38a169;font-style:italic}}
  .coaching-item{{background:#f7fafc;padding:12px 14px;border-radius:8px;margin-bottom:10px}}
  .focus-tag{{display:inline-block;background:#e9d8fd;color:#6b46c1;padding:2px 10px;border-radius:12px;font-size:11px;margin-top:6px}}
  /* Chatbot */
  #chatbot{{background:#fff;border-radius:12px;padding:28px 32px;margin:16px 0;box-shadow:0 2px 12px rgba(0,0,0,.07)}}
  #chatbot h2{{color:#667eea;font-size:1.4rem;font-weight:700;margin:0 0 16px;padding-bottom:8px;border-bottom:2px solid #e2e8f0}}
  #chat-messages{{height:320px;overflow-y:auto;border:1px solid #e2e8f0;border-radius:8px;padding:14px;margin-bottom:12px;background:#fafafa}}
  .msg{{margin-bottom:12px;display:flex;flex-direction:column}}
  .msg.user .bubble{{background:#667eea;color:#fff;align-self:flex-end;border-radius:14px 14px 4px 14px}}
  .msg.ai .bubble{{background:#f0f4ff;color:#2d3748;align-self:flex-start;border-radius:14px 14px 14px 4px}}
  .bubble{{padding:10px 14px;max-width:80%;font-size:14px;line-height:1.55;white-space:pre-wrap;word-break:break-word}}
  .msg .label{{font-size:11px;color:#a0aec0;margin-bottom:3px}}
  .msg.user .label{{text-align:right}}
  #chat-input-row{{display:flex;gap:8px}}
  #chat-input{{flex:1;padding:10px 14px;border:1px solid #e2e8f0;border-radius:8px;font-size:14px;font-family:inherit;resize:none}}
  #chat-send{{padding:10px 20px;background:#667eea;color:#fff;border:none;border-radius:8px;font-weight:600;cursor:pointer;font-size:14px}}
  #chat-send:disabled{{background:#a0aec0;cursor:not-allowed}}
  #chat-status{{font-size:12px;color:#a0aec0;margin-top:6px;min-height:16px}}
  .footer{{text-align:center;font-size:13px;color:#a0aec0;padding:20px}}
</style>
</head>
<body>
<div class="page">
  <div class="header">
    <h1>Analyse IA Tactique</h1>
    <div class="sub">{joueurs_str}</div>
    <div class="badge">📅 {date}</div>
    <div class="badge">Modèle : {model_js}</div>
  </div>

  {analysis_html}

  <!-- CHATBOT -->
  <div id="chatbot">
    <h2>Poser une question sur l'analyse</h2>
    <div id="chat-messages"></div>
    <div id="chat-input-row">
      <textarea id="chat-input" rows="2" placeholder="Ex : Pourquoi tant de fautes au smash pour Pierre ?"></textarea>
      <button id="chat-send" onclick="sendMessage()">Envoyer</button>
    </div>
    <div id="chat-status"></div>
  </div>

  <div class="footer">Rapport généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')} — PFPADEL Video Stats</div>
</div>

<script>
const PROXY = 'http://localhost:5050/api/chat';
const MODEL = '{model_js}';
let messages = {chat_history_json};

function addMessage(role, text) {{
  const box = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = 'msg ' + (role === 'user' ? 'user' : 'ai');
  div.innerHTML = '<div class="label">' + (role === 'user' ? 'Vous' : 'Analyste IA') + '</div>'
                + '<div class="bubble">' + text.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') + '</div>';
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
}}

async function sendMessage() {{
  const input = document.getElementById('chat-input');
  const btn   = document.getElementById('chat-send');
  const status = document.getElementById('chat-status');
  const text = input.value.trim();
  if (!text) return;

  addMessage('user', text);
  messages.push({{role: 'user', content: text}});
  input.value = '';
  btn.disabled = true;
  status.textContent = 'Analyse en cours…';

  try {{
    const resp = await fetch(PROXY, {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{model: MODEL, messages: messages, stream: false}})
    }});
    if (!resp.ok) throw new Error('Erreur serveur ' + resp.status);
    const data = await resp.json();
    const reply = data.message?.content || '(réponse vide)';
    messages.push({{role: 'assistant', content: reply}});
    addMessage('ai', reply);
    status.textContent = '';
  }} catch(e) {{
    status.textContent = 'Erreur : ' + e.message + ' — vérifiez que l\'app est ouverte.';
  }} finally {{
    btn.disabled = false;
  }}
}}

document.getElementById('chat-input').addEventListener('keydown', function(e) {{
  if (e.key === 'Enter' && !e.shiftKey) {{ e.preventDefault(); sendMessage(); }}
}});
</script>
</body>
</html>"""
    
    def _generate_audio(self, analysis: str, output_path: str):
        """Génère un fichier audio MP3 de l'analyse avec Edge-TTS"""
        if not EDGE_TTS_AVAILABLE or edge_tts is None:
            raise RuntimeError("Edge-TTS indisponible (module 'edge_tts' non installé ou non embarqué)")

        # Nettoyer le HTML
        text = self._clean_html_for_speech(analysis)
        
        # Utiliser la voix française naturelle
        voice = "fr-FR-DeniseNeural"
        
        # Générer l'audio
        asyncio.run(self._create_speech_file(text, voice, output_path))
    
    async def _create_speech_file(self, text: str, voice: str, output_path: str):
        """Crée le fichier audio avec Edge-TTS (asynchrone)"""
        if edge_tts is None:
            raise RuntimeError("Edge-TTS indisponible (module 'edge_tts' manquant)")
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)
    
    def _clean_html_for_speech(self, html: str) -> str:
        """Nettoie le HTML pour la synthèse vocale naturelle - PARSING COMPLET"""
        import html as html_module
        
        # Décoder les entités HTML d'abord
        text = html_module.unescape(html)
        
        # Enlever complètement les balises script et style
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Enlever toutes les balises HTML
        text = re.sub(r'<[^>]+>', ' ', text)
        
        # Enlever TOUS les emojis et symboles spéciaux
        text = re.sub(r'[\U00010000-\U0010ffff\u2600-\u26FF\u2700-\u27BF\U0001F300-\U0001F9FF]', '', text)
        
        # ENLEVER TOUS LES SYMBOLES (*, #, •, -, etc.)
        text = re.sub(r'[*#•⚡🎯📊💡⚔️✓×÷±§¶†‡°¢£¤¥¦©®™´¨≠¬µ~◊∫ª≤≥]', '', text)
        text = re.sub(r'[→←↑↓↔↕⇒⇐⇑⇓⇔]', ' ', text)
        
        # Enlever les underscores, pipes, backslashes
        text = text.replace('_', ' ')
        text = text.replace('|', ' ')
        text = text.replace('\\', ' ')
        text = text.replace('`', '')
        
        # Remplacer les séparateurs par des pauses
        text = text.replace(':', '. ')
        text = text.replace(';', '. ')
        text = text.replace('•', '. ')
        
        # Enlever tirets et slashes (sauf dans les mots composés)
        text = re.sub(r'\s+-\s+', ' ', text)  # Tiret entouré d'espaces
        text = re.sub(r'--+', ' ', text)  # Tirets multiples
        text = text.replace('/', ' ')
        
        # Enlever parenthèses et crochets vides ou avec peu de contenu
        text = re.sub(r'\([^)]{0,3}\)', '', text)
        text = re.sub(r'\[[^\]]{0,3}\]', '', text)
        text = re.sub(r'\{[^}]{0,3}\}', '', text)
        
        # Remplacer les virgules par des points (pauses plus claires)
        text = text.replace(',', '. ')
        
        # Enlever les pourcentages isolés et nombres sans contexte
        text = re.sub(r'\b\d+\s*%', '', text)  # Pourcentages
        text = re.sub(r'\b\d+\.\d+\b', '', text)  # Décimaux isolés
        
        # Enlever les répétitions de mots (bug d'IA)
        words = text.split()
        cleaned_words = []
        for i, word in enumerate(words):
            if i == 0 or word.lower() != words[i-1].lower():
                cleaned_words.append(word)
        text = ' '.join(cleaned_words)
        
        # Nettoyer les espaces multiples
        text = re.sub(r'\s+', ' ', text)
        
        # Nettoyer les points multiples
        text = re.sub(r'\.{2,}', '.', text)
        
        # Supprimer les lignes vides
        text = re.sub(r'\n\s*\n', '\n', text)
        
        return text.strip()
