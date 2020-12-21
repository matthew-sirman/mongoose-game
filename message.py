class Message:
    HEADER_SIZE = 4
    BUFFER_SIZE = 256

    def __init__(self, message=b"", size=-1):
        self.message = message
        self.size = size

        self.__read_left = -1

    @staticmethod
    def new_send_message(message):
        return Message(message, len(message))

    @staticmethod
    def new_recv_message():
        return Message()

    def encode(self):
        n_blocks = self.size // Message.BUFFER_SIZE + 1
        padding_size = (n_blocks * Message.BUFFER_SIZE - self.size - Message.HEADER_SIZE) % Message.BUFFER_SIZE
        return self.size.to_bytes(Message.HEADER_SIZE, "little") + self.message + b"0" * padding_size

    def decode(self, buffer):
        __buff = buffer
        if self.size == -1:
            self.size = int.from_bytes(__buff[:4], "little")
            __buff = __buff[4:]
            self.__read_left = self.size

        if self.__read_left > len(__buff):
            self.message += __buff
            self.__read_left -= len(__buff)

            return False
        else:
            self.message += __buff[:self.__read_left]
            self.__read_left = 0

            return True

    def __str__(self):
        return self.message.decode("utf-8")

    def __repr__(self):
        return self.__str__()
