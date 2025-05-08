# HEADER FILE
# Common cryptographic functions for both the server and client

# Libraries#
from constants import *

import re

import hashlib

from Crypto.Cipher import AES

from cryptography.hazmat.primitives.asymmetric import ed25519

from cryptography.exceptions import InvalidSignature


import typing
import types
import ssl
import os
import sqlite3
import random
import selectors

# Encryption
def payload_encryption(payload: bytes, encryption_key: bytes) -> typing.Tuple[bytes, bytes, bytes, int]:
    try:
        #print("Encrypting payload ...")

        # print(f"Encrypting: {payload}")
        # print (f"Using encryption key: {encryption_key}")
        
        if re.search(r'\baes', ENCRYPTION_ALGORITHM): # AES
            print("Using AES algorithm.")
            encryption_cipher = AES.new(encryption_key, AES.MODE_GCM)
            nonce = encryption_cipher.nonce
            encrypted_payload, tag = encryption_cipher.encrypt_and_digest(payload)

        # print(f"Encrypted payload: {encrypted_payload}")
        
        #print("Payload encrypted.")
        return nonce, encrypted_payload, tag, SUCCESS
            
    except Exception as e:
        print(f"An error occurred during payload encryption: {e}")
        return BYTES_NONE, BYTES_NONE, BYTES_NONE, ERROR

# Decryption
def payload_decryption(payload: bytes, nonce: bytes, tag: bytes, encryption_key: bytes) -> typing.Tuple[bytes, int]:
    try:
        #print("Decrypting payload ...")

        # print(f"Decrypting: {payload}")
        # print (f"Using encryption key: {encryption_key}")
        
        if re.search(r'\baes', ENCRYPTION_ALGORITHM): # AES
            print("Using AES algorithm.")
            decryption_cipher = AES.new(encryption_key, AES.MODE_GCM, nonce=nonce)
            decrypted_payload = decryption_cipher.decrypt_and_verify(payload, tag)

        # print(f"Decrypted payload: {decrypted_payload}")

        #print("Payload decrypted.")
        return decrypted_payload, SUCCESS
            
    except Exception as e:
        print(f"An error occurred during payload decryption: {e}")
        return BYTES_NONE, ERROR

# Generate hash
def generate_hash(file_data: bytes) -> typing.Tuple[bytes, int]:
    try:
        #print("Generating hash ...")

        if HASHING_ALGORITHM == 'sha-256': # SHA-256
            print("Using SHA-256 hashing algorithm.")
            update_file_hash = str.encode(hashlib.sha256(file_data).hexdigest()) # Creates hash of the update file
        elif HASHING_ALGORITHM == 'sha-384':
            print("Using SHA-384 hashing algorithm.")
            update_file_hash = str.encode(hashlib.sha384(file_data).hexdigest())
        elif HASHING_ALGORITHM == 'sha-512':
            print("Using SHA-512 hashing algorithm.")
            update_file_hash = str.encode(hashlib.sha512(file_data).hexdigest())

        #print("Hash generated.")

        # print(f"Generated {HASHING_ALGORITHM} hash: {update_file_hash}")

        return update_file_hash, SUCCESS
    
    except Exception as e:
        print(f"An error occurred during hash verification: {e}")
        return BYTES_NONE, ERROR

# Generate signature
def generate_signature(payload: bytes, private_key_bytes: bytes) -> typing.Tuple[bytes, int]:
    try:
        #print("Generating signature ...")

        if SIGNATURE_ALGORITHM == 'ed25519':
            print("Using Ed25519 signature algorithm.")
            private_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_key_bytes)
            signature = private_key.sign(payload)

        # print(f"Generated signature: {signature}")

        # print("Signature generated.")
        payload += signature

        return payload, SUCCESS
    
    except Exception as e:
        print(f"An error occurred during signature verification: {e}")
        return BYTES_NONE, ERROR

def get_signature_size() -> int:
    if SIGNATURE_ALGORITHM == 'ed25519':
        return ED25591_SIGNATURE_SIZE
    elif SIGNATURE_ALGORITHM == 'rsa':
        # Add logic to get RSA signature size if needed
        return ERROR
    elif SIGNATURE_ALGORITHM == 'ecdsa':
        # Add logic to get ECDSA signature size if needed
        return ERROR
    
# Verify hash
def verify_hash(payload: bytes, file_name_length: int, payload_length: int) -> typing.Tuple[bytes, int]:
    try:
        #print("Verifying hash ...")

        signature_size = get_signature_size()
        data_inb = payload[file_name_length:payload_length - HASH_SIZE - signature_size]
        update_file_hash = (payload[payload_length - HASH_SIZE - signature_size:payload_length - signature_size]).decode()

        if HASHING_ALGORITHM == 'sha-256': # SHA-256
            print("Using SHA-256 hashing algorithm.")
            generated_hash = hashlib.sha256(data_inb).hexdigest() # Verify hash of the update file
        elif HASHING_ALGORITHM == 'sha-384':
            print("Using SHA-384 hashing algorithm.")
            generated_hash = hashlib.sha384(data_inb).hexdigest()
        elif HASHING_ALGORITHM == 'sha-512':
            print("Using SHA-512 hashing algorithm.")
            generated_hash = hashlib.sha512(data_inb).hexdigest()
        

        # print(f"Hash received: {update_file_hash}")
        # print(f"Hash generated: {generated_hash}")

        if update_file_hash != generated_hash:
            #print("Hash mismatch. Payload not valid.")
            return BYTES_NONE, INVALID_PAYLOAD_ERROR
        
        # print("Hash verified.")
        return data_inb, SUCCESS
    
    except Exception as e:
        print(f"An error occurred during hash verification: {e}")
        return ERROR

# Verify signature
def verify_signature(public_key_bytes: bytes, payload: bytes, payload_length: int) -> int:
    try:
        #print("Verifying signature ...")
        
        signature_size = get_signature_size()
        signed_payload = payload[:payload_length - signature_size] # Extracts the bytes that were originally signed
        signature = payload[payload_length - signature_size:payload_length]

        # print(f"Signature: {signature}")
        # print(f"Key: {public_key}")

        if SIGNATURE_ALGORITHM == 'ed25519':
            print("Using Ed25519 signature algorithm.")
            public_key = ed25519.Ed25519PublicKey.from_public_bytes(public_key_bytes)
            public_key.verify(signature, signed_payload)

        #print("Signature verified.")
        return SUCCESS

    except InvalidSignature:
        #print("Signature is not valid.")
        return SIGNATURE_INVALID_ERROR
    
    except Exception as e:
        print(f"An error occurred during signature verification: {e}")
        return ERROR

# Wrapper to create TLS contexts
def create_context(mode: str, port: int) -> typing.Tuple[ssl.SSLContext, int]:
    try:
        if mode == 'server':
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER) # Auto-negotiates highgest available protocol

        elif mode == 'client':
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT) # Auto-negotiates highgest available protocol
            context.check_hostname = True
        else:
            print("Invalid mode. Use 'server' or 'client'.")
            return None, ERROR
        
        context.minimum_version = ssl.TLSVersion.TLSv1_3 # Enforces TLS 1.3 ciphers
        context.verify_mode = ssl.CERT_REQUIRED
        
        context, ret_val = load_cryptographic_data(context, port)
        if ret_val == ERROR:
            print("Error loading cryptographic data.")
            return None, ERROR

        return context, SUCCESS

    except Exception as e:
        print(f"An error occurred: {e}")
        return None, ERROR

def load_cryptographic_data(context: ssl.SSLContext, port: int) -> typing.Tuple[ssl.SSLContext, int]:
    try:
        if port == SERVER_PORT:
            database = os.getenv("SERVER_DATABASE")
            query = "SELECT server_private_key, server_certificate, root_ca FROM cryptographic_data WHERE cryptographic_entry_id = 1"
        elif port == WINDOWS_PORT:
            database = os.getenv("WINDOWS_CLIENT_DATABASE")
            query = "SELECT windows_client_private_key, windows_client_certificate, root_ca FROM cryptographic_data WHERE cryptographic_entry_id = 1"
        elif port == LINUX_PORT:
            database = os.getenv("LINUX_CLIENT_DATABASE")
            query = "SELECT linux_client_private_key, linux_client_certificate, root_ca FROM cryptographic_data WHERE cryptographic_entry_id = 1"

        db_connection = sqlite3.connect(database)
        cursor = db_connection.cursor()
        connection_private_key, connection_certificate, root_ca = (cursor.execute(query)).fetchone()
        connection_private_key = connection_private_key.decode()
        connection_certificate = connection_certificate.decode()
        root_ca = root_ca.decode()
        db_connection.close()

        # Work around for having hardcoded certificate paths
        # Allows server and clients to use their respective certificates
        with open("connection_certificate.pem", "w", newline='') as connection_certificate_temp, open("connection_private_key.pem", "w", newline='') as connection_private_key_temp, open("root_ca.pem", "w", newline='') as root_ca_temp:
            connection_certificate_temp.write(connection_certificate)
            connection_private_key_temp.write(connection_private_key)
            root_ca_temp.write(root_ca)
        context.load_cert_chain(certfile="connection_certificate.pem", keyfile="connection_private_key.pem")
        context.load_verify_locations(cafile="root_ca.pem")
        #print("Certificates loaded.")
        #print("Removing temporary files ...")
        os.remove("connection_certificate.pem")
        os.remove("connection_private_key.pem")
        os.remove("root_ca.pem")
        #print("Temporary files removed.")

        return context, SUCCESS

    except Exception as e:
        print(f"An error occurred while loading cryptographic data: {e}")
        return None, ERROR

# Implemented as a workaround for the client going into receive mode after the handshake is complete instead of write mode
def wait_for_TLS_handshake(connection_socket: ssl.SSLSocket, selector: selectors.SelectSelector) -> int:
    try:
        # Waits for TLS handshake confirmation to be sent
        while True:
            # Get list of events from the selector
            events = selector.select(timeout=1) # Refreshes events every second
            for key, mask in events:
                if key.data == "listening_socket":
                    continue
                connection_socket = key.fileobj
                if key.data.outb != HANDSHAKE_COMPLETE:
                    # Read events
                    if mask & selectors.EVENT_READ:                        
                        try:
                            key.data.inb = connection_socket.recv(STATUS_CODE_SIZE)
                            if key.data.inb == HANDSHAKE_COMPLETE:
                                #print("TLS handshake complete.")
                                key.data.outb = HANDSHAKE_FINISHED
                            key.data.handshake_complete = True
                        except ssl.SSLWantReadError:
                            continue
                        except ssl.SSLWantWriteError:
                            continue
                if mask & selectors.EVENT_WRITE:
                    if key.data.outb:
                        while key.data.outb:
                            sent = connection_socket.send(key.data.outb)
                            key.data.outb = key.data.outb[sent:]
                        key.data.outb = BYTES_NONE
                        #print("Data sent.")
                        break
            if key.data.handshake_complete == True:
                key.data.inb = BYTES_NONE
                key.data.outb = BYTES_NONE
                break
        return SUCCESS
    
    except Exception as e:
        print(f"An error occurred during TLS handshake: {e}")
        return ERROR