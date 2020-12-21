import socket
import threading
import select
import time
from message import Message
from instructions import Instruction
from cards import Deck


class Server:
    MAX_CONCURRENT_REQUESTS = 4
    UPDATE_FREQUENCY = 1000
    SEND_RATE = 50

    class Flags:
        SHUTDOWN_SERVER = 1

    def __init__(self, address, verbose=True):
        self.ip, self.port = address

        self.verbose = verbose

        self.sock = self.setup_socket()

        self.__flags = 0

        self.__inst_queue = []

        self.__client_sockets = []
        self.__client_info = {}

        self.__client_send_queue = {}

        self.__game_running = False

        self.__curr_client_id = 0

        self.__decks = []

    def setup_socket(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        s.bind((self.ip, self.port))

        if self.verbose:
            print(f"Set up socket on {self.ip}:{self.port}.")

        return s

    def start_server(self):
        self.sock.listen(Server.MAX_CONCURRENT_REQUESTS)

        if self.verbose:
            print("Starting server...")
            self.__inst_queue.append(lambda: print("Server started successfully."))

        listen_t = threading.Thread(target=self.listen, daemon=True)
        console_t = threading.Thread(target=self.console, daemon=True)

        listen_t.start()
        console_t.start()

        self.run()

        if self.verbose:
            print("Shutting down server...")

        self.sock.close()
        listen_t.join(1)
        console_t.join(0.1)

        if self.verbose:
            print("Server shut down successfully.")

    def run(self):
        while not self.__flags & Server.Flags.SHUTDOWN_SERVER:
            while self.__inst_queue:
                self.__inst_queue.pop(0)()

            self.handle_client_channels()

    def listen(self):
        while not self.__flags & Server.Flags.SHUTDOWN_SERVER:
            try:
                client_socket, address = self.sock.accept()
            except socket.timeout:
                pass
            except Exception as e:
                raise e
            else:
                self.__inst_queue.append(lambda: self.accept_new_client(client_socket, address))

    def accept_new_client(self, client_socket, address):
        if self.verbose:
            print(f"Connection from {':'.join(map(str, address))}")

        if self.__game_running:
            print("Rejecting client; game already running.")
            client_socket.sendall(Message.new_send_message(Instruction.Update.GAME_RUNNING.encode("utf-8")).encode())
            client_socket.close()

            return

        self.__client_sockets.append(client_socket)

        self.__client_info[client_socket.getpeername()] = {"id": self.__curr_client_id}
        self.__client_send_queue[client_socket.getpeername()] = []

        self.__curr_client_id += 1

    def handle_client_channels(self):
        # read any incoming requests from the clients
        read_sockets, _, _ = select.select(self.__client_sockets, [], [], 1 / Server.UPDATE_FREQUENCY)

        for s in read_sockets:
            message = Message.new_recv_message()

            buffer = s.recv(Message.BUFFER_SIZE)

            if not buffer:
                if self.verbose:
                    print(f"{s.getpeername()[0]} disconnected.")

                self.__client_sockets.remove(s)
                del self.__client_send_queue[s.getpeername()]
                continue

            while not message.decode(buffer):
                buffer = s.recv(Message.BUFFER_SIZE)

            self.decode_instruction(s.getpeername(), message.message.decode("utf-8"))

        # send any outgoing messages to the clients
        for s in self.__client_sockets:
            while self.__client_send_queue[s.getpeername()]:
                message = self.__client_send_queue[s.getpeername()].pop(0)

                s.sendall(message.encode())

                # if self.__client_send_queue[s.getpeername()]:
                #     time.sleep(1.0 / Server.SEND_RATE)

    def decode_instruction(self, client, message):
        operands = []

        if ":" in message:
            instruction, operand = message.split(":", 1)

            in_string = False
            cur_operand = ""

            for c in operand:
                if c == "'":
                    in_string = not in_string
                else:
                    if in_string:
                        cur_operand += c
                    elif c == ":":
                        operands.append(cur_operand)
                        cur_operand = ""

            operands.append(cur_operand)
        else:
            instruction = message

        if instruction == Instruction.SET_PROPERTY:
            assert len(operands) == 2
            self.__client_info[client][operands[0]] = operands[1]

            if operands[0] == "name":
                player_joined_message = Message.new_send_message(
                    f"{Instruction.Update.PLAYER_JOINED}:'{operands[1]}'".encode("utf-8")
                )

                for c in self.__client_send_queue:
                    if c == client:
                        continue
                    self.__client_send_queue[c].append(player_joined_message)

        if instruction == Instruction.Game.PICKUP_CARD:
            assert len(operands) == 1

            pickup_message = Message.new_send_message(message.encode("utf-8"))

            for c in self.__client_send_queue:
                if c == client:
                    continue
                self.__client_send_queue[c].append(pickup_message)

        if instruction == Instruction.Game.PLACE_CARD:
            assert len(operands) == 2

            src_deck = self.__decks[int(operands[0])]
            dst_deck = self.__decks[int(operands[1])]

            dst_deck.add_card_to_top(src_deck.take_top())

            place_message = Message.new_send_message(message.encode("utf-8"))

            for c in self.__client_send_queue:
                if c == client:
                    continue
                self.__client_send_queue[c].append(place_message)

        if instruction == Instruction.Game.MOVE_ENDED:
            ended_message = Message.new_send_message(Instruction.Game.MOVE_ENDED.encode("utf-8"))

            for c in self.__client_send_queue:
                if c == client:
                    continue
                self.__client_send_queue[c].append(ended_message)

        if instruction == Instruction.Game.CALL_MONGOOSE:
            mongoose_message = Message.new_send_message(message.encode("utf-8"))

            for c in self.__client_send_queue:
                self.__client_send_queue[c].append(mongoose_message)

        if instruction == Instruction.Update.CHAT_MESSAGE:
            chat_message = Message.new_send_message(message.encode("utf-8"))

            for c in self.__client_send_queue:
                self.__client_send_queue[c].append(chat_message)

        if instruction == Instruction.Game.FLIP_DECK:
            flip_message = Message.new_send_message(message.encode("utf-8"))

            for c in self.__client_send_queue:
                self.__client_send_queue[c].append(flip_message)

        if instruction == Instruction.Update.QUIT_GAME:
            if self.verbose:
                print(f"Player {self.__client_info[client]['name']} left the game.")
            del self.__client_info[client]

    def console(self):
        while not self.__flags & Server.Flags.SHUTDOWN_SERVER:
            i = input()
            if i.lower() in ("q", "quit", "shutdown"):
                self.__flags |= Server.Flags.SHUTDOWN_SERVER
                self.__inst_queue.append(lambda: print(f"Shutting down server..."))
            elif i.lower() in ("h", "help"):
                self.__inst_queue.append(Server.help)
            elif i.lower() in ("s", "start"):
                self.__inst_queue.append(self.start_game)

    def start_game(self):
        curr_id = 0
        for c in self.__client_info:
            self.__client_info[c]["id"] = curr_id
            curr_id += 1

        p_names = [f"'{self.__client_info[c]['name']}':'{self.__client_info[c]['id']}'" for c in self.__client_info]

        game_deck = Deck.full()
        game_deck.shuffle()

        suit_map = {"Spades": "0", "Diamonds": "1", "Clubs": "2", "Hearts": "3"}

        deck_str = ":".join([f"'{suit_map[card.suit]}-{card.value}'" for card in game_deck.cards])

        send_deck = f"{Instruction.Game.SEND_DECK}:{deck_str}"

        for c in self.__client_sockets:
            self.__client_send_queue[c.getpeername()].append(Message.new_send_message(send_deck.encode("utf-8")))

            c_id = self.__client_info[c.getpeername()]["id"]
            message_text = Instruction.START_GAME + f":'{c_id}':" + ":".join(p_names)

            message = Message.new_send_message(message_text.encode("utf-8"))
            self.__client_send_queue[c.getpeername()].append(message)

        player_decks = game_deck.deal(len(self.__client_sockets))

        # setup the decks in the order that each player will hold their IDs
        for d in player_decks:
            self.__decks.append(d)
            self.__decks.append(Deck.empty())

        for i in range(4):
            self.__decks.append(Deck.empty())

        self.__inst_queue.append(lambda: print(f"Starting game with: {', '.join(p_names)}"))

        self.__game_running = True

    @staticmethod
    def help():
        print("q, quit, shutdown - Shutdown the server")
        print("s, start - Start the game")
        print("h, help - Show the help message")

    def stop_server(self):
        self.sock.close()


def main():
    # this user has run the server script directly, so they are intending to host
    ip = input("Enter host IP> ")
    port = int(input("Enter host port> "))
    server = Server((ip, port))
    server.start_server()


if __name__ == "__main__":
    main()
