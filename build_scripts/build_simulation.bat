@ECHO OFF
REM This script is used to build the simulation environment for the project

REM Set environment variables
SET root_dir=%CD%\..
SET build_scripts_dir=%root_dir%\build_scripts
SET helpers_dir=%root_dir%\helpers

REM Clean the tree of old build files
cd %root_dir%
ECHO Cleaning up old build files ...
RMDIR /S /Q build\
DEL /Q client.spec
DEL /Q server.spec
DEL /Q client.exe
DEL /Q server.exe
DEL /Q server_ota_updates.db
DEL /Q client_linux_ota_updates.db
DEL /Q client_windows_ota_updates.db
RMDIR /S /Q install_location\

REM Create the update installation path
IF NOT EXIST "%root_dir%\install_location" (
    ECHO Creating update installation path ...
    MKDIR "%root_dir%\install_location"
)

REM Setup new databases and populate the tables
ECHO Setting up new databases ...
CALL python %helpers_dir%\setup_db.py

REM Build executables
ECHO Building executables...
CALL pyinstaller --onefile --name client --distpath "%root_dir%" client.py
CALL pyinstaller --onefile --name server --distpath "%root_dir%" server.py

REM Return back to the build_scripts directory
ECHO Build complete.
CD %build_scripts_dir%



