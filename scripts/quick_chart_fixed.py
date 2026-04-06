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
            {"joueur": j, "fd": fd, "fp_sub": fp_sub, "pg": pg, "fp_gen": fp_gen, "impact": impact}
        )

    date = match.get("date", "")
    video = match.get("video", "")

    TEMPLATE = """<!DOCTYPE html>
<html lang=\"fr\">
<head>
  <meta charset=\"UTF-8\" />
  <title>Rapport Test Point - __DATE__</title>
  <script src=\"https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js\"></script>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    body{font-family:Inter,Segoe UI,Arial,sans-serif;background:#0f172a;color:#e2e8f0;padding:28px;}
    .wrap{max-width:1200px;margin:0 auto;}
    .card{background:linear-gradient(180deg,#0b1220 0%,#0a1120 100%);padding:28px;border-radius:18px;box-shadow:0 12px 40px rgba(2,8,23,0.45);max-width:1200px;margin:0 auto 20px;border:1px solid #1e293b;}
    h2,h3{margin:0 0 8px 0}
    .sub{color:#6b7280;margin-bottom:12px}
    .chips{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0 16px}
    .chip{padding:6px 10px;border-radius:999px;border:1px solid #e5e7eb;font-size:12px;color:#374151;background:#fafafa}
    .chip.ok{border-color:#22c55e;color:#166534;background:#ecfdf5}
    .chip.bad{border-color:#ef4444;color:#7f1d1d;background:#fef2f2}
    .chip.neutre{border-color:#9ca3af;color:#374151;background:#f9fafb}
    canvas{background:#fff;border:1px solid #edf2f7;border-radius:10px;height:360px !important;}
    table{background:#fff;border:1px solid #e5e7eb;border-radius:10px;overflow:hidden}
    th, td{color:#1f2937}
    thead th{background:#f9fafb}
    .legend-compact{display:flex;gap:10px;flex-wrap:wrap;margin-top:10px;color:#94a3b8;font-size:13px}
    .legend-compact .item{display:flex;align-items:center;gap:6px}
    .legend-compact .swatch{width:12px;height:12px;border-radius:3px;border:1px solid #1e293b}
  </style>
</head>
<body>
  <div class=\"card\">
    <h2 style=\"margin-top:0\">Impact des joueurs</h2>
    <p class=\"sub\">Source: __VIDEO__</p>
    <div class=\"chips\" id=\"summaryChips\"></div>
    <canvas id=\"impactChart\"></canvas>
  </div>
  <div class=\"card\" style=\"margin-top:16px\">
    <h3 style=\"margin-top:0\">Détails par joueur</h3>
    <table style=\"width:100%;border-collapse:collapse\">
      <thead>
        <tr>
          <th style=\"text-align:left;padding:8px;border-bottom:1px solid #eee\">Joueur</th>
          <th style=\"text-align:left;padding:8px;border-bottom:1px solid #eee\">FD</th>
          <th style=\"text-align:left;padding:8px;border-bottom:1px solid #eee\">FP_sub</th>
          <th style=\"text-align:left;padding:8px;border-bottom:1px solid #eee\">PG</th>
          <th style=\"text-align:left;padding:8px;border-bottom:1px solid #eee\">FP_gen</th>
          <th style=\"text-align:left;padding:8px;border-bottom:1px solid #eee\">Impact (PG + FP_gen − (FD + FP_sub))</th>
        </tr>
      </thead>
      <tbody id=\"detailBody\"></tbody>
    </table>
  </div>
  <div class=\"card\" style=\"margin-top:16px\">
    <h3 style=\"margin-top:0\">Camembert des impacts favorables</h3>
    <p class=\"muted\">Parts normalisées sur 100% des impacts favorables</p>
    <canvas id=\"impactDonut\"></canvas>
  </div>
  <script>
    const labels = __LABELS__;
    const dataVals = __IMPACTS__;
    const details = __DETAILS__;
    const pairs = labels.map((l,i)=>({label:l,value:dataVals[i]})).sort((a,b)=>b.value-a.value);
    const sortedLabels = pairs.map(p=>p.label);
    const sortedValues = pairs.map(p=>p.value);
    const minVal = Math.min(...sortedValues);
    const maxVal = Math.max(...sortedValues);
    const range = (maxVal - minVal) || 1;

    const ctx = document.getElementById('impactChart');
    // Plugin simple pour afficher les valeurs au-dessus des barres
    const valueLabelsPlugin = {
      id: 'valueLabels',
      afterDatasetsDraw(chart, args, pluginOptions) {
        const { ctx } = chart;
        ctx.save();
        ctx.fillStyle = '#374151';
        ctx.font = '12px Segoe UI, Arial';
        chart.getDatasetMeta(0).data.forEach((bar, idx) => {
          const val = chart.data.datasets[0].data[idx];
          const x = bar.x;
          const y = bar.y - 6;
          ctx.textAlign = 'center';
          ctx.fillText(val, x, y);
        });
        ctx.restore();
      }
    };

    new Chart(ctx, {
      type: 'bar',
      data: {
        labels: sortedLabels,
        datasets: [{
          label: 'Impact favorable',
          data: sortedValues,
          // Vert pour positif, rouge pour négatif, gris pour zéro
          backgroundColor: sortedValues.map(v => (v > 0 ? '#22c55e' : (v < 0 ? '#ef4444' : '#6b7280')))
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { position: 'bottom' } },
        scales: { y: { beginAtZero: true, grid: { color: '#eef2f7' } }, x: { grid: { display:false } } }
      },
      plugins: [valueLabelsPlugin]
    });

    const body = document.getElementById('detailBody');
    const detailByImpact = details.slice().sort((a,b)=> b.impact - a.impact);
    body.innerHTML = detailByImpact.map(row => (
      `<tr>`+
      `<td>${row.joueur}</td>`+
      `<td>${row.fd}</td>`+
      `<td>${row.fp_sub}</td>`+
      `<td>${row.pg}</td>`+
      `<td>${row.fp_gen}</td>`+
      `<td>${row.impact}</td>`+
      `</tr>`
    )).join('');

    const dctx = document.getElementById('impactDonut');
    // Camembert sur impacts favorables uniquement
    const donutValues = sortedValues.map(v => Math.max(v, 0));
    const donutColors = ['#3b82f6', '#ef4444', '#22c55e', '#f59e0b', '#06b6d4', '#a78bfa'];
    new Chart(dctx, {
      type: 'doughnut',
      data: {
        labels: sortedLabels,
        datasets: [{
          data: donutValues,
          backgroundColor: sortedLabels.map((_,i)=> donutColors[i % donutColors.length])
        }]
      },
      options: {
        responsive: true,
        plugins: {
          legend: { position: 'bottom' },
          tooltip: {
            callbacks: {
              label: function(ctx) {
                const raw = ctx.raw;
                const total = donutValues.reduce((a,b)=>a+b,0) || 1;
                const pct = ((raw/total)*100).toFixed(1) + '%';
                return ctx.label + ': ' + raw + ' (' + pct + ')';
              }
            }
          }
        }
      }
    });

    // Légende compacte sous le camembert
    const legend = document.createElement('div');
    legend.className = 'legend-compact';
    const palette = sortedLabels.map((l,i)=>({ label:l, color: donutColors[i % donutColors.length] }));
    legend.innerHTML = palette.map(p=> `<span class="item"><span class="swatch" style="background:${p.color}"></span>${p.label}</span>`).join('');
    dctx.parentElement.appendChild(legend);

    // Chips résumé (meilleur, pire, neutres)
    const bestIdx = sortedValues.indexOf(Math.max(...sortedValues));
    const worstIdx = sortedValues.indexOf(Math.min(...sortedValues));
    const positives = pairs.filter(p=> p.value>0).length;
    const negatives = pairs.filter(p=> p.value<0).length;
    const zeros = pairs.filter(p=> p.value===0).length;
    const chips = document.getElementById('summaryChips');
    chips.innerHTML = [
      `<span class="chip ok">Top: ${sortedLabels[bestIdx]} (${sortedValues[bestIdx]})</span>`,
      `<span class="chip bad">Bas: ${sortedLabels[worstIdx]} (${sortedValues[worstIdx]})</span>`,
      `<span class="chip ok">Positifs: ${positives}</span>`,
      `<span class="chip bad">Négatifs: ${negatives}</span>`,
      `<span class="chip neutre">Neutres: ${zeros}</span>`
    ].join('');
  </script>
</body>
</html>
"""

    html = TEMPLATE.replace("__DATE__", date).replace("__VIDEO__", str(video))
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
    out_path = os.path.join(data_dir, 'rapport_test_point.html')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(out_path)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())