@ECHO OFF
REM This script is used to run the simulation project

SET root_dir=%CD%\..
SET build_scripts_dir=%root_dir%\build_scripts

cd %root_dir%
START CMD /C "server.exe"
START CMD /C "client.exe"

cd %build_scripts_dir%