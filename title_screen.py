import pygame
import socket
import errno
import threading
from button import Button
from text import Text, TextFeed
from textbox import TextBox
from message import Message
from instructions import Instruction
from cards import Deck, Card


class TitleScreen:
    UPDATE_FREQUENCY = 1000

    def __init__(self, screen_size=(1280, 720), title="Mongoose", clear_colour=(66, 135, 245)):
        self.screen_size = screen_size
        self.title = title
        self.clear_colour = clear_colour

        pygame.init()

        self.screen = pygame.display.set_mode(screen_size, pygame.DOUBLEBUF | pygame.RESIZABLE)
        pygame.display.set_caption(title)

        self.clock = pygame.time.Clock()

        self.__title_text = Text(title, 64, text_colour=(255, 255, 255))

        self.__name_input = TextBox((0.5, 0.4), (0.4, 0.06),
                                    Text(font_size=32, font_hierarchy=["Verdana"]),
                                    Text("Name", font_size=32, font_hierarchy=["Verdana"], text_colour=(64, 64, 64)),
                                    register_group="title_screen")
        self.__ip_input = TextBox((0.5, 0.5), (0.4, 0.06),
                                  Text(font_size=32, font_hierarchy=["Verdana"]),
                                  Text("IP Address", font_size=32, font_hierarchy=["Verdana"],
                                       text_colour=(64, 64, 64)),
                                  register_group="title_screen")
        self.__port_input = TextBox((0.5, 0.6), (0.4, 0.06),
                                    Text(font_size=32, font_hierarchy=["Verdana"]),
                                    Text("Port", font_size=32, font_hierarchy=["Verdana"], text_colour=(64, 64, 64)),
                                    register_group="title_screen")

        self.__join_button = Button("Join", (0.5, 0.8), (0.1, 0.08), register_group="title_screen")
        self.__join_button.subscribe_event(self.join_game)

        self.__status_text = Text("Status: Not connected", font_size=28,
                                  font_hierarchy=["Verdana"], text_colour=(255, 0, 0))

        self.__info_feed = TextFeed((0.85, 0.5), (0.3, 0.3))

        self.client_socket = None

        self.__connected_to_server = False

        # self.__server_handling_thread = threading.Thread(target=self.handle_server_io, daemon=True)

        # self.__server_handling_thread.start()

        self.__sync_deck = None
        self.__game_package = []

        self.__join_game_thread = None

    def run(self):
        while not self.__game_package:
            pygame.event.pump()
            for event in pygame.event.get():
                if event.type == pygame.VIDEORESIZE:
                    self.screen_size = (event.w, event.h)
                    self.screen = pygame.display.set_mode(self.screen_size, pygame.DOUBLEBUF | pygame.RESIZABLE)

                if event.type == pygame.QUIT:
                    self.quit()

                TextBox.update_all("title_screen", self.screen_size, event)

            mouse_pos = pygame.mouse.get_pos()
            mouse_pressed = pygame.mouse.get_pressed()

            Button.update_all("title_screen", self.screen_size, mouse_pos, mouse_pressed)

            self.render()

            self.handle_server_io()

            self.clock.tick(60)

        return self.__game_package

    def render(self):
        self.screen.fill(self.clear_colour)

        self.__title_text.render(self.screen, (0.5, 0.2))

        Button.render_all("title_screen", self.screen)
        TextBox.render_all("title_screen", self.screen)

        self.__status_text.render_from_corner(self.screen, (0.1 * self.screen_size[0], 0.8 * self.screen_size[1]))

        self.__info_feed.render(self.screen)

        pygame.display.flip()

    def join_game(self):
        if self.__join_game_thread is not None:
            if self.__join_game_thread.is_alive():
                return

        self.__join_game_thread = threading.Thread(target=self.join_game_async)
        self.__join_game_thread.start()

    def join_game_async(self):
        if not self.__port_input.text.isnumeric() or self.__connected_to_server:
            return

        ip = self.__ip_input.text
        port = int(self.__port_input.text)

        try:
            self.__status_text.text = f"Status: Connecting to server..."
            self.__status_text.text_colour = (255, 170, 0)
            self.__status_text.update()

            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(10)
            self.client_socket.connect((ip, port))

            self.client_socket.setblocking(False)

            self.__status_text.text = f"Status: Connected to {ip}:{port}. Waiting for game..."
            self.__status_text.text_colour = (0, 255, 0)
            self.__status_text.update()

            name_message = Message.new_send_message(
                f"{Instruction.SET_PROPERTY}:'name':'{self.__name_input.text}'".encode("utf-8")
            )

            self.client_socket.sendall(name_message.encode())

            self.__connected_to_server = True

        except ConnectionRefusedError:
            self.__status_text.text = f"Status: Connection to {ip}:{port} failed."
            self.__status_text.text_colour = (255, 0, 0)
            self.__status_text.update()

        except socket.timeout:
            self.__status_text.text = f"Status: Connection to {ip}:{port} timed out."
            self.__status_text.text_colour = (255, 0, 0)
            self.__status_text.update()

    def handle_server_io(self):
        if not self.__connected_to_server:
            return

        try:
            message = Message.new_recv_message()

            buffer = self.client_socket.recv(Message.BUFFER_SIZE)

            if not buffer:
                self.__status_text.text = f"Status: Lost connection to server."
                self.__status_text.text_colour = (255, 0, 0)
                self.__status_text.update()
                self.client_socket.close()

                self.__connected_to_server = False

            while not message.decode(buffer):
                buffer = self.client_socket.recv(Message.BUFFER_SIZE)

            self.decode_instruction(message.message.decode("utf-8"))
        except IOError as e:
            if e.errno != errno.EAGAIN and e.errno != errno.EWOULDBLOCK:
                self.__status_text.text = f"Error: {e}"
                self.__status_text.text_colour = (255, 0, 0)
                self.__status_text.update()
                self.client_socket.close()

                self.__connected_to_server = False

    def decode_instruction(self, message):
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

        if instruction == Instruction.Update.GAME_RUNNING:
            self.__status_text.text = f"Status: Game already running on server."
            self.__status_text.text_colour = (255, 170, 0)
            self.__status_text.update()
            self.client_socket.close()

            self.__connected_to_server = False

        if instruction == Instruction.START_GAME:
            active_id = int(operands[0])

            players = []

            _p = []

            for i, o in enumerate(operands[1:]):
                # even: name, odd: id
                if i % 2 == 0:
                    _p = [o]
                else:
                    _p.append(int(o))
                    players.append(_p)

            self.start_game(active_id, sorted(players, key=lambda x: x[1]))

        if instruction == Instruction.Update.PLAYER_JOINED:
            assert len(operands) == 1
            self.__info_feed.add_line(f"Player {operands[0]} joined the game.")

        if instruction == Instruction.Game.SEND_DECK:
            assert len(operands) == 52
            suit_map = {"0": "Spades", "1": "Diamonds", "2": "Clubs", "3": "Hearts"}

            cards = []

            for card in operands:
                s, v = card.split("-")
                cards.append(Card(suit_map[s], int(v)))

            self.__sync_deck = Deck(cards)

    def start_game(self, active_id, players):
        self.__game_package = [active_id, players, self.client_socket, self.__sync_deck]

    def quit(self):
        if self.__connected_to_server:
            self.client_socket.sendall(Message.new_send_message(Instruction.Update.QUIT_GAME.encode("utf-8")).encode())
        # self.__server_handling_thread.join(0.5)
        pygame.quit()
        quit()
