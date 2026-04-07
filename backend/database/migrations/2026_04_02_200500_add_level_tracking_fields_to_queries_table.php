<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('queries', function (Blueprint $table) {
            $table->string('nivel_objetivo', 20)->nullable()->after('acierto');
            $table->string('nivel_pregunta', 20)->nullable()->after('nivel_objetivo');
            $table->string('tipo_pregunta', 40)->nullable()->after('nivel_pregunta');

            $table->index(['es_practica', 'competencia', 'nivel_objetivo']);
            $table->index(['es_practica', 'competencia', 'nivel_pregunta']);
        });
    }

    public function down(): void
    {
        Schema::table('queries', function (Blueprint $table) {
            $table->dropIndex(['es_practica', 'competencia', 'nivel_objetivo']);
            $table->dropIndex(['es_practica', 'competencia', 'nivel_pregunta']);
            $table->dropColumn(['nivel_objetivo', 'nivel_pregunta', 'tipo_pregunta']);
        });
    }
};
