# Запуск фронтенда ProjectsControl (окно остаётся открытым при ошибке)
$root = "C:\project on my Local PC\ProjectsControl"
$venv = "$root\.venv\Scripts\python.exe"
$env:PYTHONPATH = "$root\frontend"

Set-Location $root
& $venv "$root\frontend\app\main.py"
$code = $LASTEXITCODE
if ($code -ne 0) {
    Write-Host "Выход с кодом: $code" -ForegroundColor Red
    Read-Host "Нажмите Enter для закрытия"
}
