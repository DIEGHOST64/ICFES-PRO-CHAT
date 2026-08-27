<?php

namespace App\Http\Controllers;

use App\Models\Query;
use App\Models\Student;
use App\Models\StudentLoginEvent;
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
     * Actividad de estudiantes: ingresos y sesiones por rafagas.
     */
    public function activity(Request $request)
    {
        $minGap = 30; // minutos de inactividad para considerar una sesion nueva

        // 1. Ingresos desde la tabla de eventos de login
        $ingresosTotal = StudentLoginEvent::count();
        $ingresosHoy = StudentLoginEvent::whereDate('created_at', today())->count();
        $ingresos7d = StudentLoginEvent::where('created_at', '>=', now()->subDays(7))->count();

        $loginSeries = StudentLoginEvent::select(
                DB::raw('DATE(created_at) as fecha'),
                DB::raw('COUNT(*) as ingresos'),
                DB::raw('COUNT(DISTINCT student_hash) as estudiantes')
            )
            ->where('created_at', '>=', now()->subDays(30))
            ->groupBy(DB::raw('DATE(created_at)'))
            ->orderBy('fecha')
            ->get()
            ->keyBy('fecha');

        // 2. Sesiones por rafagas de actividad sobre las consultas
        $rows = Query::select('student_hash', 'created_at')
            ->where('created_at', '>=', now()->subDays(30))
            ->orderBy('student_hash')
            ->orderBy('created_at')
            ->get();

        $porEstudiante = [];
        foreach ($rows as $r) {
            if (!$r->student_hash) {
                continue;
            }
            $porEstudiante[$r->student_hash][] = $r->created_at;
        }

        $series = [];
        $porEstudianteResumen = [];
        $diasActivos = [];
        $totalHoras = 0.0;
        $totalSesiones = 0;
        $totalHoras7d = 0.0;

        $hashToStudent = [];
        foreach (Student::all() as $s) {
            $hashToStudent[hash('sha256', 'icfes_salt_' . $s->id)] = [
                'nombre' => $s->nombre,
                'cedula' => $s->cedula,
                'programa' => $s->programa,
            ];
        }

        $ingresosPorHash = StudentLoginEvent::selectRaw('student_hash, COUNT(*) as n')
            ->whereNotNull('student_hash')
            ->groupBy('student_hash')
            ->pluck('n', 'student_hash');

        foreach ($porEstudiante as $hash => $times) {
            $prev = null;
            $sStart = null;
            $sLast = null;
            $sesiones = 0;
            $horas = 0.0;
            $porDia = [];

            foreach ($times as $t) {
                if ($prev === null || $t->diffInMinutes($prev, true) > $minGap) {
                    if ($sStart !== null) {
                        $horas += $sLast->diffInMinutes($sStart, true) / 60.0;
                        $dia = $sLast->format('Y-m-d');
                        $porDia[$dia] = ($porDia[$dia] ?? 0) + $sLast->diffInMinutes($sStart, true) / 60.0;
                    }
                    $sStart = $t;
                    $sesiones++;
                }
                $sLast = $t;
                $prev = $t;
            }
            if ($sStart !== null) {
                $horas += $sLast->diffInMinutes($sStart, true) / 60.0;
                $dia = $sLast->format('Y-m-d');
                $porDia[$dia] = ($porDia[$dia] ?? 0) + $sLast->diffInMinutes($sStart, true) / 60.0;
            }

            $totalHoras += $horas;
            $totalSesiones += $sesiones;

            foreach ($times as $t) {
                $diasActivos[$t->format('Y-m-d')] = true;
            }

            $st = $hashToStudent[$hash] ?? null;
            $porEstudianteResumen[] = [
                'student_hash' => substr($hash, 0, 12),
                'nombre' => $st['nombre'] ?? 'Estudiante sin registro',
                'cedula' => $st['cedula'] ?? '',
                'programa' => $st['programa'] ?? '',
                'sesiones' => $sesiones,
                'horas_totales' => round($horas, 2),
                'ingresos' => (int) ($ingresosPorHash[$hash] ?? 0),
            ];

            foreach ($porDia as $dia => $h) {
                $series[$dia]['horas_activas'] = round(($series[$dia]['horas_activas'] ?? 0) + $h, 2);
                $series[$dia]['sesiones'] = ($series[$dia]['sesiones'] ?? 0) + 1;
            }
        }

        usort($porEstudianteResumen, fn ($a, $b) => $b['horas_totales'] <=> $a['horas_totales']);

        // Serie diaria: desde el despliegue del software (2026-08-18), sin dias
        // vacios previos. Si aun no hay actividad, cae a los ultimos 30 dias.
        $primeraActividad = Query::min('created_at');
        $primerLogin = StudentLoginEvent::min('created_at');
        $inicioActividad = null;
        if ($primeraActividad && $primerLogin) {
            $inicioActividad = $primeraActividad < $primerLogin ? $primeraActividad : $primerLogin;
        } else {
            $inicioActividad = $primeraActividad ?? $primerLogin;
        }
        $fechaDespliegue = \Illuminate\Support\Carbon::parse('2026-08-18')->startOfDay();
        $inicioSerie = $inicioActividad
            ? max(\Illuminate\Support\Carbon::parse($inicioActividad)->startOfDay(), $fechaDespliegue)
            : now()->subDays(30)->startOfDay();
        $totalDias = max(now()->startOfDay()->diffInDays($inicioSerie, true) + 1, 1);

        $salida = [];
        for ($i = $totalDias - 1; $i >= 0; $i--) {
            $fecha = now()->subDays($i)->format('Y-m-d');
            $horas = $series[$fecha]['horas_activas'] ?? 0;
            if ($i < 7) {
                $totalHoras7d += $horas;
            }
            $salida[] = [
                'fecha' => $fecha,
                'ingresos' => (int) ($loginSeries->get($fecha)->ingresos ?? 0),
                'estudiantes_login' => (int) ($loginSeries->get($fecha)->estudiantes ?? 0),
                'horas_activas' => $horas,
                'sesiones' => (int) ($series[$fecha]['sesiones'] ?? 0),
            ];
        }

        $nDiasActivos = max(count($diasActivos), 1);

        return response()->json([
            'kpis' => [
                'ingresos_hoy' => $ingresosHoy,
                'ingresos_total' => $ingresosTotal,
                'ingresos_7d' => $ingresos7d,
                'horas_diarias_prom' => round($totalHoras / $nDiasActivos, 2),
                'horas_semanales_prom' => round($totalHoras7d / 7, 2),
                'sesiones_prom_dia' => round($totalSesiones / $nDiasActivos, 2),
                'duracion_sesion_prom_min' => round(($totalHoras * 60) / max($totalSesiones, 1), 1),
            ],
            'serie' => $salida,
            'por_estudiante' => $porEstudianteResumen,
        ]);
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
