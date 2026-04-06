"""
Générateur de rapport HTML (v2) avec chargement Chart.js fiable,
normalisation des joueurs et section "Pack des joueurs" détaillée.
"""

import os
from datetime import datetime


class HTMLGenerator2:
    def __init__(self, template_path=None):
        self.template_path = template_path

    def generate_report(self, annotation_manager, output_path=None, fast_mode=True):
        # Essayer de charger Chart.js localement pour inline
        chart_inline = ""
        try:
            base_dir = os.path.dirname(__file__)
            chart_path = os.path.normpath(os.path.join(base_dir, "..", "..", "assets", "vendor", "chart.umd.min.js"))
            if os.path.isfile(chart_path):
                with open(chart_path, 'r', encoding='utf-8') as cf:
                    chart_inline = cf.read()
        except Exception:
            chart_inline = ""
        data = annotation_manager.export_to_dict()
        match = data.get("match", {})
        stats = data.get("stats", {})
        points = data.get("points", [])

        # Normaliser les joueurs en chaînes
        raw_joueurs = match.get("joueurs", [])
        joueurs = [
            (j if isinstance(j, str) else str(j.get("nom", "Joueur")))
            for j in raw_joueurs
        ]

        date = match.get("date", "")
        video = match.get("video", "")
        total_points = len(points)
        total_fautes = sum(1 for p in points if p.get("type") == "faute_directe")
        total_gagnants = sum(1 for p in points if p.get("type") == "point_gagnant")
        total_provoquees = sum(1 for p in points if p.get("type") == "faute_provoquee")

        # Données Impact
        impact_labels = []
        impact_values = []
        impact_detail_rows = []
        for j in joueurs:
            s = stats.get(j, {})
            fd = s.get('fautes_directes', 0)
            pg = s.get('points_gagnants', 0)
            fp_gen = s.get('fautes_provoquees_generees', 0)
            fp_sub = s.get('fautes_provoquees_subies', 0)
            # Impact favorable: PG + FP_gen − (FD + FP_sub)
            impact = (pg + fp_gen) - (fd + fp_sub)
            impact_labels.append(j)
            impact_values.append(impact)
            impact_detail_rows.append((j, fd, fp_sub, pg, fp_gen, impact))

        # Utilisation CDN uniquement pour Chart.js

        # Préparer données répartition par type
        type_counts = {
            'faute_directe': total_fautes,
            'point_gagnant': total_gagnants,
            'faute_provoquee': total_provoquees,
        }

        # Préparer données timeline (cumul au fil du temps)
        timeline_points = []
        cf, cg, cp = 0, 0, 0
        for p in points:
            t = p.get('timestamp', 0)
            typ = p.get('type', '')
            if typ == 'faute_directe':
                cf += 1
            elif typ == 'point_gagnant':
                cg += 1
            elif typ == 'faute_provoquee':
                cp += 1
            timeline_points.append({'x': float(t), 'f': cf, 'g': cg, 'p': cp})

        # Préparer progression par joueur (10 tranches)
        progression_data = {}
        try:
            for j in joueurs:
                prog = annotation_manager.get_player_progression(j)
                progression_data[j] = [seg.get('efficacite', 0) for seg in (prog or [])]
        except Exception:
            progression_data = {j: [] for j in joueurs}

        html = f"""<!DOCTYPE html>
<html lang='fr'>
<head>
  <meta charset='UTF-8'>
  <meta name='viewport' content='width=device-width, initial-scale=1.0'>
  <title>Rapport v2 - {date}</title>
  <!-- Chart.js inline (fallback CDN si vide) -->
  <script>
{chart_inline}
  </script>
  <script>
    if (typeof Chart === 'undefined') {{
      var s = document.createElement('script');
      s.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js';
      document.head.appendChild(s);
    }}
  </script>
  <style>
    body {{ font-family: Inter, Segoe UI, Arial, sans-serif; background:#0b1220; color:#e5e7eb; padding:24px; }}
    .container {{ max-width:1200px; margin:0 auto; }}
    .card {{ background:#111827; padding:24px; border-radius:16px; box-shadow:0 10px 25px rgba(2, 8, 23, 0.35); margin-bottom:24px; border:1px solid #1f2937; }}
    table {{ width:100%; border-collapse:collapse; }}
    th, td {{ padding:10px; border-bottom:1px solid #1f2937; text-align:left; }}
    th {{ background:linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%); color:#fff; }}
    .number {{ font-size:28px; font-weight:700; }}
    .grid {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(320px,1fr)); gap:20px; }}
    .card h2 {{ color:#e5e7eb; margin-bottom:12px; }}
    .sub {{ color:#94a3b8; font-size:14px; margin-bottom:16px; }}
    .badges {{ display:flex; flex-wrap:wrap; gap:8px; margin:8px 0 16px; }}
    .badge {{ display:inline-flex; align-items:center; gap:8px; background:#0f172a; border:1px solid #1f2937; color:#e5e7eb; padding:6px 10px; border-radius:999px; font-size:13px; }}
    .badge .dot {{ width:10px; height:10px; border-radius:50%; display:inline-block; }}
    
    /* Media queries pour mobile */
    @media (max-width: 768px) {{
      body {{ padding: 12px; }}
      .container {{ margin: 0; }}
      .card {{ padding: 16px; margin-bottom: 16px; }}
      .grid {{ grid-template-columns: 1fr; gap: 15px; }}
      .number {{ font-size: 24px; }}
      h2 {{ font-size: 1.3em; }}
      h3 {{ font-size: 1.1em; }}
      table {{ font-size: 0.85em; }}
      th, td {{ padding: 8px 4px; }}
      .badges {{ gap: 6px; }}
      .badge {{ font-size: 12px; padding: 5px 8px; }}
    }}
    
    @media (max-width: 480px) {{
      body {{ padding: 8px; }}
      .card {{ padding: 12px; }}
      .number {{ font-size: 20px; }}
      h2 {{ font-size: 1.2em; }}
      table {{ font-size: 0.75em; }}
      th, td {{ padding: 6px 2px; }}
    }}
  </style>
</head>
<body>
  <div class='container'>
    <div class='card'>
      <h2 style='margin:0'>Résumé</h2>
      <p>{date} — {video}</p>
      <div class='grid'>
        <div class='card'><div>Total Points</div><div class='number'>{total_points}</div></div>
        <div class='card'><div>Fautes Directes</div><div class='number'>{total_fautes}</div></div>
        <div class='card'><div>Points Gagnants</div><div class='number'>{total_gagnants}</div></div>
        <div class='card'><div>Fautes Provoquées</div><div class='number'>{total_provoquees}</div></div>
      </div>
    </div>

    <div class='card'>
      <h2 style='margin-top:0'>Impact des joueurs</h2>
      <div class='badges'>
        <!-- badges joueurs avec couleur -->
        {''.join([f"<span class='badge'><span class='dot' style='background:{c}'></span>{j}</span>" for j,c in zip(joueurs, ['#3b82f6','#ef4444','#22c55e','#f59e0b','#06b6d4','#a78bfa'])])}
      </div>
      <div class='grid'>
        <div class='card'>
          <h3 style='margin-top:0'>Barre (signée)</h3>
          <p class='sub'>Vert: favorable, rouge: défavorable</p>
          <canvas id='impactChart'></canvas>
        </div>
        <div class='card'>
          <h3 style='margin-top:0'>Camembert (parts favorables)</h3>
          <p class='sub'>Parts normalisées sur 100% des impacts favorables</p>
          <canvas id='impactDonut'></canvas>
        </div>
      </div>
      <h3>Détails du calcul</h3>
      <table>
        <thead>
          <tr>
            <th>Joueur</th>
            <th>FD</th>
            <th>FP_sub</th>
            <th>PG</th>
            <th>FP_gen</th>
            <th>Impact favorable (PG + FP_gen − (FD + FP_sub))</th>
          </tr>
        </thead>
        <tbody>
"""

        for row in impact_detail_rows:
            j, fd, fp_sub, pg, fp_gen, imp = row
            html += f"""
          <tr>
            <td>{j}</td>
            <td>{fd}</td>
            <td>{fp_sub}</td>
            <td>{pg}</td>
            <td>{fp_gen}</td>
            <td>{imp}</td>
          </tr>
"""

        html += """
        </tbody>
      </table>
    </div>

    <div class='card'>
      <h2>Répartition par type</h2>
      <p class='sub'>Parts des catégories de points</p>
      <canvas id='typeChart'></canvas>
    </div>

    <div class='card'>
      <h2>Évolution temporelle</h2>
      <p class='sub'>Cumul des actions au fil du match</p>
      <canvas id='timelineChart'></canvas>
    </div>

    <div class='card'>
      <h2>Progression des joueurs</h2>
      <p class='sub'>Efficacité (%) par tranches de 10%</p>
      <canvas id='progressionChart'></canvas>
    </div>
  </div>

  <script>
    // Plugin d'étiquettes de valeurs au-dessus des barres
    const valueLabels = {
      id: 'valueLabels',
      afterDatasetsDraw(chart, args, pluginOptions) {
        const {ctx, chartArea: {top}, scales} = chart;
        const yScale = scales.y;
        const xScale = scales.x || chart.scales.x;
        chart.data.datasets.forEach((ds, dsIndex) => {
          const meta = chart.getDatasetMeta(dsIndex);
          meta.data.forEach((bar, i) => {
            const val = ds.data[i];
            if (val === null || val === undefined) return;
            const x = bar.x;
            const y = bar.y - 6;
            ctx.save();
            ctx.fillStyle = '#e5e7eb';
            ctx.font = '12px Inter, Segoe UI, Arial';
            ctx.textAlign = 'center';
            ctx.fillText(val, x, y);
            ctx.restore();
          });
        });
      }
    };

    function initCharts() {
      if (typeof Chart === 'undefined') { return; }
      const labels = """ + str(impact_labels).replace("'", "\"") + """;
      const values = """ + str(impact_values) + """;
      const pairs = labels.map((l,i)=>({label:l, value: values[i]})).sort((a,b)=>b.value-a.value);
      const sLabels = pairs.map(p=>p.label);
      const sValues = pairs.map(p=>p.value);
      const ctx = document.getElementById('impactChart');
      new Chart(ctx, {
        type: 'bar',
        data: {
          labels: sLabels,
          datasets: [{
            label: 'Impact favorable (plus haut est meilleur)',
            data: sValues,
            backgroundColor: sValues.map(v => v > 0 ? '#22c55e' : (v < 0 ? '#ef4444' : '#9ca3af'))
          }]
        },
        options: {
          responsive:true,
          plugins:{ legend:{ position:'bottom', labels:{ color:'#e5e7eb' } } },
          scales:{
            x:{ ticks:{ color:'#cbd5e1' } },
            y:{ beginAtZero:true, ticks:{ color:'#cbd5e1' }, grid:{ color:'#1f2937' } }
          }
        },
        plugins: [valueLabels]
      });

      // Donut des parts favorables (normalisées sur 100%)
      const dctx = document.getElementById('impactDonut');
      const positive = sValues.map(v=> Math.max(v, 0));
      const totalPos = positive.reduce((a,b)=>a+b, 0);
      const donutValues = totalPos > 0 ? positive.map(v=> v) : sValues.map(()=>0);
      const donutColors = ['#3b82f6', '#ef4444', '#22c55e', '#f59e0b', '#06b6d4', '#a78bfa'];
      new Chart(dctx, {
        type: 'doughnut',
        data: {
          labels: sLabels,
          datasets: [{
            data: donutValues,
            backgroundColor: sLabels.map((_,i)=> donutColors[i % donutColors.length])
          }]
        },
        options: {
          responsive:true,
          plugins:{
            legend:{ position:'bottom', labels:{ color:'#e5e7eb' } },
            tooltip:{
              callbacks:{
                label: function(ctx){
                  const raw = ctx.raw;
                  const pct = totalPos > 0 ? ((raw/totalPos)*100).toFixed(1) + '%': '0%';
                  return ctx.label + ': ' + raw + ' (' + pct + ')';
                }
              }
            }
          }
        }
      });

      // Répartition par type (doughnut)
      const tctx = document.getElementById('typeChart');
      new Chart(tctx, {
        type: 'doughnut',
        data: {
          labels: ['Fautes Directes', 'Points Gagnants', 'Fautes Provoquées'],
          datasets: [{
            data: [{type_counts['faute_directe']}, {type_counts['point_gagnant']}, {type_counts['faute_provoquee']}],
            backgroundColor: ['#ef4444', '#22c55e', '#f59e0b']
          }]
        },
        options: { responsive:true, plugins:{ legend:{ position:'bottom', labels:{ color:'#e5e7eb' } } } }
      });

      // Timeline cumulée
      const tlctx = document.getElementById('timelineChart');
      const tl = """ + str(timeline_points) + """;
      new Chart(tlctx, {
        type: 'line',
        data: {
          datasets: [
            { label:'Fautes directes', data: tl.map(d=>({x:d.x, y:d.f})), borderColor:'#ef4444', backgroundColor:'#ef44441a', fill:true },
            { label:'Points gagnants', data: tl.map(d=>({x:d.x, y:d.g})), borderColor:'#22c55e', backgroundColor:'#22c55e1a', fill:true },
            { label:'Fautes provoquées', data: tl.map(d=>({x:d.x, y:d.p})), borderColor:'#f59e0b', backgroundColor:'#f59e0b1a', fill:true }
          ]
        },
        options: {
          responsive:true,
          plugins:{ legend:{ position:'bottom', labels:{ color:'#e5e7eb' } } },
          scales:{ x:{ type:'linear', title:{ display:true, text:'Temps (s)', color:'#cbd5e1' }, ticks:{ color:'#cbd5e1' }, grid:{ color:'#1f2937' } }, y:{ beginAtZero:true, ticks:{ color:'#cbd5e1' }, grid:{ color:'#1f2937' } } }
        }
      });

      // Progression par joueur
      const prctx = document.getElementById('progressionChart');
      const pr = """ + str(progression_data) + """;
      const colors = ['#3b82f6', '#ef4444', '#22c55e', '#f59e0b', '#06b6d4', '#a78bfa'];
      const datasets = Object.keys(pr).map((name, idx)=>({
        label: name,
        data: (pr[name]||[]),
        borderColor: colors[idx % colors.length],
        backgroundColor: colors[idx % colors.length] + '33',
        tension: 0.4,
        fill: false
      }));
      new Chart(prctx, {
        type: 'line',
        data: { labels: ['10%','20%','30%','40%','50%','60%','70%','80%','90%','100%'], datasets },
        options: {
          responsive:true,
          plugins:{ legend:{ position:'bottom', labels:{ color:'#e5e7eb' } } },
          scales:{ y:{ beginAtZero:true, max:100, title:{ display:true, text:'Efficacité (%)', color:'#cbd5e1' }, ticks:{ color:'#cbd5e1' }, grid:{ color:'#1f2937' } }, x:{ title:{ display:true, text:'Progression du match', color:'#cbd5e1' }, ticks:{ color:'#cbd5e1' }, grid:{ color:'#1f2937' } } }
        }
      });
    }

    window.addEventListener('load', function() {
      if (typeof Chart === 'undefined') {
        // Charger CDN dynamiquement et initialiser à la fin
        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js';
        script.onload = initCharts;
        script.onerror = function(){
          const cont = document.querySelector('.container');
          const warn = document.createElement('div');
          warn.className = 'card';
          warn.innerHTML = "<strong>Erreur:</strong> Chart.js introuvable. Vérifiez la connexion ou le fichier local.";
          cont.prepend(warn);
        };
        document.head.appendChild(script);
      } else {
        initCharts();
      }
    });
  </script>
</body>
</html>
"""

        # Sortie
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = os.path.join(annotation_manager.data_folder, f'rapport_v2_{timestamp}.html')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        return output_path
