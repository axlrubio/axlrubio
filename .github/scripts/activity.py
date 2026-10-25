import json
import os
import random
import sys
import urllib.request
from datetime import date, timedelta

DIAS = 31
W, H = 900, 300
PAD_L, PAD_R, PAD_T, PAD_B = 60, 30, 70, 50

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def obtener_contribuciones(usuario: str, token: str) -> list[tuple[str, int]]:
    body = json.dumps({"query": QUERY, "variables": {"login": usuario}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "errors" in data:
        raise SystemExit(f"Error de la API: {data['errors']}")
    semanas = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    dias = [(d["date"], d["contributionCount"]) for s in semanas for d in s["contributionDays"]]
    return dias[-DIAS:]


def datos_demo() -> list[tuple[str, int]]:
    hoy = date.today()
    random.seed(7)
    return [((hoy - timedelta(days=DIAS - 1 - i)).isoformat(), random.choice([0, 0, 1, 2, 3, 5, 8, 4]))
            for i in range(DIAS)]


def racha_actual(valores: list[int]) -> int:
    n = 0
    for v in reversed(valores):
        if v == 0:
            break
        n += 1
    return n


def generar_svg(dias: list[tuple[str, int]]) -> str:
    valores = [c for _, c in dias]
    total, maximo = sum(valores), max(valores)
    racha = racha_actual(valores)
    tope = max(maximo, 4)
    ancho = W - PAD_L - PAD_R
    alto = H - PAD_T - PAD_B
    paso = ancho / (len(valores) - 1)

    def x(i): return PAD_L + i * paso
    def y(v): return PAD_T + alto - (v / tope) * alto

    pts = [(x(i), y(v)) for i, v in enumerate(valores)]
    linea = " ".join(f"{'M' if i == 0 else 'L'}{px:.1f},{py:.1f}" for i, (px, py) in enumerate(pts))
    area = f"{linea} L{pts[-1][0]:.1f},{PAD_T + alto} L{pts[0][0]:.1f},{PAD_T + alto} Z"

    grid = []
    for k in range(5):
        v = tope * k / 4
        gy = y(v)
        grid.append(f'<line x1="{PAD_L}" y1="{gy:.1f}" x2="{W - PAD_R}" y2="{gy:.1f}" class="grid"/>')
        grid.append(f'<text x="{PAD_L - 12}" y="{gy + 4:.1f}" text-anchor="end" class="axis">{v:g}</text>')

    etiquetas = []
    for i, (d, _) in enumerate(dias):
        if i % 3 == 0 or i == len(dias) - 1:
            etiquetas.append(f'<text x="{x(i):.1f}" y="{H - PAD_B + 22}" text-anchor="middle" class="axis">{d[8:]}</text>')

    puntos = "".join(
        f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{3.5 if v else 2}" class="{"pt" if v else "pt0"}"><title>{d}: {v}</title></circle>'
        for (px, py), (d, v) in zip(pts, dias)
    )

    vacio = ""
    if total == 0:
        vacio = (f'<text x="{W/2}" y="{PAD_T + alto/2}" text-anchor="middle" class="empty">'
                 f'// sin commits todavía — ¡el primero está por llegar!</text>')

    inicio, fin = dias[0][0], dias[-1][0]
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <style>
    text {{ font-family: 'JetBrains Mono', 'Fira Code', Consolas, 'Courier New', monospace; }}
    .title {{ font-size: 15px; fill: #39D353; }}
    .meta  {{ font-size: 13px; fill: #8B949E; }}
    .num   {{ fill: #C9D1D9; font-weight: 700; }}
    .axis  {{ font-size: 11px; fill: #8B949E; }}
    .grid  {{ stroke: #21262D; stroke-dasharray: 3 4; }}
    .line  {{ fill: none; stroke: #39D353; stroke-width: 2.5; stroke-linejoin: round;
              stroke-dasharray: 3000; stroke-dashoffset: 3000; animation: draw 2s ease-out forwards; }}
    .area  {{ fill: url(#g); opacity: 0; animation: fade 1s ease-out 1s forwards; }}
    .pt    {{ fill: #0D1117; stroke: #39D353; stroke-width: 2; }}
    .pt0   {{ fill: #30363D; }}
    .empty {{ font-size: 14px; fill: #8B949E; }}
    @keyframes draw {{ to {{ stroke-dashoffset: 0; }} }}
    @keyframes fade {{ to {{ opacity: 1; }} }}
  </style>
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#39D353" stop-opacity=".35"/>
      <stop offset="1" stop-color="#39D353" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="12" fill="#0D1117" stroke="#30363D" stroke-width="2"/>
  <text x="24" y="32" class="title">$ git log --since="{inicio}" --until="{fin}" | wc -l</text>
  <text x="24" y="54" class="meta">commits: <tspan class="num">{total}</tspan>   ·   mejor día: <tspan class="num">{maximo}</tspan>   ·   racha actual: <tspan class="num">{racha} {"día" if racha == 1 else "días"}</tspan></text>
  {"".join(grid)}
  <path d="{area}" class="area"/>
  <path d="{linea}" class="line"/>
  {puntos}
  {"".join(etiquetas)}
  {vacio}
</svg>
'''


def main():
    args = sys.argv[1:]
    if not args:
        raise SystemExit(__doc__)
    salida = args[1] if len(args) > 1 else "dist/activity.svg"
    if args[0] == "--demo":
        dias = datos_demo()
    else:
        token = os.environ.get("GITHUB_TOKEN") or sys.exit("Falta GITHUB_TOKEN")
        dias = obtener_contribuciones(args[0], token)
    os.makedirs(os.path.dirname(salida) or ".", exist_ok=True)
    with open(salida, "w", encoding="utf-8") as f:
        f.write(generar_svg(dias))
    print(f"✔ {salida} generado ({sum(c for _, c in dias)} contribuciones)")


if __name__ == "__main__":
    main()
