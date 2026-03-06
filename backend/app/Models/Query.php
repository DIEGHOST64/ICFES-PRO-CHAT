<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Query extends Model
{
    protected $fillable = [
        'student_hash',
        'programa',
        'competencia',
        'pregunta',
        'respuesta',
        'tiempo_respuesta_ms',
        'calificacion',
    ];

    protected $casts = [
        'calificacion' => 'boolean',
    ];
}
