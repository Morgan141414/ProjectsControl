# ProjectsControl — запуск backend + frontend
$root = "C:\project on my Local PC\ProjectsControl"
$venv = "$root\.venv\Scripts\python.exe"

# 1) Backend
Start-Process -FilePath $venv -ArgumentList "-m","uvicorn","app.main:app","--host","127.0.0.1","--port","8000" -WorkingDirectory "$root\backend" -WindowStyle Normal
Start-Sleep -Seconds 3

# 2) Frontend (через launcher, чтобы PYTHONPATH и ошибки были видны)
Start-Process -FilePath "powershell" -ArgumentList "-NoProfile","-ExecutionPolicy","Bypass","-File","`"$root\launch-frontend.ps1`"" -WorkingDirectory $root -WindowStyle Normal

Write-Host "Backend и Frontend запущены. Backend: http://127.0.0.1:8000"
