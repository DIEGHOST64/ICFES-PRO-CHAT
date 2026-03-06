<?php

namespace App\Http\Controllers;

use App\Models\Student;
use Illuminate\Http\Request;

class StudentController extends Controller
{
    /**
     * RF-13, RF-14: Listado de estudiantes con filtro opcional por programa.
     * Solo accesible por coordinadores.
     */
    public function index(Request $request)
    {
        $query = Student::select(['id', 'cedula', 'nombre', 'programa', 'created_at']);

        // RF-14: Filtro por programa
        if ($request->has('programa') && $request->programa !== '') {
            $query->where('programa', $request->programa);
        }

        $students = $query->orderBy('nombre')->paginate(20);

        return response()->json($students);
    }

    /**
     * Listado de programas únicos para el filtro del coordinador.
     */
    public function programs()
    {
        $programs = Student::distinct()->pluck('programa')->sort()->values();
        return response()->json($programs);
    }
}
