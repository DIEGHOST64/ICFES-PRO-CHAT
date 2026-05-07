<?php

use App\Http\Controllers\AuthController;
use App\Http\Controllers\DashboardController;
use App\Http\Controllers\QueryController;
use App\Http\Controllers\StudentController;
use Illuminate\Support\Facades\Route;

Route::get('/health', fn () => response()->json(['status' => 'ok', 'service' => 'backend']));

// ─── Rutas públicas ─────────────────────────────────────
Route::prefix('auth')->group(function () {
    Route::post('register', [AuthController::class , 'registerStudent']); // RF-01, RF-02
    Route::post('login', [AuthController::class , 'loginStudent']); // RF-03
    Route::post('coordinator/login', [AuthController::class , 'loginCoordinator']); // RF-12
});

// ─── Rutas protegidas (estudiante autenticado) ───────────
Route::middleware('auth:sanctum')->group(function () {
    Route::post('auth/logout', [AuthController::class , 'logout']);

    // Consultas — RF-05, RF-08, RF-10, RF-11
    Route::post('queries', [QueryController::class , 'store']);
    Route::get('queries/history', [QueryController::class , 'history']);
    Route::patch('queries/{id}/rate', [QueryController::class , 'rate']);
    Route::patch('queries/{id}/visual', [QueryController::class , 'updateVisual']);
});

// ─── Rutas protegidas (solo coordinador) ────────────────
Route::middleware(['auth:sanctum', 'ability:role:coordinator'])->group(function () {
    // Gestión de estudiantes — RF-13, RF-14
    Route::get('students', [StudentController::class , 'index']);
    Route::get('students/programs', [StudentController::class , 'programs']);

    // Dashboard e indicadores — RF-15 a RF-19
    Route::get('dashboard/metrics', [DashboardController::class , 'metrics']);
    Route::get('dashboard/programs', [DashboardController::class , 'programs']);
    Route::get('dashboard/by-program', [DashboardController::class , 'byProgram']);
    Route::get('dashboard/trend', [DashboardController::class , 'trend']);
    Route::get('dashboard/top-topics', [DashboardController::class , 'topTopics']);
    Route::get('dashboard/practice-students', [DashboardController::class , 'practiceStudents']);
    Route::get('dashboard/practice-competencies', [DashboardController::class , 'practiceCompetencies']);
    Route::get('dashboard/level-progression', [DashboardController::class , 'levelProgression']);
    Route::get('dashboard/difficulty-distribution', [DashboardController::class , 'difficultyDistribution']);
    Route::get('dashboard/english-parts', [DashboardController::class , 'englishParts']);
    Route::get('dashboard/response-time', [DashboardController::class , 'responseTime']);
    Route::get('dashboard/ratings-breakdown', [DashboardController::class , 'ratingsBreakdown']);
});
