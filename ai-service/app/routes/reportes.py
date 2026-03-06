"""
RF-20, RF-21, RF-24, RF-25: Endpoints de generación de reportes.
GET /reportes/excel → archivo Excel con resumen, detalle, tendencia y temas.
GET /reportes/pdf   → informe PDF institucional con gráficos Plotly.
"""

import io
import httpx
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from fastapi import APIRouter, Query as QueryParam, HTTPException
from fastapi.responses import StreamingResponse
from jinja2 import Environment, BaseLoader

router = APIRouter()

BACKEND_URL = "http://backend/api"


async def fetch_data(programa: str | None, fecha_inicio: str | None, fecha_fin: str | None) -> dict:
    """Obtiene datos desde el backend Laravel."""
    params = {}
    if programa:
        params["programa"] = programa
    if fecha_inicio:
        params["fecha_inicio"] = fecha_inicio
    if fecha_fin:
        params["fecha_fin"] = fecha_fin

    # Nota: en producción se debe incluir header de autenticación interna
    async with httpx.AsyncClient(timeout=10) as client:
        metrics   = (await client.get(f"{BACKEND_URL}/dashboard/metrics", params=params)).json()
        by_prog   = (await client.get(f"{BACKEND_URL}/dashboard/by-program", params=params)).json()
        trend     = (await client.get(f"{BACKEND_URL}/dashboard/trend", params=params)).json()
        top_topics= (await client.get(f"{BACKEND_URL}/dashboard/top-topics", params=params)).json()

    return {
        "metrics":    metrics,
        "by_program": by_prog,
        "trend":      trend,
        "top_topics": top_topics,
    }


@router.get("/excel")
async def export_excel(
    programa: str | None = QueryParam(None),
    fecha_inicio: str | None = QueryParam(None),
    fecha_fin: str | None = QueryParam(None),
):
    """RF-20, RF-24: Genera reporte Excel con múltiples hojas."""
    try:
        data = await fetch_data(programa, fecha_inicio, fecha_fin)

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

        output.seek(0)
        filename = f"reporte_saberpro_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"

        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando Excel: {str(e)}")


@router.get("/pdf")
async def export_pdf(
    programa: str | None = QueryParam(None),
    fecha_inicio: str | None = QueryParam(None),
    fecha_fin: str | None = QueryParam(None),
):
    """RF-21, RF-25: Genera reporte PDF con gráficos Plotly y WeasyPrint."""
    try:
        from weasyprint import HTML

        data = await fetch_data(programa, fecha_inicio, fecha_fin)

        # Gráfico de barras: consultas por programa
        by_prog = data["by_program"]
        fig_bar = go.Figure(go.Bar(
            x=[p["programa"] for p in by_prog],
            y=[p["total"] for p in by_prog],
            marker_color="#4F46E5",
        ))
        fig_bar.update_layout(title="Consultas por Programa", height=350)
        chart_bar = fig_bar.to_html(full_html=False, include_plotlyjs="cdn")

        # Gráfico de líneas: tendencia
        trend = data["trend"]
        fig_line = go.Figure(go.Scatter(
            x=[t["fecha"] for t in trend],
            y=[t["total"] for t in trend],
            mode="lines+markers",
            line=dict(color="#10B981"),
        ))
        fig_line.update_layout(title="Tendencia de Uso", height=300)
        chart_line = fig_line.to_html(full_html=False, include_plotlyjs=False)

        # Tabla de temas
        topics_rows = "".join([
            f"<tr><td>{t['competencia']}</td><td>{t['programa']}</td><td>{t['total']}</td></tr>"
            for t in data["top_topics"]
        ])

        metrics = data["metrics"]
        titulo_filtro = f" — Programa: {programa}" if programa else ""
        fecha_gen = datetime.now().strftime("%d/%m/%Y %H:%M")

        html_template = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<style>
  body {{ font-family: Arial, sans-serif; margin: 40px; color: #1f2937; }}
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
</style>
</head>
<body>
<h1>Informe de Uso — Asistente Saber Pro{titulo_filtro}</h1>
<p style="color:#6B7280; font-size:12px;">Universidad de Cundinamarca, Sede Fusagasugá · Generado el {fecha_gen}</p>

<h2>Indicadores Generales</h2>
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
</div>

<h2>Consultas por Programa</h2>
{chart_bar}

<h2>Tendencia de Uso</h2>
{chart_line}

<h2>Temas más Consultados</h2>
<table>
  <tr><th>Competencia</th><th>Programa</th><th>Total Consultas</th></tr>
  {topics_rows}
</table>

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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando PDF: {str(e)}")
