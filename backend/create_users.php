<?php
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
    $cedula = 1000 + $i;
    $password_raw = "123456";
    $hash_input = $cedula . $password_raw;
    
    // Create or update
    $student = \App\Models\Student::updateOrCreate(
        ['cedula' => (string)$cedula],
        [
            'nombre' => 'Estudiante ' . $programa,
            'programa' => $programa,
            'password_hash' => bcrypt($hash_input)
        ]
    );

    $results[] = [
        'Programa' => $programa,
        'Nombre' => $student->nombre,
        'Usuario (Cedula)' => $cedula,
        'Contraseña (Clave Secreta)' => $password_raw
    ];
}

// Ensure the directory exists
@mkdir('/var/www/html/storage/app/public', 0755, true);

$file = fopen('/var/www/html/storage/app/public/usuarios_prueba.csv', 'w');
// UTF-8 BOM for Excel
fputs($file, "\xEF\xBB\xBF");
fputcsv($file, array_keys($results[0]), ';');
foreach ($results as $row) {
    fputcsv($file, array_values($row), ';');
}
fclose($file);

echo "CSVDONE";
