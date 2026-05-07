<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Query extends Model
{
    protected $fillable = [
        'session_id',
        'student_id',
        'student_nombre',
        'student_hash',
        'programa',
        'competencia',
        'pregunta',
        'respuesta',
        'respuesta_visual',
        'tiempo_respuesta_ms',
        'es_practica',
        'acierto',
        'nivel_objetivo',
        'nivel_pregunta',
        'tipo_pregunta',
        'calificacion',
    ];

    protected $casts = [
        'es_practica' => 'boolean',
        'acierto' => 'boolean',
        'calificacion' => 'boolean',
    ];
}
