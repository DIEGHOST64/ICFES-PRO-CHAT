<?php

namespace Database\Seeders;

use App\Models\Coordinator;
use Illuminate\Database\Console\Seeds\WithoutModelEvents;
use Illuminate\Database\Seeder;

class DatabaseSeeder extends Seeder
{
    use WithoutModelEvents;

    /**
     * Seed the application's database.
     */
    public function run(): void
    {
        \App\Models\Student::updateOrCreate(
            ['cedula' => '123456789'],
            [
                'nombre' => 'Estudiante Demo',
                'email' => 'estudiante@saberpro.edu.co',
                'programa' => 'Ingeniería de Sistemas',
                'password_hash' => bcrypt('1234567891'),
            ]
        );

        \App\Models\Coordinator::updateOrCreate(
            ['email' => 'coordinador@saberpro.edu.co'],
            [
                'nombre' => 'Gestor Demo',
                'password' => bcrypt('admin123'),
            ]
        );
    }
}
