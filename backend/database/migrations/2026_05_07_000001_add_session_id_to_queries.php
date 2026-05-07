<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('queries', function (Blueprint $table) {
            $table->string('session_id', 64)->nullable()->after('id');
            $table->index(['student_hash', 'session_id']);
        });
    }

    public function down(): void
    {
        Schema::table('queries', function (Blueprint $table) {
            $table->dropIndex(['student_hash', 'session_id']);
            $table->dropColumn('session_id');
        });
    }
};
