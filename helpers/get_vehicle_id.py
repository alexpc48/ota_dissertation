import platform
import subprocess

# AI used
# TODO: Rewrite and integrate for setup_db
# Gets the BIOS UUID of the system which is used as the unique identifier for the vehicle
def get_bios_uuid():
    try:
        if platform.system() == "Windows":
            result = subprocess.check_output("wmic csproduct get UUID", shell=True).decode()
            return result.split("\n")[1].strip()
        elif platform.system() == "Linux":
            try:
                result = subprocess.check_output("cat /sys/class/dmi/id/product_uuid", shell=True).decode()
            except:
                result = subprocess.check_output("cat /etc/machine-id", shell=True).decode()
            return result.strip()
        else:
            return 1
    except Exception as e:
        #print(f"An error occured: {e}")
        return 1
    
#print(get_bios_uuid())