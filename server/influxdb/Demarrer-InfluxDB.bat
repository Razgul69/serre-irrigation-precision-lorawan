@echo off
title InfluxDB Server
echo.
echo  ================================================
echo   InfluxDB 2.7 - Demarrage...
echo   Interface web : http://localhost:8086
echo  ================================================
echo.
cd /d "D:\InfluxDB"
influxd.exe --config-path D:\InfluxDB\config.yml
pause
