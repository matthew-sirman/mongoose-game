import socket
from message import Message

IP = "localhost"
PORT = 1234

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((IP, PORT))

message = Message.new_recv_message()

while True:
    buffer = s.recv(1024)
    if message.decode(buffer):
        print(message.message.decode("utf-8"))