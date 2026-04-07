<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('queries', function (Blueprint $table) {
            $table->unsignedBigInteger('student_id')->nullable()->after('id');
            $table->string('student_nombre', 150)->nullable()->after('student_id');
            $table->boolean('es_practica')->default(false)->after('tiempo_respuesta_ms');
            $table->boolean('acierto')->nullable()->after('es_practica');

            $table->index(['es_practica', 'programa']);
            $table->index(['programa', 'competencia', 'es_practica']);
        });

        // Backfill inicial: inferir intentos de practica desde el texto guardado historicamente.
        DB::statement("UPDATE queries SET es_practica = true WHERE respuesta LIKE 'Respuesta elegida:%Respuesta correcta:%'");

        DB::statement("
            UPDATE queries
            SET acierto = (
                regexp_replace(split_part(split_part(respuesta, E'\\n', 1), 'Respuesta elegida: ', 2), '^\\s+|\\s+$', '', 'g') =
                regexp_replace(split_part(split_part(respuesta, E'\\n', 2), 'Respuesta correcta: ', 2), '^\\s+|\\s+$', '', 'g')
            )
            WHERE es_practica = true AND acierto IS NULL
        ");
    }

    public function down(): void
    {
        Schema::table('queries', function (Blueprint $table) {
            $table->dropIndex(['es_practica', 'programa']);
            $table->dropIndex(['programa', 'competencia', 'es_practica']);
            $table->dropColumn(['student_id', 'student_nombre', 'es_practica', 'acierto']);
        });
    }
};
