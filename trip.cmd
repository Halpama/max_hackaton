@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul 2>&1

rem Trip Planner — jury-friendly launcher (Windows)
rem Usage: trip.cmd <command>   or   trip <command> if . is on PATH

cd /d "%~dp0"
set "ROOT=%CD%"
set "ENV_FILE=%ROOT%\backend\.env"
set "ENV_EXAMPLE=%ROOT%\backend\.env.example"
if not defined TRIP_API_URL set "TRIP_API_URL=http://localhost:8000"
if not defined TRIP_WEB_URL set "TRIP_WEB_URL=http://localhost:3000"

set "CMD=%~1"
if "%CMD%"=="" set "CMD=help"
shift

if /I "%CMD%"=="help" goto :help
if /I "%CMD%"=="-h" goto :help
if /I "%CMD%"=="--help" goto :help
if /I "%CMD%"=="up" goto :up
if /I "%CMD%"=="start" goto :up
if /I "%CMD%"=="down" goto :down
if /I "%CMD%"=="stop" goto :down
if /I "%CMD%"=="restart" goto :restart
if /I "%CMD%"=="status" goto :status
if /I "%CMD%"=="ps" goto :status
if /I "%CMD%"=="logs" goto :logs
if /I "%CMD%"=="log" goto :logs
if /I "%CMD%"=="bot" goto :bot
if /I "%CMD%"=="doctor" goto :doctor
if /I "%CMD%"=="check" goto :doctor
if /I "%CMD%"=="open" goto :open

echo [x] Unknown command: %CMD%
echo.
goto :help

:need_docker
where docker >nul 2>&1
if errorlevel 1 (
  echo [x] Docker not found. Install Docker Desktop and retry.
  exit /b 1
)
docker info >nul 2>&1
if errorlevel 1 (
  echo [x] Docker daemon is not running. Open Docker Desktop.
  exit /b 1
)
exit /b 0

:ensure_env
if exist "%ENV_FILE%" exit /b 0
if exist "%ENV_EXAMPLE%" (
  copy /Y "%ENV_EXAMPLE%" "%ENV_FILE%" >nul
  echo [!] Created backend\.env from .env.example — fill in keys and restart.
  exit /b 0
)
echo [x] Missing backend\.env and backend\.env.example
exit /b 1

:env_get
rem usage: call :env_get KEY  -> sets ENV_VAL
set "ENV_VAL="
if not exist "%ENV_FILE%" exit /b 0
for /f "usebackq tokens=1,* delims==" %%A in (`findstr /B /I /C:"%~1=" "%ENV_FILE%" 2^>nul`) do (
  set "ENV_VAL=%%B"
)
exit /b 0

:env_set
rem usage: call :env_set KEY VALUE
call :ensure_env
if errorlevel 1 exit /b 1
set "K=%~1"
set "V=%~2"
set "TMP=%TEMP%\trip-env-%RANDOM%.txt"
if exist "%TMP%" del /f /q "%TMP%" >nul 2>&1
set "FOUND=0"
for /f "usebackq delims=" %%L in ("%ENV_FILE%") do (
  set "LINE=%%L"
  echo !LINE! | findstr /B /I /C:"%K%=" >nul
  if not errorlevel 1 (
    echo %K%=%V%>>"%TMP%"
    set "FOUND=1"
  ) else (
    echo %%L>>"%TMP%"
  )
)
if "!FOUND!"=="0" (
  echo.>>"%TMP%"
  echo %K%=%V%>>"%TMP%"
)
move /Y "%TMP%" "%ENV_FILE%" >nul
exit /b 0

:wait_healthy
set "TRIES=%~1"
if "%TRIES%"=="" set "TRIES=60"
echo -^> Waiting for api healthy... (%TRIES%s max)
for /L %%I in (1,1,%TRIES%) do (
  curl -fsS --max-time 2 "%TRIP_API_URL%/health" >nul 2>&1
  if not errorlevel 1 (
    echo [+] api responds on /health
    exit /b 0
  )
  timeout /t 1 /nobreak >nul
)
echo [!] api not healthy yet — try: trip.cmd logs
exit /b 1

:help
echo.
echo Trip Planner — quick launcher for jury / demo
echo.
echo Usage:
echo   trip.cmd ^<command^>
echo.
echo Commands:
echo   up            start stack (postgres, redis, api, web) + status
echo   down          stop containers
echo   restart       rebuild/restart api
echo   status        services + integrations
echo   logs [svc]    follow logs (default: api)
echo   bot           MAX bot status
echo   bot on^|off    enable/disable bot + restart api
echo   bot mode ^<auto^|polling^|webhook^|off^>
echo   doctor        check Docker and .env keys
echo   open          open web + Swagger in browser
echo   help          this help
echo.
echo After trip.cmd up:
echo   Web      %TRIP_WEB_URL%
echo   API      %TRIP_API_URL%
echo   Swagger  %TRIP_API_URL%/docs
echo   Bot      %TRIP_API_URL%/api/v1/bot/status
echo.
echo Keys live in backend\.env (template: backend\.env.example).
echo On macOS/Linux use ./trip instead.
exit /b 0

:up
call :need_docker
if errorlevel 1 exit /b 1
call :ensure_env
if errorlevel 1 exit /b 1
echo.
echo === Starting Trip Planner ===
echo -^> docker compose up -d --build
docker compose up -d --build
if errorlevel 1 exit /b 1
call :wait_healthy 90
echo.
call :status
echo.
echo -^> Web:     %TRIP_WEB_URL%
echo -^> Swagger: %TRIP_API_URL%/docs
echo -^> Status:  trip.cmd status
echo -^> Bot:     trip.cmd bot
exit /b 0

:down
call :need_docker
if errorlevel 1 exit /b 1
echo.
echo === Stopping ===
docker compose down
echo [+] Stack stopped
exit /b 0

:restart
call :need_docker
if errorlevel 1 exit /b 1
call :ensure_env
if errorlevel 1 exit /b 1
echo.
echo === Restart api ===
docker compose up -d --build api
call :wait_healthy 60
call :status
exit /b 0

:logs
call :need_docker
if errorlevel 1 exit /b 1
set "SVC=%~1"
if "%SVC%"=="" set "SVC=api"
echo -^> Logs: %SVC% (Ctrl+C to stop)
docker compose logs -f --tail=120 %SVC%
exit /b 0

:open
start "" "%TRIP_WEB_URL%"
start "" "%TRIP_API_URL%/docs"
echo [+] Opened web + Swagger
exit /b 0

:doctor
echo.
echo === Doctor ===
call :need_docker
if errorlevel 1 exit /b 1
echo [+] Docker OK
call :ensure_env
if errorlevel 1 exit /b 1
echo [+] backend\.env present
echo.
echo === Keys in backend\.env ===
call :print_key_status GIGACHAT_AUTH_KEY required
call :print_key_status OPENTRIPMAP_API_KEY required
call :print_key_status ORS_API_KEY optional
call :print_key_status MAX_BOT_TOKEN optional
call :print_flag_status MAX_BOT_ENABLED
call :env_get MAX_BOT_MODE
if "!ENV_VAL!"=="" (echo [+] MAX_BOT_MODE=auto) else (echo [+] MAX_BOT_MODE=!ENV_VAL!)
call :env_get MAX_BOT_WEBHOOK_URL
if "!ENV_VAL!"=="" (echo [!] MAX_BOT_WEBHOOK_URL empty — auto uses polling) else (echo [+] MAX_BOT_WEBHOOK_URL=!ENV_VAL!)
call :env_get MAX_WEBAPP_URL
if "!ENV_VAL!"=="" (echo [!] MAX_WEBAPP_URL empty) else (echo [+] MAX_WEBAPP_URL=!ENV_VAL!)
exit /b 0

:print_key_status
call :env_get %~1
if "!ENV_VAL!"=="" (
  if /I "%~2"=="required" (echo [x] %~1 empty) else (echo [!] %~1 empty)
) else (
  echo [+] %~1 set
)
exit /b 0

:print_flag_status
call :env_get %~1
if /I "!ENV_VAL!"=="true" (echo [+] %~1=true) else if /I "!ENV_VAL!"=="1" (echo [+] %~1=!ENV_VAL!) else (echo [!] %~1=!ENV_VAL!)
exit /b 0

:status
call :need_docker
if errorlevel 1 exit /b 1
call :ensure_env
if errorlevel 1 exit /b 1
echo.
echo === Services ===
call :print_svc postgres
call :print_svc redis
call :print_svc api "%TRIP_API_URL%"
call :print_svc web "%TRIP_WEB_URL%"
echo.
echo === Integrations ===
curl -fsS --max-time 3 "%TRIP_API_URL%/health" > "%TEMP%\trip-health.json" 2>nul
if errorlevel 1 (
  echo [!] API unreachable — showing .env only
  call :status_from_env
) else (
  powershell -NoProfile -Command ^
    "$d=Get-Content -Raw '%TEMP%\trip-health.json' | ConvertFrom-Json; ^
     function R($ok,$l,$x){ if($ok){Write-Host '[+] '$l$(if($x){' — '+$x})}else{Write-Host '[x] '$l$(if($x){' — '+$x})} }; ^
     R ($d.status -in @('ok','degraded')) ('API status='+$d.status); ^
     R ([bool]$d.redis) 'Redis'; ^
     R ([bool]$d.gigachat) 'GigaChat' $(if($d.gigachat){'LLM'}else{'fallback'}); ^
     R ([bool]$d.opentripmap) 'OpenTripMap' $(if($d.opentripmap){'places'}else{'needs key'}); ^
     R ([bool]$d.ors) 'openrouteservice' $(if($d.ors){'routing'}else{'OSRM fallback'}); ^
     R ([bool]$d.kudago) 'KudaGo' 'hours/popularity'; ^
     R ([bool]$d.weather) 'Open-Meteo' 'daily weather'; ^
     $b=$d.bot; if($b.enabled -and $b.configured){R $true 'MAX bot' ('mode='+$b.mode)} elseif($b.configured){R $false 'MAX bot' ('token ok, ENABLED=false mode='+$b.mode)} else {R $false 'MAX bot' 'off / no token'}; ^
     if($b.webhookUrl){R $true 'Webhook URL' $b.webhookUrl} else {R $false 'Webhook URL' 'empty → polling'}"
)
exit /b 0

:status_from_env
call :print_key_status GIGACHAT_AUTH_KEY required
call :print_key_status OPENTRIPMAP_API_KEY required
call :print_key_status ORS_API_KEY optional
call :print_flag_status MAX_BOT_ENABLED
call :print_key_status MAX_BOT_TOKEN optional
exit /b 0

:print_svc
set "NAME=%~1"
set "URL=%~2"
for /f "tokens=1,2,3" %%A in ('docker compose ps --format "{{.Service}} {{.State}} {{.Health}}" 2^>nul ^| findstr /B /I /C:"%NAME% "') do (
  set "ST=%%B"
  set "HL=%%C"
)
if not defined ST (
  echo [x] %NAME%  down
  set "ST="
  set "HL="
  exit /b 0
)
if /I "!ST!"=="running" (
  if /I "!HL!"=="healthy" (
    if "%URL%"=="" (echo [+] %NAME%  healthy) else (echo [+] %NAME%  healthy  %URL%)
  ) else if /I "!HL!"=="unhealthy" (
    echo [x] %NAME%  unhealthy
  ) else if /I "!HL!"=="starting" (
    echo [!] %NAME%  starting...
  ) else (
    if "%URL%"=="" (echo [+] %NAME%  running) else (echo [+] %NAME%  running  %URL%)
  )
) else (
  echo [x] %NAME%  !ST!
)
set "ST="
set "HL="
exit /b 0

:bot
set "SUB=%~1"
if "%SUB%"=="" set "SUB=status"
if /I "%SUB%"=="status" goto :bot_status
if /I "%SUB%"=="on" goto :bot_on
if /I "%SUB%"=="off" goto :bot_off
if /I "%SUB%"=="mode" goto :bot_mode
echo [x] Unknown: bot %SUB%  (status^|on^|off^|mode)
exit /b 1

:bot_status
call :ensure_env
if errorlevel 1 exit /b 1
call :need_docker
if errorlevel 1 exit /b 1
echo.
echo === MAX bot ===
call :env_get MAX_BOT_ENABLED
if /I "!ENV_VAL!"=="true" (echo [+] MAX_BOT_ENABLED=true) else (echo [!] MAX_BOT_ENABLED=!ENV_VAL!)
call :env_get MAX_BOT_TOKEN
if "!ENV_VAL!"=="" (echo [x] MAX_BOT_TOKEN empty) else (echo [+] MAX_BOT_TOKEN set)
call :env_get MAX_BOT_MODE
if "!ENV_VAL!"=="" (echo [+] MAX_BOT_MODE=auto) else (echo [+] MAX_BOT_MODE=!ENV_VAL!)
call :env_get MAX_BOT_WEBHOOK_URL
if "!ENV_VAL!"=="" (echo [!] Webhook URL empty → polling when mode=auto) else (echo [+] Webhook: !ENV_VAL!)
call :env_get MAX_WEBAPP_URL
if "!ENV_VAL!"=="" (echo [!] MAX_WEBAPP_URL empty) else (echo [+] Mini-app: !ENV_VAL!)
echo.
echo -^> Live /api/v1/bot/status:
curl -fsS --max-time 3 "%TRIP_API_URL%/api/v1/bot/status" 2>nul
if errorlevel 1 (
  echo [!] API not responding — run trip.cmd up first
) else (
  echo.
)
echo.
echo How to enable for demo:
echo   1. Put MAX_BOT_TOKEN into backend\.env
echo   2. trip.cmd bot on
echo   3. Without public HTTPS — mode=polling ^(default auto^)
echo   4. With tunnel: set MAX_BOT_WEBHOOK_URL then trip.cmd bot mode webhook
exit /b 0

:bot_on
call :ensure_env
if errorlevel 1 exit /b 1
call :env_get MAX_BOT_TOKEN
if "!ENV_VAL!"=="" (
  echo [x] Set MAX_BOT_TOKEN in backend\.env first
  exit /b 1
)
call :env_set MAX_BOT_ENABLED true
call :env_get MAX_BOT_MODE
if "!ENV_VAL!"=="" call :env_set MAX_BOT_MODE auto
echo [+] MAX_BOT_ENABLED=true
echo -^> Restarting api...
docker compose up -d api
call :wait_healthy 45
call :bot_status
exit /b 0

:bot_off
call :env_set MAX_BOT_ENABLED false
echo [+] MAX_BOT_ENABLED=false
docker compose up -d api
call :wait_healthy 45
exit /b 0

:bot_mode
set "M=%~2"
if /I "%M%"=="auto" goto :bot_mode_ok
if /I "%M%"=="polling" goto :bot_mode_ok
if /I "%M%"=="webhook" goto :bot_mode_ok
if /I "%M%"=="off" goto :bot_mode_ok
echo [x] mode: auto ^| polling ^| webhook ^| off
exit /b 1

:bot_mode_ok
call :env_set MAX_BOT_MODE %M%
echo [+] MAX_BOT_MODE=%M%
if /I "%M%"=="webhook" (
  call :env_get MAX_BOT_WEBHOOK_URL
  if "!ENV_VAL!"=="" echo [!] Set MAX_BOT_WEBHOOK_URL=https://host/api/v1/bot/webhook
)
docker compose up -d api
call :wait_healthy 45
exit /b 0
