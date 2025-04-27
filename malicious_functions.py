# HEADER FILE
# EXAMPLE

import ssl, platform, selectors, socket, time, random, types, os, errno, sqlite3, dotenv, typing
from constants import *
from functions import *
from server_functions import *

# Only the create connection part since the system should detect the use of invalid certificates and exit the connection
def connect_with_invalid_tls(selector: selectors.DefaultSelector) -> typing.Tuple[selectors.DefaultSelector, ssl.SSLSocket, int]:
    try:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT) # Auto-negotiates highgest available protocol
        context.minimum_version = ssl.TLSVersion.TLSv1_3 # Enforces NIST-approved TLS 1.3 ciphers
        context.verify_mode = ssl.CERT_REQUIRED
        
        # Change certs depending on if testing on local host or remote host
        os_type = platform.system()
        # Local host
        if os_type == "Windows":
            context.load_cert_chain(certfile="cryptographic_material\\server_malicious_root_ca_certificate_local_host.pem", keyfile="cryptographic_material\\server_malicious_root_ca_private_key_local_host.pem")
            context.load_verify_locations(cafile="cryptographic_material\\root_ca_malicious.pem")
        elif os_type == "Linux":
            context.load_cert_chain(certfile="cryptographic_material/server_malicious_root_ca_certificate_local_host.pem", keyfile="cryptographic_material/server_malicious_root_ca_private_key_local_host.pem")
            context.load_verify_locations(cafile="cryptographic_material/root_ca_malicious.pem")
        
        # Network
        # if os_type == "Windows":
        #     context.load_cert_chain(certfile="cryptographic_material\\server_malicious_root_ca_certificate_pi_client.pem", keyfile="cryptographic_material\\server_malicious_root_ca_private_key_pi_client.pem")
        #     context.load_verify_locations(cafile="cryptographic_material\\root_ca_malicious.pem")
        # elif os_type == "Linux":
        #     context.load_cert_chain(certfile="cryptographic_material/server_malicious_root_ca_certificate_pi_client.pem", keyfile="cryptographic_material/server_malicious_root_ca_private_key_pi_client.pem")
        #     context.load_verify_locations(cafile="cryptographic_material/root_ca_malicious.pem")

        connection_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connection_socket.setblocking(False)
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        _, _, host, port, _ = get_client_network_information()
        data = types.SimpleNamespace(address=(host, port), inb=BYTES_NONE, outb=BYTES_NONE, connected=False, file_name=STR_NONE, data_subtype=INT_NONE, handshake_complete=False)
        
        # Waits for the connection to complete in a non-blocking way, but blocks all other operations
        connection_attempts = 0
        while not data.connected:
            err = connection_socket.connect_ex((host, port)) # Try connecting
            if err == 10056 or err == SUCCESS: # Connection made
                print(f"Connection to {host}:{port} successful.")
                data.connected = True
                break
            elif err == 10035 or err == errno.EINPROGRESS or err == errno.EALREADY: # Non-blocking connection in progress
                print(f"Connection to {host}:{port} in progress ...")
                time.sleep(1)
                continue
            elif err == 10022 or err == errno.EINVAL: # Failed connction (no client at the address)
                print("No device found at the specified address.")
                # Try up to 5 times to connect to the client
                if connection_attempts > 5:
                    print("Connection attempts exceeded. Exiting ...")
                    return None, None, CONNECTION_INITIATE_ERROR
                print("Trying again ...")
                time.sleep(5)
                connection_attempts += 1
                continue
            else:
                print(f"Connection to {host}:{port} failed with error: {errno.errorcode[err]}\n")
                print("Please check the host and port details.")
                return None, None, CONNECTION_INITIATE_ERROR

        # Wrap socket with TSL
        connection_socket = context.wrap_socket(connection_socket, do_handshake_on_connect=False, server_hostname=host) # Wraps the socket with TLS
        print("Initiating TLS handshake ...")
        start_time = time.time()
        while time.time() - start_time < 10:  # Wait 10 seconds until timing out
            try:
                connection_socket.do_handshake() # Can't measure the performance of this due to non-blocking nature
                # do_tls_handshake_stats = measure_operation(process, connection_socket.do_handshake)
                data.outb = HANDSHAKE_COMPLETE
                break
            except ssl.SSLWantReadError:
                # print("SSLWantReadError during handshake.")
                continue
            except ssl.SSLWantWriteError:
                print("SSLWantWriteError during handshake.")
            except ssl.SSLError as e:
                print(f"SSLError during handshake: {e}")
                return None, None, ERROR
            except Exception as e:
                print(f"An unexpected error occurred during handshake: {e}")
                return None, None, ERROR
        
        # Register the connection with the selector for read and write events
        selector.register(connection_socket, events, data=data)
        print("Socket registered.")

        print("Waiting for TLS handshake ...")
        ret_val = wait_for_TLS_handshake(connection_socket, selector)
        if ret_val != SUCCESS:
            print("Error during TLS handshake.")
            return None, None, ERROR
        print("TLS handshake successful.")

        return selector, connection_socket, SUCCESS
    
    except Exception as e:
        print(f"An error occurred: {e}")
        _ = close_connection(connection_socket, selector)
        return None, None, CONNECTION_INITIATE_ERROR