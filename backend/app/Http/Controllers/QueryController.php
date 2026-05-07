<?php

namespace App\Http\Controllers;

use App\Models\Query;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Hash;

class QueryController extends Controller
{
    /**
     * RF-11: Almacena una consulta anonimizada en PostgreSQL.
     * Recibe la respuesta ya generada por el microservicio IA (Laravel actúa como proxy).
     */
    public function store(Request $request)
    {
        $request->validate([
            'programa' => 'required|string|max:100',
            'competencia' => 'nullable|string|max:100',
            'pregunta' => 'required|string',
            'respuesta' => 'required|string',
            'tiempo_respuesta_ms' => 'nullable|integer',
            'es_practica' => 'nullable|boolean',
            'acierto' => 'nullable|boolean',
            'nivel_objetivo' => 'nullable|string|max:20',
            'nivel_pregunta' => 'nullable|string|max:20',
            'tipo_pregunta' => 'nullable|string|max:40',
            'respuesta_visual' => 'nullable|string',
            'session_id' => 'nullable|string|max:64',
        ]);

        $student = $request->user(); // Autenticado con Sanctum

        // El estudiante demo (123456789) no guarda métricas reales
        if ($student->cedula === '123456789') {
            return response()->json([
                'id' => 0,
                'message' => 'Modo demo — consulta no almacenada.',
            ], 200);
        }

        // RF-11: Anonimización — hash del ID del estudiante con sal fija del proyecto
        $studentHash = hash('sha256', 'icfes_salt_' . $student->id);

        $query = Query::create([
            'session_id' => $request->get('session_id'),
            'student_id' => $student->id,
            'student_nombre' => $student->nombre,
            'student_hash' => $studentHash,
            'programa' => $request->programa,
            'competencia' => $request->competencia,
            'pregunta' => $request->pregunta,
            'respuesta' => $request->respuesta,
            'tiempo_respuesta_ms' => $request->tiempo_respuesta_ms,
            'es_practica' => $request->boolean('es_practica', false),
            'acierto' => $request->has('acierto') ? $request->boolean('acierto') : null,
            'nivel_objetivo' => $request->get('nivel_objetivo'),
            'nivel_pregunta' => $request->get('nivel_pregunta'),
            'tipo_pregunta' => $request->get('tipo_pregunta'),
            'respuesta_visual' => $request->get('respuesta_visual'),
            'calificacion' => null,
        ]);

        return response()->json([
            'id' => $query->id,
            'message' => 'Consulta registrada.',
        ], 201);
    }

    /**
     * RF-08: Historial de los últimos 5 días para el estudiante autenticado.
     */
    public function history(Request $request)
    {
        $student = $request->user();
        $studentHash = hash('sha256', 'icfes_salt_' . $student->id);

        $queries = Query::where('student_hash', $studentHash)
            ->where('created_at', '>=', now()->subDays(5))
            ->orderBy('created_at', 'asc')
            ->select(['id', 'session_id', 'pregunta', 'respuesta', 'respuesta_visual', 'competencia', 'calificacion', 'es_practica', 'acierto', 'created_at'])
            ->get();

        return response()->json($queries);
    }

    /**
     * RF-10: Calificación de respuesta como útil o no útil.
     */
    public function rate(Request $request, $id)
    {
        $request->validate([
            'util' => 'required|boolean',
        ]);

        $student = $request->user();
        $studentHash = hash('sha256', 'icfes_salt_' . $student->id);

        $query = Query::where('id', $id)
            ->where('student_hash', $studentHash)
            ->firstOrFail();

        $query->update(['calificacion' => $request->util]);

        return response()->json(['message' => 'Calificación registrada. ¡Gracias!']);
    }

    /**
     * Actualiza los datos visuales (imagen guía, LaTeX, pasos) de una consulta ya guardada.
     */
    public function updateVisual(Request $request, $id)
    {
        $request->validate([
            'respuesta_visual' => 'required|string',
        ]);

        $student = $request->user();
        $studentHash = hash('sha256', 'icfes_salt_' . $student->id);

        $query = Query::where('id', $id)
            ->where('student_hash', $studentHash)
            ->firstOrFail();

        $query->update(['respuesta_visual' => $request->respuesta_visual]);

        return response()->json(['message' => 'Datos visuales actualizados.']);
    }
}
