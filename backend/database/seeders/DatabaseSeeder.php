<?php

namespace Database\Seeders;

use App\Models\User;
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
        // User::factory(10)->create();

        User::create([
            'name' => 'Test User',
            'email' => 'test@example.com',
            'password' => bcrypt('password'),
        ]);

        \App\Models\Student::create([
            'cedula' => '123456789',
            'nombre' => 'Estudiante Demo',
            'programa' => 'Ingeniería de Sistemas',
            'password_hash' => bcrypt('123456789123456789'),
        ]);

        // Crear coordinador por defecto
        Coordinator::create([
            'nombre' => 'Coordinador Demo',
            'email' => 'coordinador@example.com',
            'password' => bcrypt('password'),
        ]);
    }
}
