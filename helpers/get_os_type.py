import platform

def get_os_type_func():        
    os_type = platform.system()
    if os_type == "Windows":
        #print("The machine is running Windows.")
        pass
    elif os_type == "Linux":
        #print("The machine is running Linux.")
        pass
    return os_type