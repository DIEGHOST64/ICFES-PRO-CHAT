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
        ]);

        $student = $request->user(); // Autenticado con Sanctum

        // RF-11: Anonimización — hash del ID del estudiante con sal fija del proyecto
        $studentHash = hash('sha256', 'icfes_salt_' . $student->id);

        $query = Query::create([
            'student_hash' => $studentHash,
            'programa' => $request->programa,
            'competencia' => $request->competencia,
            'pregunta' => $request->pregunta,
            'respuesta' => $request->respuesta,
            'tiempo_respuesta_ms' => $request->tiempo_respuesta_ms,
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
            ->select(['id', 'pregunta', 'respuesta', 'competencia', 'calificacion', 'created_at'])
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
}
