# Decode bytes and write it to a new file
import sys

def decode_bytes(input_file, output_file) -> int:
    with open(input_file, 'rb') as file:
        input_data = file.read()
    stripped_data = input_data[25:] # Strips header file and data
    print(stripped_data)  
    with open(output_file, 'wb') as file:
        file.write(stripped_data)
    return 1

if __name__=='__main__':
    input_file, output_file = sys.argv[1], sys.argv[2]
    print(input_file)
    print(output_file)
    decode_bytes(input_file, output_file)
    sys.exit(1)