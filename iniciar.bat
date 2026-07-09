@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
cd /d "%~dp0"
title GD Frete Diagnostico - Iniciando

echo.
echo  ========================================
echo   GD Frete Diagnostico - Iniciando...
echo  ========================================
echo.

REM ---------------------------------------------------------------------------
REM 1) Docker Desktop esta rodando?
REM ---------------------------------------------------------------------------
docker info >nul 2>&1
if errorlevel 1 (
  echo  [ERRO] O Docker Desktop nao esta em execucao.
  echo         Abra o Docker Desktop, espere aparecer "Engine running" e rode de novo.
  echo.
  pause
  exit /b 1
)

REM ---------------------------------------------------------------------------
REM 2) Garantir o backend\.env  ^(SEM ele o compose aborta e NADA sobe^)
REM    Essa era a causa do banco nao subir.
REM ---------------------------------------------------------------------------
if not exist "backend\.env" (
  if exist "backend\.env.example" (
    copy /y "backend\.env.example" "backend\.env" >nul
    echo  [OK]  Arquivo backend\.env criado a partir do .env.example.
  ) else (
    echo  [ERRO] Nao existe backend\.env nem backend\.env.example.
    echo         Crie o backend\.env antes de continuar.
    echo.
    pause
    exit /b 1
  )
) else (
  echo  [OK]  backend\.env encontrado.
)

REM ---------------------------------------------------------------------------
REM 3) Subir os containers ^(db + backend + frontend^)
REM ---------------------------------------------------------------------------
echo.
echo  Subindo containers... (na primeira vez pode demorar alguns minutos)
docker compose -f docker-compose.dev.yml up --build -d
if errorlevel 1 (
  echo.
  echo  [ERRO] Falha ao subir os containers. Ultimos logs:
  echo  ----------------------------------------------------------------------
  docker compose -f docker-compose.dev.yml logs --tail=40
  echo  ----------------------------------------------------------------------
  echo  Corrija o erro acima e rode o iniciar.bat de novo.
  echo.
  pause
  exit /b 1
)
echo  [OK]  Containers iniciados.

REM ---------------------------------------------------------------------------
REM 4) Esperar o BACKEND responder (migracoes + API) antes de abrir o navegador
REM ---------------------------------------------------------------------------
echo.
where curl >nul 2>&1
if errorlevel 1 (
  echo  Aguardando aplicacao subir (60s)...
  timeout /t 60 /nobreak >nul
  goto abrir
)

echo  Aguardando o backend (migracoes + API) ficar pronto...
set /a _n=0
:esperar
curl -s -f http://localhost:8000/ >nul 2>&1
if not errorlevel 1 goto pronto
set /a _n+=1
if !_n! GEQ 60 (
  echo.
  echo  [AVISO] O backend demorou mais que o esperado. Verifique os logs com:
  echo          docker compose -f docker-compose.dev.yml logs -f backend
  goto abrir
)
<nul set /p "=."
timeout /t 3 /nobreak >nul
goto esperar
:pronto
echo.
echo  [OK]  Backend no ar.

:abrir
echo.
echo  Abrindo no navegador...
start http://localhost:5173

echo.
echo  ========================================
echo   Aplicacao rodando!
echo   Frontend: http://localhost:5173
echo   Backend:  http://localhost:8000/docs
echo.
echo   Login dev: admin@gdconecta.com.br
echo   Para encerrar: parar.bat
echo  ========================================
echo.
pause
endlocal
