<?php

namespace App\Http\Controllers;

use App\Models\Query;
use App\Models\Student;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;

class DashboardController extends Controller
{
    /**
     * RF-15: Indicadores generales del dashboard del coordinador.
     */
    public function metrics(Request $request)
    {
        $programa = $request->get('programa');
        $fechaInicio = $request->get('fecha_inicio');
        $fechaFin = $request->get('fecha_fin');

        $q = Query::query();

        if ($programa)
            $q->where('programa', $programa);
        if ($fechaInicio)
            $q->whereDate('created_at', '>=', $fechaInicio);
        if ($fechaFin)
            $q->whereDate('created_at', '<=', $fechaFin);

        $totalConsultas = (clone $q)->count();
        $estudiantesUnicos = (clone $q)->distinct('student_hash')->count('student_hash');
        $consultasHoy = (clone $q)->whereDate('created_at', today())->count();
        $promedioPositivas = (clone $q)->whereNotNull('calificacion')
            ->avg(DB::raw('CASE WHEN calificacion = true THEN 1 ELSE 0 END'));

        return response()->json([
            'total_consultas' => $totalConsultas,
            'estudiantes_unicos' => $estudiantesUnicos,
            'consultas_hoy' => $consultasHoy,
            'promedio_positivas' => round($promedioPositivas * 100, 1) . '%',
            'total_estudiantes' => Student::count(),
        ]);
    }

    /**
     * RF-16: Distribución de consultas por programa (gráfico de barras).
     */
    public function byProgram(Request $request)
    {
        $q = $this->applyFilters(Query::query(), $request);

        $data = $q->select('programa', DB::raw('count(*) as total'))
            ->groupBy('programa')
            ->orderByDesc('total')
            ->get();

        return response()->json($data);
    }

    /**
     * RF-17: Tendencia de uso diaria o semanal (gráfico de líneas).
     */
    public function trend(Request $request)
    {
        $q = $this->applyFilters(Query::query(), $request);

        $data = $q
            ->selectRaw("DATE(created_at) as fecha, COUNT(*) as total")
            ->groupByRaw("DATE(created_at)")
            ->orderByRaw("DATE(created_at)")
            ->get();

        return response()->json($data);
    }

    /**
     * RF-19: Tabla de temas más consultados (por competencia).
     */
    public function topTopics(Request $request)
    {
        $q = $this->applyFilters(Query::query(), $request);

        $data = $q->whereNotNull('competencia')
            ->select('competencia', 'programa', DB::raw('count(*) as total'))
            ->groupBy('competencia', 'programa')
            ->orderByDesc('total')
            ->limit(20)
            ->get();

        return response()->json($data);
    }

    /**
     * Helper: aplica filtros de programa y rango de fechas — RF-18
     */
    private function applyFilters($query, Request $request)
    {
        if ($request->has('programa') && $request->programa) {
            $query->where('programa', $request->programa);
        }
        if ($request->has('fecha_inicio') && $request->fecha_inicio) {
            $query->whereDate('created_at', '>=', $request->fecha_inicio);
        }
        if ($request->has('fecha_fin') && $request->fecha_fin) {
            $query->whereDate('created_at', '<=', $request->fecha_fin);
        }
        return $query;
    }
}
