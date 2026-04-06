import os
import json
from datetime import datetime


def find_latest_analysis(data_dir):
    candidates = []
    for name in os.listdir(data_dir):
        if name.startswith("match_") and name.endswith(".json"):
            path = os.path.join(data_dir, name)
            try:
                mtime = os.path.getmtime(path)
            except OSError:
                continue
            candidates.append((mtime, path))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def build_html(match_data):
    match = match_data.get("match", {})
    stats = match_data.get("stats", {})
    joueurs = match.get("joueurs", [])
    joueurs = [
        (j if isinstance(j, str) else str(j.get("nom", "Joueur"))) for j in joueurs
    ]

    labels = []
    impacts = []
    detail_rows = []
    for j in joueurs:
        s = stats.get(j, {})
        fd = s.get("fautes_directes", 0)
        pg = s.get("points_gagnants", 0)
        fp_gen = s.get("fautes_provoquees_generees", 0)
        fp_sub = s.get("fautes_provoquees_subies", 0)
        impact = (pg + fp_gen) - (fd + fp_sub)
        labels.append(j)
        impacts.append(impact)
        detail_rows.append(
            {
                "joueur": j,
                "fd": fd,
                "fp_sub": fp_sub,
                "pg": pg,
                "fp_gen": fp_gen,
                "impact": impact,
            }
        )

    date = match.get("date", "")
    video = match.get("video", "")

    chartjs_local_src = "../assets/vendor/chart.umd.min.js"

    TEMPLATE = """<!DOCTYPE html>
<html lang=\"fr\">
<head>
  <meta charset=\"UTF-8\" />
  <title>Graphique rapide - __DATE__</title>
  <script src=\"__CHARTJS_LOCAL__\"></script>
  <script src=\"https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js\"></script>
  <style>
    body{font-family:Segoe UI,Arial,sans-serif;background:#0b1220;color:#e5e7eb;padding:20px;}
    .card{background:#111827;padding:24px;border-radius:12px;box-shadow:0 4px 12px rgba(0,0,0,0.3);max-width:1200px;margin:16px auto;border:1px solid #1f2937;}
    canvas{background:#1f2937;border-radius:8px;}
    table{border-collapse:collapse;width:100%;}
    th{text-align:left;padding:12px;border-bottom:2px solid #374151;color:#9ca3af;font-weight:600;font-size:0.875rem;}
    td{padding:12px;border-bottom:1px solid #1f2937;color:#e5e7eb;}
    tr:hover{background:#1f2937;}
    .positive{color:#10b981;font-weight:600;}
    .negative{color:#ef4444;font-weight:600;}
    .neutral{color:#6b7280;}
    h2,h3{color:#f3f4f6;margin-top:0;}
    .subtitle{color:#9ca3af;font-size:0.875rem;margin-top:8px;}
  </style>
</head>
<body>
  <div class=\"card\">
    <h2>📊 Impact des joueurs</h2>
    <p class=\"subtitle\">Source: __VIDEO__ • Date: __DATE__</p>
    <canvas id=\"impactChart\" height=\"80\"></canvas>
  </div>
  
  <div class=\"card\">
    <h3>📈 Statistiques détaillées par joueur</h3>
    <p class=\"subtitle\">Impact = (Points Gagnants + Fautes Provoquées Générées) − (Fautes Directes + Fautes Provoquées Subies)</p>
    <table>
      <thead>
        <tr>
          <th>Joueur</th>
          <th>FD<br><span style=\"font-weight:400;font-size:0.75rem\">(Fautes Directes)</span></th>
          <th>FP subies<br><span style=\"font-weight:400;font-size:0.75rem\">(Provoquées)</span></th>
          <th>PG<br><span style=\"font-weight:400;font-size:0.75rem\">(Points Gagnants)</span></th>
          <th>FP générées<br><span style=\"font-weight:400;font-size:0.75rem\">(Provoquées)</span></th>
          <th>Impact Total</th>
        </tr>
      </thead>
      <tbody id=\"detailBody\"></tbody>
    </table>
  </div>
  
  <div class=\"card\">
    <h3>🥧 Répartition des impacts positifs</h3>
    <p class=\"subtitle\">Distribution des contributions favorables (en %)</p>
    <canvas id=\"impactDonut\" height=\"100\"></canvas>
  </div>
  <script>
    const labels = __LABELS__;
    const dataVals = __IMPACTS__;
    const details = __DETAILS__;
    const pairs = labels
      .map((l,i)=>({label:l,value:dataVals[i]}))
      .sort((a,b)=>b.value-a.value);
    const sortedLabels = pairs.map(p=>p.label);
    const sortedValues = pairs.map(p=>p.value);

    // Bar chart couleurs: >0 vert, <0 rouge, =0 gris
    const ctx = document.getElementById('impactChart');
    new Chart(ctx, {
      type: 'bar',
      data: {
        labels: sortedLabels,
        datasets: [{
          label: 'Impact favorable',
          data: sortedValues,
          backgroundColor: sortedValues.map(v => (
            v > 0 ? '#10b981' : (v < 0 ? '#ef4444' : '#6b7280')
          )),
          borderWidth: 0
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { 
          legend: { 
            display: true,
            labels: { color: '#9ca3af', font: { size: 12 } }
          },
          tooltip: {
            backgroundColor: '#1f2937',
            titleColor: '#f3f4f6',
            bodyColor: '#e5e7eb',
            borderColor: '#374151',
            borderWidth: 1
          }
        },
        scales: { 
          y: { 
            beginAtZero: true,
            grid: { color: '#374151' },
            ticks: { color: '#9ca3af' }
          },
          x: {
            grid: { display: false },
            ticks: { color: '#9ca3af' }
          }
        }
      }
    });

    // Détails table (trié par impact)
    const body = document.getElementById('detailBody');
    const detailByImpact = details.slice().sort((a,b)=> b.impact - a.impact);
    body.innerHTML = detailByImpact.map(row => {
      const impactClass = row.impact > 0 ? 'positive' : (row.impact < 0 ? 'negative' : 'neutral');
      return (
        `<tr>`+
        `<td style="font-weight:600">${row.joueur}</td>`+
        `<td>${row.fd}</td>`+
        `<td>${row.fp_sub}</td>`+
        `<td>${row.pg}</td>`+
        `<td>${row.fp_gen}</td>`+
        `<td class="${impactClass}" style="font-size:1.1rem">${row.impact > 0 ? '+' : ''}${row.impact}</td>`+
        `</tr>`
      );
    }).join('');

    // Donut des parts favorables
    const dctx = document.getElementById('impactDonut');
    const positive = sortedValues.map(v=> Math.max(v, 0));
    const totalPos = positive.reduce((a,b)=>a+b, 0);
    const donutValues = totalPos > 0 ? positive : sortedValues.map(()=>0);
    const donutColors = [
      '#667eea', '#f59e0b', '#10b981', '#06b6d4', '#ec4899', '#a78bfa'
    ];
    new Chart(dctx, {{
      type: 'doughnut',
      data: {{
        labels: sortedLabels,
        datasets: [{
          data: donutValues,
          backgroundColor: sortedLabels.map((_,i)=> donutColors[i % donutColors.length]),
          borderWidth: 0
        }]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
          legend: {{ 
            position: 'bottom',
            labels: {{ color: '#9ca3af', font: {{ size: 12 }} }}
          }},
          tooltip: {{
            backgroundColor: '#1f2937',
            titleColor: '#f3f4f6',
            bodyColor: '#e5e7eb',
            borderColor: '#374151',
            borderWidth: 1,
            callbacks: {{
              label: function(ctx) {{
                const raw = ctx.raw;
                const pct = totalPos > 0
                  ? ((raw/totalPos)*100).toFixed(1) + '%'
                  : '0%';
                return ctx.label + ': ' + raw + ' (' + pct + ')';
              }}
            }}
          }}
        }}
      }}
    }});
  </script>
</body>
</html>
"""

    html = TEMPLATE.replace("__DATE__", date).replace("__CHARTJS_LOCAL__", chartjs_local_src).replace("__VIDEO__", str(video))
    html = html.replace("__LABELS__", json.dumps(labels, ensure_ascii=False))
    html = html.replace("__IMPACTS__", json.dumps(impacts))
    html = html.replace("__DETAILS__", json.dumps(detail_rows, ensure_ascii=False))
    return html


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(root, 'data')
    latest = find_latest_analysis(data_dir)
    if not latest:
        print("Aucun fichier d'analyse 'match_*.json' trouvé dans data/")
        return 1
    with open(latest, 'r', encoding='utf-8') as f:
        match_data = json.load(f)
    html = build_html(match_data)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_path = os.path.join(data_dir, f'rapport_quick_{ts}.html')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(out_path)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
