<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class StudentLoginEvent extends Model
{
    protected $fillable = [
        'student_id',
        'student_hash',
    ];
}
