# HEADER FILE
# Common cryptographic functions for both the server and client

# Libraries#
from constants import *

import re
import hashlib
from Crypto.Cipher import AES
from cryptography.hazmat.primitives.asymmetric import ed25519
import typing
import random

# Encryption
def payload_encryption(payload: bytes, encryption_key: bytes) -> typing.Tuple[bytes, bytes, bytes, int]:
    try:
        print("Encrypting payload ...")
        if SECURITY_MODE == 0: # Testing purpose, no encryption
            # Generate random nonce and tag as fillers (not secure)
            nonce = random.randbytes(NONCE_LENGTH)
            tag = random.randbytes(TAG_LENGTH)
            encrypted_payload = payload
            print("No encryption needed.")
        
        elif re.search(r'\baes', ENCRYPTION_ALGORITHM) and SECURITY_MODE == 1: # AES
            print("Using AES encryption.")
            encryption_cipher = AES.new(encryption_key, AES.MODE_GCM)
            nonce = encryption_cipher.nonce
            encrypted_payload, tag = encryption_cipher.encrypt_and_digest(payload)
        
        print("Payload encrypted.")
        # encrypted_payload += b'malicious_code' # Makes the authentication fail for the encrypted payload as tag was generated on the original encrypted payload
        return nonce, encrypted_payload, tag, SUCCESS
            
    except Exception as e:
        print(f"An error occurred during payload encryption: {e}")
        return BYTES_NONE, BYTES_NONE, BYTES_NONE, ERROR

# Decryption
def payload_decryption(payload: bytes, nonce: bytes, tag: bytes, encryption_key: bytes) -> typing.Tuple[bytes, int]:
    try:
        print("Decrypting payload ...")
        if SECURITY_MODE == 0:
            decrypted_payload = payload
            print("No decryption needed.")
        
        elif re.search(r'\baes', ENCRYPTION_ALGORITHM) and SECURITY_MODE == 1: # AES
            print("Using AES decryption.")
            decryption_cipher = AES.new(encryption_key, AES.MODE_GCM, nonce=nonce)
            decrypted_payload = decryption_cipher.decrypt_and_verify(payload, tag)

        print("Payload decrypted.")
        return decrypted_payload, SUCCESS
            
    except Exception as e:
        print(f"An error occurred during payload decryption: {e}")
        return BYTES_NONE, ERROR

# Generate hash
def generate_hash(file_data: bytes) -> typing.Tuple[bytes, int]:
    try:
        print("Generating hash ...")
        if SECURITY_MODE == 0:
            print("No hash generation needed.")
            return BYTES_NONE, SUCCESS
        
        update_file_hash = str.encode(hashlib.sha256(file_data).hexdigest()) # Creates hash of the update file
        print(f"Update file hash: {update_file_hash}")
        # data_to_send = data_to_send + b'malicious_code' # Makes the authentication fail for the unencrypted payload as the hashes will not match up

        print("Hash generated.")
        return update_file_hash, SUCCESS
    
    except Exception as e:
        print(f"An error occurred during hash verification: {e}")
        return BYTES_NONE, ERROR

# Generate signature
def generate_signature(payload: bytes, private_key_bytes: bytes) -> typing.Tuple[bytes, int]:
    try:
        print("Generating signature ...")
        if SECURITY_MODE == 0:
            print("No signature verification needed.")
            return payload, SUCCESS
        
        private_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_key_bytes)
        signature = private_key.sign(payload)
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
        return 0
    elif SIGNATURE_ALGORITHM == 'ecdsa':
        # Add logic to get ECDSA signature size if needed
        return 0
    
# Verify hash
def verify_hash(payload: bytes, file_name_length: int, payload_length: int) -> typing.Tuple[bytes, int]:
    try:
        print("Verifying hash ...")
        if SECURITY_MODE == 0:
            print("No hash verification needed.")
            data_inb = payload[file_name_length:payload_length]
            return data_inb, SUCCESS

        signature_size = get_signature_size()
        data_inb = payload[file_name_length:payload_length - HASH_SIZE - signature_size]
        # print(f"Payload: {data_inb}")
        update_file_hash = (payload[payload_length - HASH_SIZE - signature_size:payload_length - signature_size]).decode()
        print(f"Received hash: {update_file_hash}")
        generated_hash = hashlib.sha256(data_inb).hexdigest() # Verify hash of the update file
        print(f"Generated hash: {generated_hash}")

        if update_file_hash != generated_hash:
            print("Hash mismatch. Payload not valid.")
            return BYTES_NONE, INVALID_PAYLOAD_ERROR
        
        print("Hash verified.")
        return data_inb, SUCCESS
    
    except Exception as e:
        print(f"An error occurred during hash verification: {e}")
        return ERROR

# Verify signature
def verify_signature(public_key: bytes, payload: bytes, payload_length: int) -> int:
    try:
        print("Verifying signature ...")
        if SECURITY_MODE == 0:
            print("No signature verification needed.")
            return SUCCESS
        
        signature_size = get_signature_size()
        signed_payload = payload[:payload_length - signature_size] # Extracts the bytes that were originally signed
        signature = payload[payload_length - signature_size:payload_length]
        print(f"Signature: {signature}")

        public_key = ed25519.Ed25519PublicKey.from_public_bytes(public_key)
        public_key.verify(signature, signed_payload)

        print("Signature verified.")
        return SUCCESS

    except ed25519.InvalidSignature:
        print("Signature is not valid.")
        return SIGNATURE_INVALID_ERROR
    
    except Exception as e:
        print(f"An error occurred during signature verification: {e}")
        return ERROR