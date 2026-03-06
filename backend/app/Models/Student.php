<?php

namespace App\Models;

use Illuminate\Foundation\Auth\User as Authenticatable;
use Laravel\Sanctum\HasApiTokens;

class Student extends Authenticatable
{
    use HasApiTokens;

    protected $fillable = [
        'cedula',
        'nombre',
        'programa',
        'password_hash',
    ];

    protected $hidden = [
        'password_hash',
    ];

    /**
     * Campo de contraseña para Sanctum/Auth
     * El hash bcrypt se almacena en password_hash — RF-02
     */
    public function getAuthPassword(): string
    {
        return $this->password_hash;
    }

    /**
     * Identificador único para autenticación — RF-03
     */
    public function getAuthIdentifierName(): string
    {
        return 'cedula';
    }
}
