# 1. Install Python and pip
# (Make sure Python and pip are installed on your system)

# 2. Install virtualenv
pip install virtualenv

# 3. Create and activate the virtual environment
python3 -m venv .venv

# Activate virtual environment
# Linux:
source .venv/bin/activate

# Windows:
.venv\Scripts\activate.bat

# 4. Install project dependencies
pip install -r requirements.txt

# 5. (Linux only) Set script permissions
chmod u+x build_simulation.sh run_simulation.sh

# 6. Build the simulation
# Linux:
./build_simulation.sh

# Windows:
build_simulation.bat

# 7. Run the simulation
# Linux:
./run_simulation.sh

# Windows:
run_simulation.bat
