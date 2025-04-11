# HEADER FILE
# Common cryphotgraphic functions for both the server and client

# Libraries
import typing
from constants import *
from Crypto.Cipher import AES


# Encryption
def payload_encryption(payload: bytes, algorithm: str) -> typing.Tuple[bytes, bytes, bytes, int]:
    try:
        match algorithm:
            case 'NONE': # DEUBG ONLY
                return BYTES_NONE, payload, BYTES_NONE, SUCCESS
            case 'AES_128':
                return aes_128_encrypt(payload)
            case 'AES_256':
                return aes_256_encrypt(payload)
            case _:
                print(f"Unknown algorithm: {algorithm}")
                return BYTES_NONE, BYTES_NONE, BYTES_NONE, ERROR
            
    except Exception as e:
        print(f"An error occurred during payload encryption: {e}")
        return BYTES_NONE, BYTES_NONE, BYTES_NONE, ERROR

def aes_128_encrypt(payload: bytes) -> typing.Tuple[bytes, bytes, bytes, int]:
    aes_key = None
    encryption_cipher = AES.new(aes_key, AES.MODE_GCM)
    nonce = encryption_cipher.nonce
    encrypted_payload, tag = encryption_cipher.encrypt_and_digest(payload)
    return nonce, encrypted_payload, tag, SUCCESS

def aes_256_encrypt(payload: bytes) -> typing.Tuple[bytes, bytes, bytes, int]:
    aes_key = None
    encryption_cipher = AES.new(aes_key, AES.MODE_GCM)
    nonce = encryption_cipher.nonce
    encrypted_payload, tag = encryption_cipher.encrypt_and_digest(payload)
    return nonce, encrypted_payload, tag, SUCCESS

# Decryption
def payload_decryption(payload: bytes, nonce: bytes, tag: bytes, algorithm: str) -> typing.Tuple[bytes, int]:
    try:
        match algorithm:
            case 'NONE': # DEUBG ONLY
                return payload, SUCCESS
            case 'AES_128':
                return aes_128_decrypt(payload, nonce, tag)
            case 'AES_256':
                return aes_256_decrypt(payload, nonce, tag)
            case _:
                print(f"Unknown algorithm: {algorithm}")
                return BYTES_NONE, ERROR
            
    except Exception as e:
        print(f"An error occurred during payload encryption: {e}")
        return BYTES_NONE, ERROR
    

def aes_128_decrypt(payload: bytes, nonce: bytes, tag: bytes) -> typing.Tuple[bytes, int]:
    aes_key = None
    decryption_cipher = AES.new(aes_key, AES.MODE_GCM, nonce=nonce)
    decrypted_payload = decryption_cipher.decrypt_and_verify(payload, tag)
    return decrypted_payload, SUCCESS

def aes_256_decrypt(payload: bytes, nonce: bytes, tag: bytes) -> typing.Tuple[bytes, int]:
    aes_key = None
    decryption_cipher = AES.new(aes_key, AES.MODE_GCM, nonce=nonce)
    decrypted_payload = decryption_cipher.decrypt_and_verify(payload, tag)
    return decrypted_payload, SUCCESS
