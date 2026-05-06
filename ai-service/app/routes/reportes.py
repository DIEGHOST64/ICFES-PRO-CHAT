"""
RF-20, RF-21, RF-24, RF-25: Endpoints de generación de reportes.
GET /reportes/excel → archivo Excel con resumen, detalle, tendencia y temas.
GET /reportes/pdf   → informe PDF institucional con gráficos Plotly.
"""

import io
import base64
import html
import httpx
import pandas as pd
from datetime import datetime
from fastapi import APIRouter, Query as QueryParam, HTTPException, Request
from fastapi.responses import StreamingResponse

router = APIRouter()

BACKEND_URL = "http://backend/api"


def _to_number(value, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        text = str(value).replace("%", "").strip()
        return float(text)
    except Exception:
        return default


def build_bar_chart_svg(title: str, labels: list[str], values: list[float], color: str = "#4F46E5") -> str:
    """Genera un grafico de barras SVG listo para incrustar en el PDF."""
    if not labels or not values:
        return ""

    width = 860
    height = 280
    padding_top = 38
    padding_right = 20
    padding_bottom = 56
    padding_left = 46
    chart_w = width - padding_left - padding_right
    chart_h = height - padding_top - padding_bottom

    safe_values = [max(0.0, _to_number(v)) for v in values]
    max_v = max(safe_values) if safe_values else 1.0
    if max_v <= 0:
        max_v = 1.0

    n = len(labels)
    bar_gap = 10
    bar_w = max(14, (chart_w - (bar_gap * (n + 1))) / max(n, 1))

    bars = []
    texts = []
    for i, (label, value) in enumerate(zip(labels, safe_values)):
        bar_h = (value / max_v) * chart_h
        x = padding_left + bar_gap + i * (bar_w + bar_gap)
        y = padding_top + chart_h - bar_h

        bars.append(
            f"<rect x='{x:.1f}' y='{y:.1f}' width='{bar_w:.1f}' height='{bar_h:.1f}' rx='4' fill='{color}' />"
        )
        texts.append(
            f"<text x='{x + (bar_w / 2):.1f}' y='{padding_top + chart_h + 16:.1f}' text-anchor='middle' font-size='10' fill='#374151'>{html.escape(str(label)[:16])}</text>"
        )
        texts.append(
            f"<text x='{x + (bar_w / 2):.1f}' y='{max(padding_top + 12, y - 6):.1f}' text-anchor='middle' font-size='10' fill='#111827'>{int(round(value))}</text>"
        )

    grid = []
    for t in [0, 0.25, 0.5, 0.75, 1.0]:
        gy = padding_top + chart_h - (chart_h * t)
        gv = max_v * t
        grid.append(f"<line x1='{padding_left}' y1='{gy:.1f}' x2='{padding_left + chart_w}' y2='{gy:.1f}' stroke='#E5E7EB' stroke-width='1' />")
        grid.append(f"<text x='{padding_left - 6}' y='{gy + 4:.1f}' text-anchor='end' font-size='10' fill='#6B7280'>{int(round(gv))}</text>")

    svg = f"""
<svg viewBox='0 0 {width} {height}' width='100%' xmlns='http://www.w3.org/2000/svg'>
  <rect x='0' y='0' width='{width}' height='{height}' fill='#FFFFFF' rx='8' />
  <text x='{padding_left}' y='22' font-size='14' font-weight='700' fill='#111827'>{html.escape(title)}</text>
  {''.join(grid)}
  {''.join(bars)}
  {''.join(texts)}
</svg>
"""
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def build_line_chart_svg(title: str, labels: list[str], values: list[float], color: str = "#0EA5E9") -> str:
    """Genera un grafico de linea SVG listo para incrustar en el PDF."""
    if not labels or not values:
        return ""

    width = 860
    height = 280
    padding_top = 38
    padding_right = 20
    padding_bottom = 56
    padding_left = 46
    chart_w = width - padding_left - padding_right
    chart_h = height - padding_top - padding_bottom

    safe_values = [max(0.0, _to_number(v)) for v in values]
    max_v = max(safe_values) if safe_values else 1.0
    if max_v <= 0:
        max_v = 1.0

    n = len(labels)
    step_x = chart_w / max(n - 1, 1)

    points = []
    dots = []
    xlabels = []
    for i, (label, value) in enumerate(zip(labels, safe_values)):
        x = padding_left + i * step_x
        y = padding_top + chart_h - ((value / max_v) * chart_h)
        points.append(f"{x:.1f},{y:.1f}")
        dots.append(f"<circle cx='{x:.1f}' cy='{y:.1f}' r='3.4' fill='{color}' />")
        dots.append(f"<text x='{x:.1f}' y='{max(padding_top + 12, y - 8):.1f}' text-anchor='middle' font-size='10' fill='#111827'>{int(round(value))}</text>")
        if i % max(1, n // 8) == 0 or i == n - 1:
            xlabels.append(f"<text x='{x:.1f}' y='{padding_top + chart_h + 16:.1f}' text-anchor='middle' font-size='10' fill='#374151'>{html.escape(str(label)[5:] if len(str(label)) >= 10 else str(label))}</text>")

    grid = []
    for t in [0, 0.25, 0.5, 0.75, 1.0]:
        gy = padding_top + chart_h - (chart_h * t)
        gv = max_v * t
        grid.append(f"<line x1='{padding_left}' y1='{gy:.1f}' x2='{padding_left + chart_w}' y2='{gy:.1f}' stroke='#E5E7EB' stroke-width='1' />")
        grid.append(f"<text x='{padding_left - 6}' y='{gy + 4:.1f}' text-anchor='end' font-size='10' fill='#6B7280'>{int(round(gv))}</text>")

    svg = f"""
<svg viewBox='0 0 {width} {height}' width='100%' xmlns='http://www.w3.org/2000/svg'>
  <rect x='0' y='0' width='{width}' height='{height}' fill='#FFFFFF' rx='8' />
  <text x='{padding_left}' y='22' font-size='14' font-weight='700' fill='#111827'>{html.escape(title)}</text>
  {''.join(grid)}
  <polyline points='{' '.join(points)}' fill='none' stroke='{color}' stroke-width='2.8' />
  {''.join(dots)}
  {''.join(xlabels)}
</svg>
"""
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def build_gauge_svg(title: str, value: float, max_value: float = 100.0) -> str:
        """Genera un medidor circular SVG para cobertura o cumplimiento porcentual."""
        width = 420
        height = 240
        cx = width / 2
        cy = 130
        r = 82

        safe_max = max(1.0, _to_number(max_value, 100.0))
        safe_value = min(max(0.0, _to_number(value, 0.0)), safe_max)
        pct = safe_value / safe_max

        # Arco semicircular usando stroke-dasharray sobre circunferencia completa.
        circumference = 2 * 3.14159265359 * r
        half = circumference / 2
        progress = half * pct

        svg = f"""
<svg viewBox='0 0 {width} {height}' width='100%' xmlns='http://www.w3.org/2000/svg'>
    <rect x='0' y='0' width='{width}' height='{height}' fill='#FFFFFF' rx='8' />
    <text x='{cx}' y='26' text-anchor='middle' font-size='14' font-weight='700' fill='#111827'>{html.escape(title)}</text>
    <g transform='rotate(180 {cx} {cy})'>
        <circle cx='{cx}' cy='{cy}' r='{r}' fill='none' stroke='#E5E7EB' stroke-width='16' stroke-dasharray='{half} {circumference}' stroke-linecap='round' />
        <circle cx='{cx}' cy='{cy}' r='{r}' fill='none' stroke='#2563EB' stroke-width='16' stroke-dasharray='{progress} {circumference}' stroke-linecap='round' />
    </g>
    <text x='{cx}' y='{cy - 4}' text-anchor='middle' font-size='30' font-weight='800' fill='#111827'>{pct * 100:.1f}%</text>
    <text x='{cx}' y='{cy + 20}' text-anchor='middle' font-size='11' fill='#6B7280'>Cobertura estimada</text>
    <text x='{cx - r + 2}' y='{cy + 48}' text-anchor='start' font-size='10' fill='#6B7280'>0%</text>
    <text x='{cx + r - 2}' y='{cy + 48}' text-anchor='end' font-size='10' fill='#6B7280'>100%</text>
</svg>
"""
        encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
        return f"data:image/svg+xml;base64,{encoded}"


async def fetch_logo_data_uri() -> str:
    """Obtiene el logo institucional y lo codifica como data URI para incrustarlo en el PDF."""
    logo_urls = [
        "http://frontend/assets/logo-ucundinamarca.png",
        "http://localhost:3000/assets/logo-ucundinamarca.png",
    ]

    timeout = httpx.Timeout(10.0, connect=3.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        for logo_url in logo_urls:
            try:
                resp = await client.get(logo_url)
                if resp.status_code == 200 and resp.content:
                    mime = resp.headers.get("content-type", "image/png").split(";")[0]
                    encoded = base64.b64encode(resp.content).decode("ascii")
                    return f"data:{mime};base64,{encoded}"
            except Exception:
                continue

    return ""


async def fetch_data(programa: str | None, fecha_inicio: str | None, fecha_fin: str | None, auth_header: str = "") -> dict:
    """Obtiene datos desde el backend Laravel reenviando la autenticación del coordinador."""
    params = {}
    if programa:
        params["programa"] = programa
    if fecha_inicio:
        params["fecha_inicio"] = fecha_inicio
    if fecha_fin:
        params["fecha_fin"] = fecha_fin

    headers = {"Accept": "application/json"}
    if auth_header:
        headers["Authorization"] = auth_header

    async def fetch_json(client: httpx.AsyncClient, path: str, request_params: dict, request_headers: dict):
        resp = await client.get(f"{BACKEND_URL}{path}", params=request_params, headers=request_headers)
        if resp.status_code >= 400:
            body = resp.text[:300]
            raise HTTPException(
                status_code=resp.status_code,
                detail=f"Error backend en {path}: {body}",
            )
        return resp.json()

    timeout = httpx.Timeout(30.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        metrics = await fetch_json(client, "/dashboard/metrics", params, headers)
        by_prog = await fetch_json(client, "/dashboard/by-program", params, headers)
        trend = await fetch_json(client, "/dashboard/trend", params, headers)
        top_topics = await fetch_json(client, "/dashboard/top-topics", params, headers)
        practice_students = await fetch_json(client, "/dashboard/practice-students", params, headers)
        practice_competencies = await fetch_json(client, "/dashboard/practice-competencies", params, headers)
        level_progression = await fetch_json(client, "/dashboard/level-progression", params, headers)
        difficulty_dist = await fetch_json(client, "/dashboard/difficulty-distribution", params, headers)
        english_parts = await fetch_json(client, "/dashboard/english-parts", params, headers)
        response_time = await fetch_json(client, "/dashboard/response-time", params, headers)
        ratings = await fetch_json(client, "/dashboard/ratings-breakdown", params, headers)

    return {
        "metrics":    metrics,
        "by_program": by_prog,
        "trend":      trend,
        "top_topics": top_topics,
        "practice_students": practice_students,
        "practice_competencies": practice_competencies,
        "level_progression": level_progression,
        "difficulty_distribution": difficulty_dist,
        "english_parts": english_parts,
        "response_time": response_time,
        "ratings": ratings,
    }


@router.get("/excel")
async def export_excel(
    request: Request,
    programa: str | None = QueryParam(None),
    fecha_inicio: str | None = QueryParam(None),
    fecha_fin: str | None = QueryParam(None),
):
    """RF-20, RF-24: Genera reporte Excel con múltiples hojas."""
    try:
        auth_header = request.headers.get("authorization", "")
        data = await fetch_data(programa, fecha_inicio, fecha_fin, auth_header)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            workbook = writer.book

            # Hoja 1: Resumen / Métricas
            metrics = data["metrics"]
            df_resumen = pd.DataFrame([metrics])
            df_resumen.to_excel(writer, sheet_name="Resumen", index=False)

            # Hoja 2: Consultas por Programa
            df_prog = pd.DataFrame(data["by_program"])
            df_prog.to_excel(writer, sheet_name="Por Programa", index=False)

            # Hoja 3: Tendencia de Uso
            df_trend = pd.DataFrame(data["trend"])
            df_trend.to_excel(writer, sheet_name="Tendencia", index=False)

            # Hoja 4: Temas más consultados
            df_topics = pd.DataFrame(data["top_topics"])
            df_topics.to_excel(writer, sheet_name="Temas", index=False)

            # Hoja 5: Rendimiento de prácticas por estudiante
            df_practice_students = pd.DataFrame(data["practice_students"])
            df_practice_students.to_excel(writer, sheet_name="Practicas Estudiante", index=False)

            # Hoja 6: Rendimiento por competencia y programa
            df_practice_comp = pd.DataFrame(data["practice_competencies"])
            df_practice_comp.to_excel(writer, sheet_name="Practicas Competencia", index=False)

            # Hoja 7: Progresion de Nivel
            df_level = pd.DataFrame(data["level_progression"])
            if not df_level.empty:
                df_level.to_excel(writer, sheet_name="Progresion Nivel", index=False)

            # Hoja 8: Distribucion por Dificultad
            df_diff = pd.DataFrame(data["difficulty_distribution"])
            if not df_diff.empty:
                df_diff.to_excel(writer, sheet_name="Distribucion Dificultad", index=False)

            # Hoja 9: Ingles por Tipo (Parte 1-7)
            df_eng = pd.DataFrame(data["english_parts"])
            if not df_eng.empty:
                df_eng.to_excel(writer, sheet_name="Ingles por Tipo", index=False)

            # Hoja 10: Tiempo de Respuesta
            df_time = pd.DataFrame(data["response_time"])
            if not df_time.empty:
                df_time.to_excel(writer, sheet_name="Tiempo Respuesta", index=False)

            # Hoja 11: Calificaciones
            df_ratings = pd.DataFrame(data["ratings"])
            if not df_ratings.empty:
                df_ratings.to_excel(writer, sheet_name="Calificaciones", index=False)

        output.seek(0)
        filename = f"reporte_saberpro_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"

        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando Excel: {str(e)}")


@router.get("/pdf")
async def export_pdf(
    request: Request,
    programa: str | None = QueryParam(None),
    fecha_inicio: str | None = QueryParam(None),
    fecha_fin: str | None = QueryParam(None),
):
    """RF-21, RF-25: Genera reporte PDF con gráficos Plotly y WeasyPrint."""
    try:
        from weasyprint import HTML

        auth_header = request.headers.get("authorization", "")
        data = await fetch_data(programa, fecha_inicio, fecha_fin, auth_header)
        logo_data_uri = await fetch_logo_data_uri()

        # Tabla resumen: consultas por programa (estatica para compatibilidad PDF)
        by_prog = data["by_program"]
        by_prog_rows = "".join([
            f"<tr><td>{p.get('programa', 'N/A')}</td><td>{p.get('total', 0)}</td></tr>"
            for p in by_prog
        ])

        # Tabla resumen: tendencia de uso (estatica para compatibilidad PDF)
        trend = data["trend"]
        trend_rows = "".join([
            f"<tr><td>{t.get('fecha', 'N/A')}</td><td>{t.get('total', 0)}</td></tr>"
            for t in trend
        ])

        # Tabla de temas
        topics_rows = "".join([
            f"<tr><td>{t.get('competencia', 'N/A')}</td><td>{t.get('programa', 'N/A')}</td><td>{t.get('total', 0)}</td></tr>"
            for t in data["top_topics"]
        ])

        # Tabla de practicas por estudiante (top 30)
        practice_students = data["practice_students"][:30]
        practice_students_rows = "".join([
            (
                f"<tr><td>{s.get('estudiante', 'N/A')}</td>"
                f"<td>{s.get('programa', 'N/A')}</td>"
                f"<td>{s.get('intentos', 0)}</td>"
                f"<td>{s.get('aciertos', 0)}</td>"
                f"<td>{s.get('puntaje_promedio', 0)}%</td></tr>"
            )
            for s in practice_students
        ])

        # Tabla de practicas por competencia/programa (top 40)
        practice_comp = data["practice_competencies"][:40]
        practice_comp_rows = "".join([
            (
                f"<tr><td>{c.get('programa', 'N/A')}</td>"
                f"<td>{c.get('competencia', 'N/A')}</td>"
                f"<td>{c.get('intentos', 0)}</td>"
                f"<td>{c.get('aciertos', 0)}</td>"
                f"<td>{c.get('promedio_competencia', 0)}%</td></tr>"
            )
            for c in practice_comp
        ])

        metrics = data["metrics"]
        titulo_filtro = f" — Programa: {programa}" if programa else ""
        fecha_gen = datetime.now().strftime("%d/%m/%Y %H:%M")
        rango_fechas = f"Rango: {fecha_inicio or 'Inicio'} a {fecha_fin or 'Hoy'}"
        logo_html = (
            f"<img src='{logo_data_uri}' alt='Logo Universidad de Cundinamarca' class='logo' />"
            if logo_data_uri else ""
        )

        if not by_prog_rows:
            by_prog_rows = "<tr><td colspan='2'>Sin datos para el filtro seleccionado.</td></tr>"
        if not trend_rows:
            trend_rows = "<tr><td colspan='2'>Sin datos para el filtro seleccionado.</td></tr>"
        if not topics_rows:
            topics_rows = "<tr><td colspan='3'>Sin datos para el filtro seleccionado.</td></tr>"
        if not practice_students_rows:
            practice_students_rows = "<tr><td colspan='5'>No hay registros de prácticas para el filtro seleccionado.</td></tr>"
        if not practice_comp_rows:
            practice_comp_rows = "<tr><td colspan='5'>No hay registros de practicas para el filtro seleccionado.</td></tr>"

        # Tabla de progresion de nivel
        level_prog = data["level_progression"]
        level_prog_rows = "".join([
            (
                f"<tr><td>{r.get('fecha', 'N/A')}</td>"
                f"<td>{r.get('competencia', 'N/A')}</td>"
                f"<td>{r.get('intentos', 0)}</td>"
                f"<td>{r.get('aciertos', 0)}</td>"
                f"<td>{_to_number(r.get('tasa_acierto', 0)):.1f}%</td>"
                f"<td>{_to_number(r.get('nivel_promedio', 0)):.1f}</td></tr>"
            )
            for r in level_prog
        ])
        if not level_prog_rows:
            level_prog_rows = "<tr><td colspan='6'>No hay datos de progresion para el filtro seleccionado.</td></tr>"

        by_prog_top = by_prog[:8]
        bar_labels = [str(p.get("programa", "N/A")) for p in by_prog_top]
        bar_values = [_to_number(p.get("total", 0)) for p in by_prog_top]
        by_program_chart = build_bar_chart_svg("Consultas por programa (Top 8)", bar_labels, bar_values)

        trend_tail = trend[-14:] if len(trend) > 14 else trend
        trend_labels = [str(t.get("fecha", "")) for t in trend_tail]
        trend_values = [_to_number(t.get("total", 0)) for t in trend_tail]
        trend_chart = build_line_chart_svg("Tendencia diaria de consultas", trend_labels, trend_values)

        comp_top = sorted(
            data["practice_competencies"],
            key=lambda c: _to_number(c.get("promedio_competencia", 0)),
            reverse=True,
        )[:10]
        comp_labels = [f"{c.get('programa', 'N/A')} - {c.get('competencia', 'N/A')}" for c in comp_top]
        comp_values = [_to_number(c.get("promedio_competencia", 0)) for c in comp_top]
        practice_chart = build_bar_chart_svg("Promedio de practica por competencia (Top 10)", comp_labels, comp_values, color="#059669")

        by_program_chart_html = f"<img src='{by_program_chart}' class='chart-image' alt='Grafica de consultas por programa' />" if by_program_chart else ""
        trend_chart_html = f"<img src='{trend_chart}' class='chart-image' alt='Grafica de tendencia de uso' />" if trend_chart else ""
        practice_chart_html = f"<img src='{practice_chart}' class='chart-image' alt='Grafica de desempeno en practicas' />" if practice_chart else ""

        total_students = _to_number(metrics.get("total_estudiantes", 0), 0)
        unique_students = _to_number(metrics.get("estudiantes_unicos", 0), 0)
        adoption_ratio = (unique_students / total_students) if total_students > 0 else 0.0
        adoption_gauge = build_gauge_svg("Cobertura de adopcion estudiantil", adoption_ratio * 100, 100)
        adoption_gauge_html = f"<img src='{adoption_gauge}' class='chart-image compact' alt='Medidor de cobertura de adopcion' />" if adoption_gauge else ""

        ranking_students = sorted(
            data["practice_students"],
            key=lambda s: (_to_number(s.get("puntaje_promedio", 0)), _to_number(s.get("intentos", 0))),
            reverse=True,
        )[:12]
        ranking_labels = [str(s.get("estudiante", "N/A")) for s in ranking_students]
        ranking_values = [_to_number(s.get("puntaje_promedio", 0)) for s in ranking_students]
        ranking_chart = build_bar_chart_svg("Ranking de estudiantes por puntaje de practica", ranking_labels, ranking_values, color="#7C3AED")
        ranking_chart_html = f"<img src='{ranking_chart}' class='chart-image' alt='Ranking de estudiantes por puntaje' />" if ranking_chart else ""

        interpretacion_general = (
            "Este informe resume el uso del asistente y el desempeno en practicas academicas. "
            "Use los indicadores generales para identificar volumen de actividad y satisfaccion, "
            "luego contraste los resultados por programa, tendencia temporal y competencias para detectar brechas concretas."
        )

        html_template = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<style>
  body {{ font-family: Arial, sans-serif; margin: 40px; color: #1f2937; }}
    .header {{ display: flex; align-items: center; justify-content: space-between; gap: 16px; }}
    .logo {{ height: 64px; width: auto; object-fit: contain; }}
    .header-meta {{ text-align: right; color: #6B7280; font-size: 12px; }}
  h1 {{ color: #4F46E5; font-size: 22px; }}
  h2 {{ color: #374151; font-size: 16px; margin-top: 24px; }}
  .metrics {{ display: flex; gap: 16px; margin: 16px 0; }}
  .metric-card {{ background: #F3F4F6; border-radius: 8px; padding: 16px; text-align: center; flex: 1; }}
  .metric-value {{ font-size: 28px; font-weight: bold; color: #4F46E5; }}
  .metric-label {{ font-size: 12px; color: #6B7280; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
  th {{ background: #4F46E5; color: white; padding: 8px; text-align: left; }}
  td {{ padding: 6px 8px; border-bottom: 1px solid #E5E7EB; font-size: 13px; }}
  .footer {{ margin-top: 40px; font-size: 11px; color: #9CA3AF; }}
    .explain {{ font-size: 12px; color: #4B5563; margin: 8px 0 12px; line-height: 1.45; }}
    .guide {{ margin: 8px 0 14px 18px; color: #374151; font-size: 12px; line-height: 1.45; }}
    .guide li {{ margin-bottom: 4px; }}
    .chart-image {{ width: 100%; margin: 8px 0 14px; border: 1px solid #E5E7EB; border-radius: 8px; }}
    .chart-image.compact {{ max-width: 500px; display: block; margin-left: auto; margin-right: auto; }}
</style>
</head>
<body>
<div class="header">
    <div>
        <h1>Informe de Uso — Asistente Saber Pro{titulo_filtro}</h1>
        <p style="color:#6B7280; font-size:12px;">Universidad de Cundinamarca, Sede Fusagasugá</p>
    </div>
    <div class="header-meta">
        {logo_html}
        <div>Generado el {fecha_gen}</div>
        <div>{rango_fechas}</div>
    </div>
</div>

<h2>Como leer este informe</h2>
<p class="explain">{interpretacion_general}</p>
<ul class="guide">
    <li>Un mayor volumen de consultas indica mayor adopcion del asistente.</li>
    <li>Un porcentaje bajo de calificaciones positivas sugiere revisar calidad de respuestas o cobertura de contenidos.</li>
    <li>Las diferencias por programa y competencia permiten priorizar intervenciones academicas focalizadas.</li>
</ul>

<h2>Indicadores Generales</h2>
<p class="explain">Este bloque muestra el panorama global del periodo filtrado. Sirve para evaluar uso, alcance y percepcion de valor del asistente.</p>
<div class="metrics">
  <div class="metric-card">
    <div class="metric-value">{metrics.get('total_consultas', 0)}</div>
    <div class="metric-label">Total Consultas</div>
  </div>
  <div class="metric-card">
    <div class="metric-value">{metrics.get('estudiantes_unicos', 0)}</div>
    <div class="metric-label">Estudiantes Únicos</div>
  </div>
  <div class="metric-card">
    <div class="metric-value">{metrics.get('consultas_hoy', 0)}</div>
    <div class="metric-label">Consultas Hoy</div>
  </div>
  <div class="metric-card">
    <div class="metric-value">{metrics.get('promedio_positivas', '0%')}</div>
    <div class="metric-label">Calificaciones Positivas</div>
  </div>
    <div class="metric-card">
        <div class="metric-value">{metrics.get('total_estudiantes', 0)}</div>
        <div class="metric-label">Total Estudiantes</div>
    </div>
</div>

<ul class="guide">
    <li><strong>Total Consultas:</strong> nivel de interaccion total con la plataforma.</li>
    <li><strong>Estudiantes Unicos:</strong> alcance real de uso en la poblacion.</li>
    <li><strong>Consultas Hoy:</strong> pulso operativo reciente y estacionalidad.</li>
    <li><strong>Calificaciones Positivas:</strong> aproximacion a satisfaccion de respuesta.</li>
    <li><strong>Total Estudiantes:</strong> base institucional para comparar cobertura de adopcion.</li>
</ul>

<h2>Cobertura de Adopcion</h2>
<p class="explain">Este medidor muestra el porcentaje de estudiantes unicos que han utilizado el asistente sobre el total de estudiantes registrados en el periodo seleccionado.</p>
{adoption_gauge_html}

<h2>Ranking de Estudiantes en Practicas</h2>
<p class="explain">Visualiza los estudiantes con mejor puntaje promedio en practicas. Sirve para identificar referentes y tambien para contrastar con estudiantes de bajo desempeno en las tablas detalladas.</p>
{ranking_chart_html}

<h2>Consultas por Programa</h2>
<p class="explain">Permite comparar la carga de uso entre programas. Si un programa tiene baja participacion relativa, puede requerir mayor socializacion o acompanamiento docente.</p>
{by_program_chart_html}
<table>
    <tr><th>Programa</th><th>Total Consultas</th></tr>
    {by_prog_rows}
</table>

<h2>Tendencia de Uso</h2>
<p class="explain">Muestra la evolucion temporal de consultas. Picos pueden asociarse a cortes academicos, evaluaciones o campanas institucionales.</p>
{trend_chart_html}
<table>
    <tr><th>Fecha</th><th>Total</th></tr>
    {trend_rows}
</table>

<h2>Temas más Consultados</h2>
<p class="explain">Identifica competencias y programas con mayor demanda. Use esta tabla para priorizar contenidos de refuerzo y bancos de preguntas.</p>
<table>
  <tr><th>Competencia</th><th>Programa</th><th>Total Consultas</th></tr>
  {topics_rows}
</table>

<h2>Rendimiento en Prácticas por Estudiante</h2>
<p class="explain">Resume resultados individuales en actividades de practica. Es util para detectar estudiantes con alto volumen pero bajo acierto, donde conviene refuerzo personalizado.</p>
<table>
    <tr><th>Estudiante</th><th>Programa</th><th>Intentos</th><th>Aciertos</th><th>Puntaje Promedio</th></tr>
    {practice_students_rows}
</table>

<h2>Rendimiento en Prácticas por Competencia y Programa</h2>
<p class="explain">Compara el desempeno agregado por competencia dentro de cada programa. Un promedio bajo indica necesidad de ajuste curricular o actividades de preparacion especificas.</p>
{practice_chart_html}
<table>
    <tr><th>Programa</th><th>Competencia</th><th>Intentos</th><th>Aciertos</th><th>Promedio</th></tr>
    {practice_comp_rows}
</table>

<h2>Progresion de Nivel por Competencia</h2>
<p class="explain">Evolucion del nivel promedio a lo largo del tiempo. Basico=1, Intermedio=2, Avanzado=3 (A2=2, B1=3 para Ingles). Una tendencia ascendente indica mejora en el desempeno.</p>
<table>
    <tr><th>Fecha</th><th>Competencia</th><th>Intentos</th><th>Aciertos</th><th>Tasa Acierto</th><th>Nivel Promedio</th></tr>
    {level_prog_rows}
</table>

<h2>Recomendaciones de interpretacion</h2>
<ul class="guide">
    <li>Priorice competencias con menor promedio y mayor numero de intentos: ahi hay impacto inmediato.</li>
    <li>Combine cobertura (estudiantes unicos) con satisfaccion (calificaciones positivas) para medir calidad de adopcion.</li>
    <li>Evalua tendencias por periodos comparables para evitar conclusiones por variaciones puntuales.</li>
</ul>

<div class="footer">
  Documento generado automáticamente por el Sistema de Asistencia Académica Saber Pro.<br>
  Universidad de Cundinamarca · Confidencial · Uso interno.
</div>
</body>
</html>"""

        pdf_bytes = HTML(string=html_template).write_pdf()
        filename = f"reporte_saberpro_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"

        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando PDF: {repr(e)}")
