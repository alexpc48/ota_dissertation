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
        
        if re.search(r'\baes', ENCRYPTION_ALGORITHM): # AES
            print("Using AES encryption.")
            encryption_cipher = AES.new(encryption_key, AES.MODE_GCM)
            nonce = encryption_cipher.nonce
            encrypted_payload, tag = encryption_cipher.encrypt_and_digest(payload)
        
        print("Payload encrypted.")
        return nonce, encrypted_payload, tag, SUCCESS
            
    except Exception as e:
        print(f"An error occurred during payload encryption: {e}")
        return BYTES_NONE, BYTES_NONE, BYTES_NONE, ERROR

# Decryption
def payload_decryption(payload: bytes, nonce: bytes, tag: bytes, encryption_key: bytes) -> typing.Tuple[bytes, int]:
    try:
        print("Decrypting payload ...")
        
        if re.search(r'\baes', ENCRYPTION_ALGORITHM): # AES
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

        update_file_hash = str.encode(hashlib.sha256(file_data).hexdigest()) # Creates hash of the update file
        print("Hash generated.")

        return update_file_hash, SUCCESS
    
    except Exception as e:
        print(f"An error occurred during hash verification: {e}")
        return BYTES_NONE, ERROR

# Generate signature
def generate_signature(payload: bytes, private_key_bytes: bytes) -> typing.Tuple[bytes, int]:
    try:
        print("Generating signature ...")
        
        private_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_key_bytes)
        signature = private_key.sign(payload)
        print("Signature generated.")
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
        print("Verifying hash ...")

        signature_size = get_signature_size()
        data_inb = payload[file_name_length:payload_length - HASH_SIZE - signature_size]
        update_file_hash = (payload[payload_length - HASH_SIZE - signature_size:payload_length - signature_size]).decode()
        generated_hash = hashlib.sha256(data_inb).hexdigest() # Verify hash of the update file

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
        
        signature_size = get_signature_size()
        signed_payload = payload[:payload_length - signature_size] # Extracts the bytes that were originally signed
        signature = payload[payload_length - signature_size:payload_length]

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