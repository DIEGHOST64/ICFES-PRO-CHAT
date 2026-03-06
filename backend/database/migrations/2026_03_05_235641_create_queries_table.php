<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration 
{
    public function up(): void
    {
        Schema::create('queries', function (Blueprint $table) {
            $table->id();
            // Identificador anonimizado del estudiante — RF-11, RNF-06
            $table->string('student_hash', 64);
            $table->string('programa', 100)->index();
            $table->string('competencia', 100)->nullable();
            $table->text('pregunta');
            $table->text('respuesta');
            // Tiempo de respuesta en milisegundos
            $table->unsignedInteger('tiempo_respuesta_ms')->nullable();
            // null=sin calificar, true=útil, false=no útil — RF-10
            $table->boolean('calificacion')->nullable();
            $table->timestamps();

            $table->index('created_at');
            $table->index(['programa', 'created_at']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('queries');
    }
};
