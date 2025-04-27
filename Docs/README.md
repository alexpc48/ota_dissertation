# Install Steps

1. **Install Python**

2. **Install pip**

3. **Install virtualenv**  
   - Run:  
     ```sh
     pip install virtualenv
     ```

4. **Create a virtual environment**  
   - Run:  
     ```sh
     python3 -m venv .venv
     ```

5. **Activate the virtual environment**  
   - **Linux**:  
     ```sh
     source .venv/bin/activate
     ```
     - Use `deactivate` to exit the `.venv` console environment.  
   - **Windows**:  
     ```sh
     .venv\Scripts\activate.bat
     ```
     - You should see `(.venv)` appear in the console.
     - Use `.venv\Scripts\deactivate` or `.venv\Scripts\deactivate.bat` to exit the `.venv` console environment.

6. **Install requirements**  
   - Run:  
     ```sh
     pip install -r requirements.txt
     ```

7. **Change script permissions (Linux only)**  
   - Run:  
     ```sh
     chmod u+x build_simulation.sh run_simulation.sh
     ```

8. **Edit IP addresses**
   - Edit `helpers\setup_db.py`
   - To run the simulation, uncomment only the local host IP addresses and ports
   - To run on a network, uncomment the relevnat block of IP addresses and ports

9. **Build the simulation**
   - Change directory to `build_scripts\` and then run the following:
   - **Linux**:  
     ```sh
     ./build_simulation.sh
     ```
   - **Windows**:  
     ```sh
     build_simulation.bat
     ```

11. **Run the simulation**
   - If running on the local host, do the following:
   - **Linux**:  
     ```sh
     ./run_simulation.sh
     ```
   - **Windows**:  
     ```sh
     run_simulation.bat
     ```
     
   - If running on a network, change back to the parent directory (`cd ..`), and then for each device run the correct executable:
   - **Linux**:
   - To run the client
     ```sh
     ./client.exe
     ```
   - To run the server
     ```sh
     ./server.exe
     ```
   - **Windows**:  
   - To run the client
     ```sh
     client.exe
     ```
   - To run the server
     ```sh
     server.exe
     ```
