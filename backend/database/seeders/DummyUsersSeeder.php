<?php

namespace Database\Seeders;

use Illuminate\Database\Seeder;
use Illuminate\Support\Facades\Hash;
use App\Models\Student;

class DummyUsersSeeder extends Seeder
{
    public function run()
    {
        $programas = [
            'Administración de Empresas',
            'Contaduría Pública',
            'Ingeniería de Sistemas y Computación',
            'Ingeniería Electrónica',
            'Ingeniería Agronómica',
            'Zootecnia',
            'Licenciatura en Ciencias Sociales',
            'Licenciatura en Educación Física, Recreación y Deportes'
        ];

        $results = [];
        foreach ($programas as $i => $programa) {
            $cedula = "202610" . $i;
            $password_raw = "demo123";
            $hash_input = $cedula . $password_raw;
            
            $student = Student::updateOrCreate(
                ['cedula' => $cedula],
                [
                    'nombre' => 'Estudiante de ' . $programa,
                    'programa' => $programa,
                    'password_hash' => Hash::make($hash_input)
                ]
            );

            $results[] = [
                'Programa' => $programa,
                'Nombre' => $student->nombre,
                'Usuario (Cedula)' => $cedula,
                'Contraseña (Clave Secreta)' => $password_raw
            ];
        }

        $filePath = database_path('seeders/usuarios_prueba.csv');
        $file = fopen($filePath, 'w');
        // UTF-8 BOM
        fputs($file, "\xEF\xBB\xBF");
        fputcsv($file, array_keys($results[0]), ';');
        foreach ($results as $row) {
            fputcsv($file, array_values($row), ';');
        }
        fclose($file);

        $this->command->info("Usuarios creados exitosamente.");
        $this->command->info("Archivo CSV guardado en: {$filePath}");
    }
}
