# Install Steps

1. **Install Python**
2. **Install pip**
3. **Install requirements**  
   - Run:  
     ```sh
     pip install -r requirements.txt
     ```
4. **Create a virtual environment**  
   - Run:  
     ```sh
     python3 -m venv .venv
     ```
5. **Activate the virtual environment**  
   - You should see `(.venv)` appear in the console.  
   - **Linux**:  
     ```sh
     source .venv/bin/activate
     ```
     - Use `deactivate` to exit the `.venv` console environment.  
   - **Windows**:  
     ```sh
     .venv\Scripts\activate.bat
     ```
     - Use `.venv\Scripts\deactivate.bat` to exit the `.venv` console environment.
6. **Change script permissions (Linux only)**  
   - Run:  
     ```sh
     chmod u+x build_simulation.sh run_simulation.sh
     ```
7. **Build the simulation**  
   - **Linux**:  
     ```sh
     ./build_simulation.sh
     ```
   - **Windows**:  
     ```sh
     build_simulation.bat
     ```
8. **Run the simulation**  
   - **Linux**:  
     ```sh
     ./run_simulation.sh
     ```
   - **Windows**:  
     ```sh
     run_simulation.bat
     ```
