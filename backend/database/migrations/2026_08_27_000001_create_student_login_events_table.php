<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('student_login_events', function (Blueprint $table) {
            $table->id();
            $table->unsignedBigInteger('student_id')->nullable();
            $table->string('student_hash', 64)->nullable();
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('student_login_events');
    }
};
