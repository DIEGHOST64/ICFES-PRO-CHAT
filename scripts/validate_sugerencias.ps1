$ErrorActionPreference = 'Stop'

$stop = @(
  'de','la','el','en','que','los','las','del','para','con','una','un','por','se','su','sus','al','como',
  'más','mas','entre','sobre','desde','hasta','cuando','donde','porque','segun','según','este','esta','estos',
  'estas','ese','esa','esos','esas','ser','estar','fue','son','han','hay','puede','pueden','cual','cuál',
  'cuáles','qué','como','cómo','their','with','from','that','this','these','those','into','about','during',
  'among','within','without','which','what','where','when','while','would','could','should'
)

$legalMarkers = @(
  'terminos y condiciones','términos y condiciones','politica de privacidad','política de privacidad','cookies',
  'licencia','suscripcion','suscripción','cancelacion','cancelación','administrador del sitio','sitio web',
  'uso indebido','datos personales'
)

$placeholderRegex = '(?i)^(opcion|opción)\s+[abcd]$|todas las anteriores|ninguna de las anteriores'

function Get-Tokens([string]$text) {
  if ([string]::IsNullOrWhiteSpace($text)) { return @() }
  $raw = [regex]::Matches($text.ToLowerInvariant(), '\p{L}{4,}') | ForEach-Object { $_.Value }
  return $raw | Where-Object { $stop -notcontains $_ } | Select-Object -Unique
}

function Shared-Count([string]$a, [string]$b) {
  $ta = Get-Tokens $a
  $tb = Get-Tokens $b
  if ($ta.Count -eq 0 -or $tb.Count -eq 0) { return 0 }

  $setB = @{}
  foreach ($t in $tb) { $setB[$t] = $true }

  $count = 0
  foreach ($t in $ta) {
    if ($setB.ContainsKey($t)) { $count++ }
  }

  return $count
}

$programa = [uri]::EscapeDataString('Ingeniería de Sistemas')
$cases = @(
  @{ competencia = 'General'; cantidad = 15; repeticiones = 3 },
  @{ competencia = 'General'; cantidad = 22; repeticiones = 2 },
  @{ competencia = 'General'; cantidad = 30; repeticiones = 2 },
  @{ competencia = 'Lectura Crítica'; cantidad = 15; repeticiones = 3 }
)

foreach ($case in $cases) {
  Write-Output "=== $($case.competencia) n=$($case.cantidad) ==="

  for ($i = 1; $i -le $case.repeticiones; $i++) {
    try {
      $url = "http://localhost:8000/sugerencias?programa=$programa&competencia=$([uri]::EscapeDataString($case.competencia))&cantidad=$($case.cantidad)"
      $resp = Invoke-RestMethod -Uri $url -Method Get
      if ($resp -is [System.Collections.IEnumerable] -and -not ($resp -is [string])) {
        $qs = @($resp)
      }
      elseif ($resp -and $resp.sugerencias) {
        $qs = @($resp.sugerencias)
      }
      else {
        $qs = @()
      }

      $dist = @{ A = 0; B = 0; C = 0; D = 0 }
      $legal = 0
      $placeholder = 0
      $suspect = 0

      foreach ($q in $qs) {
        $tb = [string]$q.texto_base
        $en = [string]$q.enunciado
        $lowTb = $tb.ToLowerInvariant()

        foreach ($m in $legalMarkers) {
          if ($lowTb.Contains($m)) {
            $legal++
            break
          }
        }

        $rc = [string]$q.respuesta_correcta
        $letter = ''
        if ($rc -match '^\s*([A-Da-d])') {
          $letter = $Matches[1].ToUpper()
        }
        if ($dist.ContainsKey($letter)) { $dist[$letter]++ }

        $optVals = @()
        if ($q.opciones -is [System.Collections.IEnumerable] -and -not ($q.opciones -is [string])) {
          $optVals = @($q.opciones)
        }
        elseif ($q.opciones -is [System.Collections.IDictionary]) {
          $optVals = @($q.opciones.Values)
        }
        elseif ($q.opciones) {
          $optVals = @($q.opciones.A, $q.opciones.B, $q.opciones.C, $q.opciones.D)
        }

        foreach ($ov in $optVals) {
          if (([string]$ov).Trim() -match $placeholderRegex) {
            $placeholder++
            break
          }
        }

        $ansText = ''
        if ($q.opciones -is [System.Collections.IEnumerable] -and -not ($q.opciones -is [string]) -and $q.respuesta_correcta) {
          $optsList = @($q.opciones)
          if ($rc -match '^\s*([A-Da-d])') {
            $idx = [int][char]$Matches[1].ToUpper() - [int][char]'A'
            if ($idx -ge 0 -and $idx -lt $optsList.Count) {
              $ansText = [string]$optsList[$idx]
            }
          }
          if (-not $ansText) {
            $ansText = $rc
          }
        }
        elseif ($q.opciones -is [System.Collections.IDictionary] -and $q.respuesta_correcta) {
          $k = [string]$q.respuesta_correcta
          if ($q.opciones.Contains($k)) { $ansText = [string]$q.opciones[$k] }
        }
        elseif ($q.opciones -and $q.respuesta_correcta) {
          $k = [string]$q.respuesta_correcta
          if ($q.opciones.PSObject.Properties.Name -contains $k) { $ansText = [string]$q.opciones.$k }
        }

        if ((Shared-Count $tb $en) -eq 0 -or (Shared-Count $tb $ansText) -eq 0) {
          $suspect++
        }
      }

      $exact = ($qs.Count -eq [int]$case.cantidad)
      Write-Output ("run={0} count={1} exact={2} legal={3} placeholder={4} suspect={5} dist=A:{6} B:{7} C:{8} D:{9}" -f $i, $qs.Count, $exact, $legal, $placeholder, $suspect, $dist.A, $dist.B, $dist.C, $dist.D)
    }
    catch {
      Write-Output ("run={0} ERROR={1}" -f $i, $_.Exception.Message)
    }
  }
}
