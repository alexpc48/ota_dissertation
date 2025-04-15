import socket
import ssl
import select
import threading
import os
import subprocess
import time

CERT_FILE = 'server.crt'
KEY_FILE = 'server.key'

def generate_self_signed_certificate():
    if not os.path.exists(KEY_FILE) or not os.path.exists(CERT_FILE):
        print("Generating self-signed certificates for testing...")
        try:
            subprocess.run(['D:\\Program Files\\OpenSSL-Win64\\bin\\openssl.exe', 'genrsa', '-out', KEY_FILE, '2048'], check=True)
            subprocess.run(['D:\\Program Files\\OpenSSL-Win64\\bin\\openssl.exe', 'req', '-new', '-key', KEY_FILE, '-out', 'server.csr', '-subj', '/CN=localhost'], check=True)
            subprocess.run(['D:\\Program Files\\OpenSSL-Win64\\bin\\openssl.exe', 'x509', '-req', '-days', '365', '-in', 'server.csr', '-signkey', KEY_FILE, '-out', CERT_FILE], check=True)
            print(f"Certificates generated ({KEY_FILE}, {CERT_FILE}).")
        except ImportError:
            print("Error: 'openssl' command not found. Please install it or provide your own server.key and server.crt files.")
            exit()
        except subprocess.CalledProcessError as e:
            print(f"Error generating certificates: {e}")
            exit()
    else:
        print(f"Using existing {KEY_FILE} and {CERT_FILE} files.")

def non_blocking_server():
    server_address = ('localhost', 12345)
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setblocking(False)

    try:
        server_socket.bind(server_address)
        server_socket.listen(5)
        print(f"Non-blocking server listening on {server_address}")

        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(CERT_FILE, KEY_FILE)

        inputs = [server_socket]
        outputs = []
        connections = {}
        ssl_connections = {}

        while inputs:
            readable, writable, exceptional = select.select(inputs, outputs, inputs)

            for s in readable:
                if s is server_socket:
                    try:
                        conn, addr = server_socket.accept()
                        conn.setblocking(False)
                        ssl_conn = context.wrap_socket(conn, server_side=True)
                        inputs.append(ssl_conn)
                        connections[ssl_conn] = addr
                        ssl_connections[conn] = ssl_conn
                        print(f"Accepted non-blocking connection from {addr}")
                    except ssl.SSLError as e:
                        print(f"SSL error during accept: {e}")
                        if conn in inputs:
                            inputs.remove(conn)
                        conn.close()
                    except BlockingIOError:
                        pass
                else:
                    try:
                        data = s.recv(1024)
                        if data:
                            print(f"Received from {connections[s]}: {data.decode('utf-8')}")
                            response = f"Server received: {data.decode('utf-8')}".encode('utf-8')
                            outputs.append(s)
                            s.send(response)
                        else:
                            print(f"Closing non-blocking connection from {connections[s]}")
                            if s in outputs:
                                outputs.remove(s)
                            inputs.remove(s)
                            s.close()
                            del connections[s]
                            for original_sock, ssl_sock in list(ssl_connections.items()):
                                if ssl_sock is s:
                                    del ssl_connections[original_sock]
                                    break
                    except ssl.SSLWantReadError:
                        pass
                    except ssl.SSLWantWriteError:
                        if s not in outputs:
                            outputs.append(s)
                    except ssl.SSLError as e:
                        print(f"SSL error with {connections[s]}: {e}")
                        if s in outputs:
                            outputs.remove(s)
                        inputs.remove(s)
                        s.close()
                        del connections[s]
                        for original_sock, ssl_sock in list(ssl_connections.items()):
                            if ssl_sock is s:
                                del ssl_connections[original_sock]
                                break
                    except BlockingIOError:
                        pass
                    except ConnectionResetError:
                        print(f"Connection reset by {connections[s]}")
                        if s in outputs:
                            outputs.remove(s)
                        inputs.remove(s)
                        s.close()
                        del connections[s]
                        for original_sock, ssl_sock in list(ssl_connections.items()):
                            if ssl_sock is s:
                                del ssl_connections[original_sock]
                                break
                    except Exception as e:
                        print(f"Error handling connection from {connections[s]}: {e}")
                        if s in outputs:
                            outputs.remove(s)
                        inputs.remove(s)
                        s.close()
                        del connections[s]
                        for original_sock, ssl_sock in list(ssl_connections.items()):
                            if ssl_sock is s:
                                del ssl_connections[original_sock]
                                break

            for s in exceptional:
                print(f"Handling exceptional condition for {connections.get(s, 'unknown')}")
                inputs.remove(s)
                if s in outputs:
                    outputs.remove(s)
                s.close()
                if s in connections:
                    del connections[s]
                    for original_sock, ssl_sock in list(ssl_connections.items()):
                        if ssl_sock is s:
                            del ssl_connections[original_sock]
                            break

    except socket.error as e:
        print(f"Socket error: {e}")
    finally:
        server_socket.close()

def non_blocking_client():
    server_address = ('localhost', 12345)
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.setblocking(False)

    try:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.load_verify_locations(CERT_FILE)
        context.check_hostname = False

        try:
            client_socket.connect(server_address)
        except BlockingIOError:
            pass

        ssl_client_socket = context.wrap_socket(client_socket, server_hostname=server_address[0])
        inputs = [ssl_client_socket]
        outputs = [ssl_client_socket]
        message = "Hello from the non-blocking client!".encode('utf-8')
        sent = False
        received_data = b""
        handshake_done = False

        while inputs:
            readable, writable, exceptional = select.select(inputs, outputs, inputs)

            if not handshake_done:
                if ssl_client_socket in readable or ssl_client_socket in writable:
                    try:
                        ssl_client_socket.do_handshake()
                        handshake_done = True
                        print("TLS handshake complete on client.")
                        if ssl_client_socket in outputs and not sent:
                            try:
                                bytes_sent = ssl_client_socket.send(message)
                                print(f"Sent {bytes_sent} bytes: {message.decode('utf-8')}")
                                sent = True
                                if ssl_client_socket in outputs:
                                    outputs.remove(ssl_client_socket)
                            except (ssl.SSLWantWriteError, BlockingIOError):
                                pass
                            except ssl.SSLError as e:
                                print(f"SSL error during initial send: {e}")
                                break
                            except ConnectionError as e:
                                print(f"Connection error during initial send: {e}")
                                break
                    except ssl.SSLWantReadError:
                        pass
                    except ssl.SSLWantWriteError:
                        pass
                    except ssl.SSLError as e:
                        print(f"SSL error during handshake: {e}")
                        break
                    except Exception as e:
                        print(f"Error during handshake: {e}")
                        break

            if handshake_done:
                for s in readable:
                    try:
                        data = s.recv(1024)
                        if data:
                            received_data += data
                            print(f"Received from server: {received_data.decode('utf-8')}")
                            inputs.remove(s)
                        else:
                            print("Connection closed by server.")
                            inputs.remove(s)
                            if s in outputs:
                                outputs.remove(s)
                            s.close()
                    except (ssl.SSLWantReadError, BlockingIOError):
                        pass
                    except ssl.SSLError as e:
                        print(f"SSL error during recv: {e}")
                        inputs.remove(s)
                        if s in outputs:
                            outputs.remove(s)
                        s.close()
                    except ConnectionResetError:
                        print("Connection reset by server.")
                        inputs.remove(s)
                        if s in outputs:
                            outputs.remove(s)
                        s.close()
                    except Exception as e:
                        print(f"Error during recv: {e}")
                        inputs.remove(s)
                        if s in outputs:
                            outputs.remove(s)
                        s.close()

                for s in writable:
                    if not sent and handshake_done:
                        try:
                            bytes_sent = s.send(message)
                            print(f"Sent {bytes_sent} bytes: {message.decode('utf-8')}")
                            sent = True
                            if s in outputs:
                                outputs.remove(s)
                        except (ssl.SSLWantWriteError, BlockingIOError):
                            pass
                        except ssl.SSLError as e:
                            print(f"SSL error during send: {e}")
                            if s in outputs:
                                outputs.remove(s)
                            if s in inputs:
                                inputs.remove(s)
                            s.close()
                        except ConnectionError as e:
                            print(f"Connection error during send: {e}")
                            if s in outputs:
                                outputs.remove(s)
                            if s in inputs:
                                inputs.remove(s)
                            s.close()

                for s in exceptional:
                    print("Handling exceptional condition")
                    inputs.remove(s)
                    if s in outputs:
                        outputs.remove(s)
                    s.close()

                if sent and not inputs:
                    break

    except socket.error as e:
        print(f"Socket error: {e}")
    except ssl.SSLError as e:
        print(f"SSL error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        client_socket.close()

if __name__ == "__main__":
    generate_self_signed_certificate()

    server_thread = threading.Thread(target=non_blocking_server)
    server_thread.daemon = True
    server_thread.start()

    time.sleep(0.1)  # Give the server a moment to start

    non_blocking_client()