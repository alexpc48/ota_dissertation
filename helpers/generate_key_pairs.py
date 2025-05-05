import os
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

# Create the output directory if it doesn't exist
output_dir = os.path.join("..", "cryptographic_material")
os.makedirs(output_dir, exist_ok=True)

# Helper function to save raw key bytes to a .txt file
def save_key_to_file(filename, key_bytes):
    with open(os.path.join(output_dir, filename), 'wb') as f:
        f.write(key_bytes)

# Generate keys
server_eddsa_private_key = Ed25519PrivateKey.generate()
server_eddsa_public_key = server_eddsa_private_key.public_key()
windows_eddsa_private_key = Ed25519PrivateKey.generate()
windows_eddsa_public_key = windows_eddsa_private_key.public_key()
linux_eddsa_private_key = Ed25519PrivateKey.generate()
linux_eddsa_public_key = linux_eddsa_private_key.public_key()

# Serialize to raw bytes
server_private_bytes = server_eddsa_private_key.private_bytes_raw()
server_public_bytes = server_eddsa_public_key.public_bytes_raw()
windows_private_bytes = windows_eddsa_private_key.private_bytes_raw()
windows_public_bytes = windows_eddsa_public_key.public_bytes_raw()
linux_private_bytes = linux_eddsa_private_key.private_bytes_raw()
linux_public_bytes = linux_eddsa_public_key.public_bytes_raw()

# Save raw bytes directly to .txt files
save_key_to_file("server_private.txt", server_private_bytes)
save_key_to_file("server_public.txt", server_public_bytes)
save_key_to_file("windows_private.txt", windows_private_bytes)
save_key_to_file("windows_public.txt", windows_public_bytes)
save_key_to_file("linux_private.txt", linux_private_bytes)
save_key_to_file("linux_public.txt", linux_public_bytes)
