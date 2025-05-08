# Constants
# Error codes
SUCCESS = 0
ERROR = 1
CONNECTION_ACCEPT_ERROR = 2
CONNECTION_INITIATE_ERROR = 3
CONNECTION_CLOSE_ERROR = 4
LISTENING_SOCKET_CREATION_ERROR = 5
CONNECTION_SERVICE_ERROR = 6
KEYBOARD_INTERRUPT = 7
LISTENING_ERROR = 8
WAITING_ERROR = 9
CHECK_UPDATE_ERROR = 10
DOWNLOAD_UPDATE_ERROR = 11
CLIENT_NOT_UPDATE_READY_ERROR = 12
UPDATE_STATUS_REPEAT_ERROR = 13
NO_UPDATE_ERROR = 14
QUEUED_UPDATE_ERROR = 15
UPDATE_INSTALL_ERROR = 16
UPDATE_NOT_AVALIABLE_ERROR = 17
INCOMPLETE_PAYLOAD_ERROR = 18
PAYLOAD_CREATION_ERROR = 19
PAYLOAD_ENCRYPTION_ERROR = 20
PAYLOAD_RECEIVE_ERROR = 21
PAYLOAD_DECRYPTION_ERROR = 22
INVALID_PAYLOAD_ERROR = 23
SIGNATURE_INVALID_ERROR = 24
TIMEOUT_ERROR = 25
CLIENT_UP_TO_DATE_ERROR = 26
NO_ROLLBACK_UPDATES_ERROR = 27

# Variables
BYTES_TO_READ = 1024
# Generated using os.urandom(256)
EOF_BYTE = b'\xd3\xd5]\xab9\xbe\xed\x0b{\x90\x83,\xb4\r\xc2\xfbPi\\u\x85\xdf\x9cC\xa5\x07\xed\xf2\xda\x9d\xe0\x82=\x0f\xaed\x9c\xe5M\xc4\xa8d8\xaeL\x9dM\xf8\xadBw\x8a\xe6\n\xcek\xef\x96\xae:zA\xbd;\x90E\x93\x0c\x83/\x8b`\xd7\xd6\xc6\xeb\x8fb(@\x9b\xe5\xdap\xdb\xb5@4\x95\xeaq\xbf\xd2G*\xb2\x0c\xb4\xa3Cz\xc7\xbc\x95>\xf8(A\x8e\x10\xfd\xc2\xe3\xbeRe%\x97\x92\xdbK\xe4n\xd4\xbc\xedK\xa8_\x8eX8\xcf\x0e\xc0\xa9!\x9b@v\xe8-\x82\\\x02\xf7\xa1|\x97P?\xcdY\xef\xdc.tg8|U\xb9\xf2a\xa6\x11\x8f\x7f\xa7\x7fsk\x16\xf8@\x11S\x98fj\xfc_\x8c\xc8w\xc1\xefN\x80\xaa\xdb\x9a[\x93\xcb-\xd0\x07?\xd5\xc5F\xa6\x9e\\\x8e\xf1\xfa\x83)\x13\n\xad\x98\xbc\x86\xa5.\xfa\xe9\xae\xb6\x08j\xaf\xb6ko\xd0\xba\xf7@\xce\xc1\xe38A)\x83\xfe\x14F\xd7\xe5\x18Y\x01"p0Zh\x00\xb2\xceG'
UPDATE_CHECK_REQUEST = b'10001'
UPDATE_DOWNLOAD_REQUEST = b'10002'
UPDATE_AVALIABLE = b'10003'
UPDATE_NOT_AVALIABLE = b'10004'
RECEIVED_FILE_CHECK_REQUEST = b'10005' # Did the client receive the file?
FILE_RECEIVED_ACK = b'10006'
EOF_TAG_BYTE = b'EOF'
UPDATE_READINESS_REQUEST = b'10007'
UPDATE_READY = b'10008'
UPDATE_NOT_READY = b'10009'
# Generated using os.urandom(256)
FILE_HEADER_SECTION_END = b'\xf5n\x882\xb0\xac\xd8\xe9\xf2\x8a\xe6e\xf2F{\xe3?e\x19c8\x0c\xfa6\xbc*_9-\xa8\x8f\x9c\xf0F\xd09\x8e\x81\x07\xc6\xfa\\\xfeg"\xa8\x93\xb2\xc9\xa8\x94LT\xf52_\xb2\xdb\xcc\xd0498\rE\xce\x13[pmOP\x1f\xc7\xe2{<p,I\xe75ix\x92\x0cM\xfd\x07\x81\xc3\x07Y\xd6\xd3i\xedF=\xc3I\xbb\x8a \x85Q\x8f{\x8d>_N\x89\n\x00\x0f\xe4\xb0`\xc4\x90K\x1d \xe4j\xd7\x9c\x08V\x91\x04\xceQ\xa0\xa2\x1c\x93\xe5s\xdfw\xa3|\x02B\xef@\xbeH_\x8b\xb0\x8b\xd3\x0eE\xde\xb3a\xa7\xd2\x97d\xa1\xa2u\xb0\x8d\xdd\xef&\xbaQ\xe0\xc6\xad4\xfc\xbd\x96\x81\xe7\x10^y\x8a\x81\x93\xf5RaXG\xce\\\xad\x0b5\xc7\x06\xee\xa1\x13\x1d\xee0%\xf9\'K\x1d.\x90\xe5\xaa\x8a\xaf\xfdw\xf4\xf1\xa8+Den#\xa8\xb9\x00C\x7fS\xc9z\x92\xf5d2r\x10\xe8A \x8a\xaf\xca\x0cSe\xf1\x89\xb9Sr'
STR_NONE = ''
INT_NONE = 0
BOOL_NONE = None
BYTES_NONE = b''
UPDATE_READINESS_STATUS_REQUEST = b'10010'
REQUEST = b'10011'
UPDATE_VERSION_REQUEST = b'10012'
UPDATE_VERSION_RESPONSE = b'10013'
RECEIVED_PAYLOAD_ACK_REQUEST = b'10014'
RECEIVED_PAYLOAD_ACK = b'10015'
HEADER_SIZE = 8 # Integer representing number of bytes in the header
DATA_RECEIVED_ACK = b'10016'
STATUS_CODE = 1
DATA = 2
UPDATE_VERSION = 1
UPDATE_FILE = 2
ALL_INFORMATION = 3
PACK_COUNT_BYTES = 16 # Number of bytes in the header (4 integers)
PACK_DATA_COUNT = '!IIII' # 4 Integers in the header
UPDATE_VERSION_PUSH = 4 # A client is pushing their version number to the server
TAG_LENGTH = 16
NONCE_LENGTH = 16 # Standard default is 12 bytes for GCM, but used 16 bytes due to how nonce is generated in the code
ENCRYPTION_ALGORITHM = 'aes_128' # aes_128, aes_256
IDENTIFIER_LENGTH = 36
SECURITY_MODE = 1 # 1 = Secure, 0 = Insecure - Used for demonstration purposes

ED25591_SIGNATURE_SIZE = 64
SIGNATURE_ALGORITHM = 'ed25519' # ed25519

HANDSHAKE_COMPLETE = b'10017'
STATUS_CODE_SIZE = 5
HANDSHAKE_FINISHED = b'10018'
ALL_INFORMATION_REQUEST = b'10019'
UPDATE_INSTALLED = b'10020'
UPDATE_IN_DOWNLOADS = b'10021'
INSTALL_STATUS_REQUEST = b'10022'
INSTALL_LOCATION = 'install_location'

HASH_SIZE = 128 # SHA-256 = 64, SHA-384 = 96, SHA-512 = 128
HASHING_ALGORITHM = 'sha-512' # sha-256, sha-384, sha-512

# Networking constants
SERVER_PORT = 50069
WINDOWS_PORT = 50150
LINUX_PORT = 50097