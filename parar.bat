@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title GD Frete Diagnostico - Parando

echo.
echo  ========================================
echo   GD Frete Diagnostico - Parando...
echo  ========================================
echo.

docker info >nul 2>&1
if errorlevel 1 (
  echo  [AVISO] O Docker nao esta rodando - nada a parar.
  echo.
  pause
  exit /b 0
)

REM  "down" para e remove os containers, mas PRESERVA os dados do banco
REM  (o volume nomeado gd_pg_dev_data continua intacto).
docker compose -f docker-compose.dev.yml down

echo.
echo  Aplicacao encerrada. Os dados do banco foram preservados.
echo.
echo  Obs.: para APAGAR TAMBEM os dados do banco (recomeco do zero), use:
echo        docker compose -f docker-compose.dev.yml down -v
echo.
pause
endlocal
