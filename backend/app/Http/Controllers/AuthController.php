<?php

namespace App\Http\Controllers;

use App\Models\Student;
use App\Models\Coordinator;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Facades\Validator;

class AuthController extends Controller
{
    private function normalizeCedula(?string $cedula): string
    {
        $raw = trim((string) $cedula);
        $digits = preg_replace('/\D+/', '', $raw) ?? '';
        return $digits !== '' ? $digits : $raw;
    }

    /**
     * RF-01, RF-02: Registro de estudiante
     * Campos: cedula, nombre, programa, clave_secreta
     * Se almacena bcrypt(cedula + clave_secreta)
     */
    public function registerStudent(Request $request)
    {
        $request->merge([
            'cedula' => $this->normalizeCedula($request->input('cedula')),
            'clave_secreta' => trim((string) $request->input('clave_secreta')),
        ]);

        $validator = Validator::make($request->all(), [
            'cedula' => 'required|string|max:20|unique:students,cedula',
            'nombre' => 'required|string|max:150',
            'email' => 'required|email|max:255',
            'programa' => 'required|string|max:100',
            'clave_secreta' => 'required|string|max:1', // 1 carácter — RF-01
        ]);

        if ($validator->fails()) {
            return response()->json([
                'message' => 'Datos inválidos.',
                'errors' => $validator->errors(),
            ], 422);
        }

        $passwordHash = Hash::make($request->cedula . $request->clave_secreta);

        $student = Student::create([
            'cedula' => $request->cedula,
            'nombre' => $request->nombre,
            'email' => $request->email,
            'programa' => $request->programa,
            'password_hash' => $passwordHash,
        ]);

        $token = $student->createToken('student_token', ['role:student'])->plainTextToken;

        return response()->json([
            'message' => '¡Registro exitoso! Bienvenido al asistente Saber Pro.',
            'token' => $token,
            'student' => [
                'nombre' => $student->nombre,
                'programa' => $student->programa,
            ],
        ], 201);
    }

    /**
     * RF-03: Inicio de sesión del estudiante
     * Valida bcrypt(cedula + clave_secreta) contra el hash almacenado
     */
    public function loginStudent(Request $request)
    {
        $rawCedula = trim((string) $request->input('cedula'));
        $normalizedCedula = $this->normalizeCedula($rawCedula);
        $clave = trim((string) $request->input('clave_secreta'));

        $request->merge([
            'cedula' => $normalizedCedula,
            'clave_secreta' => $clave,
        ]);

        $validator = Validator::make($request->all(), [
            'cedula' => 'required|string',
            'clave_secreta' => 'required|string',
        ]);

        if ($validator->fails()) {
            return response()->json(['message' => 'Cédula y clave secreta son requeridas.'], 422);
        }

        $student = Student::query()
            ->where('cedula', $request->cedula)
            ->orWhere('cedula', $rawCedula)
            ->first();

        $candidateCurrentNormalized = $request->cedula . $request->clave_secreta;
        $candidateCurrentStored = $student ? ((string) $student->cedula) . $request->clave_secreta : '';
        $candidateLegacy = $request->clave_secreta;
        $matchesCurrent = $student
            ? (Hash::check($candidateCurrentNormalized, $student->password_hash)
                || Hash::check($candidateCurrentStored, $student->password_hash))
            : false;
        $matchesLegacy = $student ? Hash::check($candidateLegacy, $student->password_hash) : false;

        if (!$student || (!$matchesCurrent && !$matchesLegacy)) {
            return response()->json([
                'message' => 'Credenciales incorrectas. Verifica tu cédula y clave secreta.',
            ], 401);
        }

        // Revocar tokens anteriores para sesión única
        $student->tokens()->delete();
        $token = $student->createToken('student_token', ['role:student'])->plainTextToken;

        return response()->json([
            'token' => $token,
            'student' => [
                'nombre' => $student->nombre,
                'programa' => $student->programa,
            ],
        ]);
    }

    /**
     * RF-12: Inicio de sesión del coordinador
     */
    public function loginCoordinator(Request $request)
    {
        $normalizedEmail = strtolower(trim((string) $request->input('email')));
        $normalizedPassword = trim((string) $request->input('password'));
        $request->merge([
            'email' => $normalizedEmail,
            'password' => $normalizedPassword,
        ]);

        $validator = Validator::make($request->all(), [
            'email' => 'required|email',
            'password' => 'required|string',
        ]);

        if ($validator->fails()) {
            return response()->json(['message' => 'Correo y contraseña son requeridos.'], 422);
        }

    $coordinator = Coordinator::whereRaw('LOWER(email) = ?', [$request->email])->first();

        if (!$coordinator || !Hash::check($request->password, $coordinator->password)) {
            return response()->json([
                'message' => 'Credenciales de coordinador incorrectas.',
            ], 401);
        }

        $coordinator->tokens()->delete();
        $token = $coordinator->createToken('coordinator_token', ['role:coordinator'])->plainTextToken;

        return response()->json([
            'token' => $token,
            'coordinator' => [
                'nombre' => $coordinator->nombre,
                'email' => $coordinator->email,
            ],
        ]);
    }

    /**
     * Cierre de sesión (revoca token actual)
     */
    public function logout(Request $request)
    {
        $request->user()->currentAccessToken()->delete();
        return response()->json(['message' => 'Sesión cerrada exitosamente.']);
    }
}
