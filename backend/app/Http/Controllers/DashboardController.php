<?php

namespace App\Http\Controllers;

use App\Models\Query;
use App\Models\Student;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;

class DashboardController extends Controller
{
    /**
     * Programas disponibles para filtros de analitica, normalizados.
     */
    public function programs()
    {
        $rawPrograms = Query::query()
            ->whereNotNull('programa')
            ->pluck('programa')
            ->all();

        $bucket = [];
        foreach ($rawPrograms as $value) {
            $normalized = $this->normalizeProgramValue((string) $value);
            if ($normalized === '') {
                continue;
            }

            $key = function_exists('mb_strtolower')
                ? mb_strtolower($normalized, 'UTF-8')
                : strtolower($normalized);
            if (!isset($bucket[$key])) {
                $bucket[$key] = $normalized;
            }
        }

        $programs = array_values($bucket);
        natcasesort($programs);

        return response()->json(array_values($programs));
    }

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
     * Analitica de practica por estudiante y programa.
     */
    public function practiceStudents(Request $request)
    {
        $q = $this->applyFilters(Query::query(), $request)
            ->where('es_practica', true)
            ->whereNotNull('acierto');

        $q = $this->excludeCoordinatorRecords($q);

        $rows = $q->join('students', 'queries.student_id', '=', 'students.id')
            ->select(
            'queries.programa',
            DB::raw("COALESCE(NULLIF(queries.student_nombre, ''), CONCAT('Estudiante ', SUBSTRING(queries.student_hash, 1, 8))) as estudiante"),
            'queries.student_hash',
            'students.cedula',
            'students.email',
            DB::raw('COUNT(*) as intentos'),
            DB::raw('SUM(CASE WHEN queries.acierto = true THEN 1 ELSE 0 END) as aciertos'),
            DB::raw('ROUND(AVG(CASE WHEN queries.acierto = true THEN 1 ELSE 0 END) * 100, 1) as puntaje_promedio')
        )
            ->groupBy('queries.programa', 'queries.student_hash', 'queries.student_nombre', 'students.cedula', 'students.email')
            ->orderByDesc('puntaje_promedio')
            ->limit(200)
            ->get();

        return response()->json($rows);
    }

    /**
     * Promedio de calificacion por competencia y programa para comparativas.
     */
    public function practiceCompetencies(Request $request)
    {
        $q = $this->applyFilters(Query::query(), $request)
            ->where('es_practica', true)
            ->whereNotNull('acierto')
            ->whereNotNull('competencia');

        $rows = $q->select(
            'programa',
            'competencia',
            DB::raw('COUNT(*) as intentos'),
            DB::raw('SUM(CASE WHEN acierto = true THEN 1 ELSE 0 END) as aciertos'),
            DB::raw('ROUND(AVG(CASE WHEN acierto = true THEN 1 ELSE 0 END) * 100, 1) as promedio_competencia')
        )
            ->groupBy('programa', 'competencia')
            ->orderBy('programa')
            ->orderByDesc('promedio_competencia')
            ->get();

        return response()->json($rows);
    }

    /**
     * Evolucion de nivel por competencia en el tiempo para seguimiento adaptativo.
     */
    public function levelProgression(Request $request)
    {
        $q = $this->applyFilters(Query::query(), $request)
            ->where('es_practica', true)
            ->where(function ($sub) {
                $sub->whereNotNull('nivel_pregunta')
                    ->orWhereNotNull('acierto');
            })
            ->whereNotNull('competencia');

        $rows = $q->selectRaw("\n            DATE(created_at) as fecha,\n            competencia,\n            COUNT(*) as intentos,\n            SUM(CASE WHEN acierto = true THEN 1 ELSE 0 END) as aciertos,\n            ROUND(AVG(CASE WHEN acierto = true THEN 1 ELSE 0 END) * 100, 1) as tasa_acierto,\n            ROUND(AVG(\n                CASE\n                    WHEN LOWER(nivel_pregunta) = 'basico' THEN 1\n                    WHEN LOWER(nivel_pregunta) IN ('intermedio', 'a2') THEN 2\n                    WHEN LOWER(nivel_pregunta) IN ('avanzado', 'b1') THEN 3\n                    WHEN nivel_pregunta IS NULL AND (LOWER(competencia) LIKE '%ingles%' OR LOWER(competencia) LIKE '%inglés%' OR LOWER(competencia) LIKE '%english%') THEN CASE WHEN acierto = true THEN 3 ELSE 2 END\n                    WHEN nivel_pregunta IS NULL THEN CASE WHEN acierto = true THEN 2 ELSE 1 END\n                    ELSE NULL\n                END\n            ), 2) as nivel_promedio\n        ")
            ->groupByRaw('DATE(created_at), competencia')
            ->orderByRaw('DATE(created_at)')
            ->orderBy('competencia')
            ->get();

        return response()->json($rows);
    }

    /**
     * Distribucion por nivel de dificultad (basico/intermedio/avanzado) por competencia.
     */
    public function difficultyDistribution(Request $request)
    {
        $q = Query::query()->where('es_practica', true);
        $q = $this->applyFilters($q, $request);

        $rows = $q->select(
                'competencia',
                'nivel_pregunta',
                DB::raw('COUNT(*) as total'),
                DB::raw('ROUND(AVG(CASE WHEN acierto THEN 1.0 ELSE 0.0 END) * 100, 1) as tasa_acierto')
            )
            ->whereNotNull('nivel_pregunta')
            ->groupBy('competencia', 'nivel_pregunta')
            ->orderBy('competencia')
            ->orderBy('nivel_pregunta')
            ->get();

        return response()->json($rows);
    }

    /**
     * Desglose de Ingles por tipo de pregunta (part1 a part7).
     */
    public function englishParts(Request $request)
    {
        $q = Query::query()->where('es_practica', true)->whereRaw("LOWER(competencia) LIKE '%ingl%'");
        $q = $this->applyFilters($q, $request);

        $rows = $q->select(
                'tipo_pregunta',
                DB::raw('COUNT(*) as total'),
                DB::raw('COUNT(DISTINCT student_id) as estudiantes'),
                DB::raw('ROUND(AVG(CASE WHEN acierto THEN 1.0 ELSE 0.0 END) * 100, 1) as tasa_acierto'),
                DB::raw('ROUND(AVG(tiempo_respuesta_ms) / 1000, 1) as tiempo_promedio_seg')
            )
            ->whereNotNull('tipo_pregunta')
            ->groupBy('tipo_pregunta')
            ->orderBy('tipo_pregunta')
            ->get();

        return response()->json($rows);
    }

    /**
     * Tiempo de respuesta promedio por competencia.
     */
    public function responseTime(Request $request)
    {
        $q = Query::query()->where('es_practica', true);
        $q = $this->applyFilters($q, $request);

        $rows = $q->select(
                'competencia',
                DB::raw('ROUND(AVG(tiempo_respuesta_ms) / 1000, 1) as tiempo_promedio_seg'),
                DB::raw('ROUND(AVG(CASE WHEN acierto THEN tiempo_respuesta_ms ELSE NULL END) / 1000, 1) as tiempo_acierto_seg'),
                DB::raw('ROUND(AVG(CASE WHEN NOT acierto THEN tiempo_respuesta_ms ELSE NULL END) / 1000, 1) as tiempo_error_seg'),
                DB::raw('COUNT(*) as total')
            )
            ->where('tiempo_respuesta_ms', '>', 0)
            ->groupBy('competencia')
            ->orderBy('tiempo_promedio_seg', 'desc')
            ->get();

        return response()->json($rows);
    }

    /**
     * Calificaciones positivas por competencia y programa.
     */
    public function ratingsBreakdown(Request $request)
    {
        $q = Query::query();
        $q = $this->applyFilters($q, $request);

        $rows = $q->select(
                'competencia',
                'programa',
                DB::raw('COUNT(*) as total'),
                DB::raw('SUM(CASE WHEN calificacion THEN 1 ELSE 0 END) as positivas'),
                DB::raw('ROUND(AVG(CASE WHEN calificacion THEN 1.0 ELSE 0.0 END) * 100, 1) as porcentaje')
            )
            ->whereNotNull('calificacion')
            ->groupBy('competencia', 'programa')
            ->orderBy('porcentaje', 'desc')
            ->get();

        return response()->json($rows);
    }

    /**
     * Helper: aplica filtros de programa y rango de fechas — RF-18
     */
    private function applyFilters($query, Request $request)
    {
        if ($request->has('programa') && $request->programa) {
            $programa = $this->normalizeProgramValue((string) $request->programa);
            $query->whereRaw(
                "LOWER(REGEXP_REPLACE(TRIM(programa), '\\s+', ' ', 'g')) = LOWER(?)",
                [$programa]
            );
        }
        if ($request->has('fecha_inicio') && $request->fecha_inicio) {
            $query->whereDate('created_at', '>=', $request->fecha_inicio);
        }
        if ($request->has('fecha_fin') && $request->fecha_fin) {
            $query->whereDate('created_at', '<=', $request->fecha_fin);
        }
        return $query;
    }

    private function normalizeProgramValue(string $value): string
    {
        $trimmed = trim($value);
        if ($trimmed === '') {
            return '';
        }

        return preg_replace('/\s+/u', ' ', $trimmed) ?? $trimmed;
    }

    /**
     * Excluye registros de coordinación en métricas de estudiantes.
     */
    private function excludeCoordinatorRecords($query)
    {
        return $query->where(function ($sub) {
            $sub->whereNull('student_nombre')
                ->orWhere(function ($byName) {
                    $byName->whereRaw("LOWER(student_nombre) NOT LIKE '%coordinador%'")
                        ->whereRaw("LOWER(student_nombre) NOT LIKE '%coordinator%'");
                });
        });
    }
}
