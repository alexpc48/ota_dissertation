# ota_dissertation
Install steps:
1. Install python
2. Install pip
3. Install requirements
    a. pip install -r requirements.txt
4. Create virutal environment
    a. python3 -m venv .venv
5. Activate virtual environment
    (.venv) should appear in the console
    a. Linux: source .venv/bin/activate
        Use deactivate to exit .venv console environment
    b. Windows: .venv/Scripts/activate.bat
        use .venv/Scripts/deactivate.bat to exit .venv console environment
6. Change script permissions (Linux)
    a. chmod u+x build_simulation.sh run_simulation.sh
7. Build simulation
    a. Linux: ./build_simulation.sh
    b. Windows: build_simulation.bat
8. Run simulation
    a. Linux: ./run_simulation.sh
    b. Windows: run_simulation.bat