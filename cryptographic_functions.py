# HEADER FILE
# Common cryphotgraphic functions for both the server and client

# Libraries
import typing
import random
from constants import *
from Crypto.Cipher import AES

# Encryption
def payload_encryption(payload: bytes, encryption_key: bytes) -> typing.Tuple[bytes, bytes, bytes, int]:
    try:
        if ENCRYPTION_ALGORITHM == 'none' and SECURITY == 0:
            nonce = random.randbytes(NONCE_LENGTH)
            tag = random.randbytes(TAG_LENGTH)
            return nonce, payload, tag, SUCCESS
        elif ENCRYPTION_ALGORITHM == 'aes_128' or ENCRYPTION_ALGORITHM == 'aes_256':
            encryption_cipher = AES.new(encryption_key, AES.MODE_GCM)
            nonce = encryption_cipher.nonce
            encrypted_payload, tag = encryption_cipher.encrypt_and_digest(payload)
            return nonce, encrypted_payload, tag, SUCCESS
            
    except Exception as e:
        print(f"An error occurred during payload encryption: {e}")
        return BYTES_NONE, BYTES_NONE, BYTES_NONE, ERROR

# Decryption
def payload_decryption(payload: bytes, nonce: bytes, tag: bytes, encryption_key: bytes) -> typing.Tuple[bytes, int]:
    try:
        if ENCRYPTION_ALGORITHM == 'none' and SECURITY == 0:
            return payload, SUCCESS
        elif ENCRYPTION_ALGORITHM == 'aes_128' or ENCRYPTION_ALGORITHM == 'aes_256':
            decryption_cipher = AES.new(encryption_key, AES.MODE_GCM, nonce=nonce)
            decrypted_payload = decryption_cipher.decrypt_and_verify(payload, tag)
            return decrypted_payload, SUCCESS
            
    except Exception as e:
        print(f"An error occurred during payload encryption: {e}")
        return BYTES_NONE, ERROR