@ECHO OFF
REM This script is used to build the simulation environment for the project

SET root_dir=%CD%\..
SET build_scripts_dir=%root_dir%\build_scripts
SET helpers_dir=%root_dir%\helpers

REM Clean tree of old build files
cd %root_dir%
ECHO Cleaning up old build files...
RMDIR /S /Q build\
DEL /Q client.spec
DEL /Q server.spec
DEL /Q client.exe
DEL /Q server.exe
DEL /Q server_ota_updates.db
DEL /Q client_linux_ota_updates.db
DEL /Q client_windows_ota_updates.db

REM Setup new databases
ECHO Setting up new databases...
CALL python %helpers_dir%\setup_db.py

REM Build executables
ECHO Building executables...
CALL pyinstaller --onefile --name client --distpath "%root_dir%" client.py
CALL pyinstaller --onefile --name server --distpath "%root_dir%" server.py

CD %build_scripts_dir%