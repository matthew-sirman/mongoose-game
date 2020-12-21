import pygame
import errno
from player import Player
from cards import Deck
from math import sin, cos, pi
from button import Button
from text import Text, TextFeed
from instructions import Instruction
from message import Message


def calc_nth_player_center(player, n_players, radius):
    theta = player * 2 * pi / n_players
    x_pos = sin(theta) * radius
    y_pos = cos(theta) * radius

    return (x_pos + 1) / 2, (y_pos + 1) / 2


class Mongoose:
    PLAYER_SPREAD_RADIUS = 0.7
    PLAYER_REGION_SIZE = 0.15
    CARD_SIZE = 0.07
    CARD_ASPECT_RATIO = 500 / 726
    CARD_STACK_SIZE = 0.02
    HOVER_HIGHLIGHT_ALLOWED_COLOUR = (66, 245, 99, 128)
    HOVER_HIGHLIGHT_DISALLOWED_COLOUR = (245, 66, 81, 128)

    UPDATE_FREQUENCY = 1000
    SEND_RATE = 100

    def __init__(self, client_socket, deck, screen_size=(1280, 720), title="Mongoose", clear_colour=(66, 135, 245)):
        self.client_socket = client_socket

        self.n_players = -1
        self.players = []
        self.deck = deck

        self.center_piles = []

        self.screen_size = screen_size
        self.clear_colour = clear_colour

        pygame.init()

        self.screen = pygame.display.set_mode(screen_size, pygame.DOUBLEBUF | pygame.RESIZABLE)
        pygame.display.set_caption(title)

        self.clock = pygame.time.Clock()

        self.__turn = 0
        self.__active_player = -1

        self.__holding_card = None
        self.__flipped_card = None

        self.__lmd_event_registered = False

        self.__mongoose_button = Button("Mongoose!", (0.9, 0.9), (0.1, 0.08), font_hierarchy=["Verdana"])
        self.__mongoose_button.subscribe_event(self.call_mongoose)

        self.__which_players_turn_label = Text("", 40, font_hierarchy=["Verdana"], text_colour=(255, 255, 255))

        self.__feed = TextFeed((0.18, 0.82), (0.3, 0.3))

        self.__flip_button = Button("Flip", (0.5, 0.7), (0.08, 0.06), "flip")

        self.__has_started_move = False

        self.__last_move = None

        self.__connected_to_server = True

        # self.__server_handling_thread = threading.Thread(target=self.handle_server_io, daemon=True)
        # self.__server_handling_thread.start()

        self.__server_send_queue = []

        self.__inst_queue = []

        self.__win_place_count = 1

    def setup_game(self, active_player, players):
        self.__active_player = active_player
        self.n_players = len(players)

        # self.deck = Deck.full()
        # self.deck.shuffle()

        piles = self.deck.deal(self.n_players)

        for (i, pile), name in zip(enumerate(piles), map(lambda x: x[0], players)):
            self.players.append(Player(pile, name, i, i == active_player))

        self.__turn = 0
        self.update_turn_label()

        self.__flip_button.subscribe_event(self.flip_deck)

        for i in range(4):
            p = Deck.empty()
            p.deck_id = len(players) * 2 + i
            self.center_piles.append(p)

    def current_player(self):
        return self.players[self.__turn % self.n_players]

    def previous_player(self):
        return self.players[(self.__turn + self.n_players - 1) % self.n_players]

    def active_player(self):
        return self.players[self.__active_player]

    def update_turn_label(self):
        self.__which_players_turn_label.text = f"{self.current_player().name}'s turn"
        self.__which_players_turn_label.update()

    def run(self):
        while True:
            pygame.event.pump()
            for event in pygame.event.get():
                if event.type == pygame.VIDEORESIZE:
                    self.screen_size = (event.w, event.h)
                    self.screen = pygame.display.set_mode(self.screen_size, pygame.DOUBLEBUF | pygame.RESIZABLE)

                if event.type == pygame.QUIT:
                    self.quit()

            mouse_pos = pygame.mouse.get_pos()
            mouse_pressed = pygame.mouse.get_pressed()

            self.current_turn()

            if not mouse_pressed[0]:
                self.__lmd_event_registered = False

            Button.update_all("main", self.screen_size, mouse_pos, mouse_pressed)

            if self.active_player().down_empty() and self.active_player() == self.current_player() and \
                    self.__holding_card is None:
                Button.update_all("flip", self.screen_size, mouse_pos, mouse_pressed)

            self.render()

            self.handle_instructions()
            self.handle_server_io()

            self.clock.tick(60)

    def render(self):
        self.screen.fill(self.clear_colour)

        # render players' hands
        for i, player in enumerate(self.players):
            # rotate each player round such that the active player is at the bottom
            screen_index = (i + self.n_players - self.__active_player) % self.n_players
            player.render_hand(self.screen,
                               calc_nth_player_center(screen_index, self.n_players, Mongoose.PLAYER_SPREAD_RADIUS),
                               i == self.__turn % self.n_players,
                               Mongoose.PLAYER_REGION_SIZE)

        # render center piles
        for i, cp in enumerate(self.center_piles):
            cx = 0.5 - (i - 1.5) * 0.08
            cy = 0.5
            self.render_pile(cp, (cx, cy), Mongoose.CARD_SIZE)

        # display held card, if the current player is holding a card
        if self.__holding_card is not None:
            # draw hovering highlights
            for i, cp in enumerate(self.center_piles):
                cx = 0.5 - (i - 1.5) * 0.08
                cy = 0.5
                h = Mongoose.CARD_SIZE * self.get_aspect_ratio() / Mongoose.CARD_ASPECT_RATIO + \
                    Mongoose.CARD_STACK_SIZE * max(len(cp.cards) - 1, 0)
                region = (cx, cy, Mongoose.CARD_SIZE, h)
                if self.hovering_in_region(region):
                    highlight_s = pygame.Surface((int(region[2] * self.screen_size[0]),
                                                  int(region[3] * self.screen_size[1])))
                    col = Mongoose.HOVER_HIGHLIGHT_ALLOWED_COLOUR if self.is_valid_center_move(cp) else \
                        Mongoose.HOVER_HIGHLIGHT_DISALLOWED_COLOUR

                    highlight_s.set_alpha(col[3])
                    highlight_s.fill(col[:3])
                    self.screen.blit(highlight_s, (int((region[0] - region[2] / 2) * self.screen_size[0]),
                                                   int((region[1] - region[3] / 2) * self.screen_size[1])))

            for i, player in enumerate(self.players):
                screen_index = (i + self.n_players - self.__active_player) % self.n_players
                region = player.get_face_up_region(calc_nth_player_center(screen_index,
                                                                          self.n_players,
                                                                          Mongoose.PLAYER_SPREAD_RADIUS),
                                                   Mongoose.PLAYER_REGION_SIZE)

                col = Mongoose.HOVER_HIGHLIGHT_ALLOWED_COLOUR \
                    if len(player.face_up.cards) != 0 or player == self.current_player() else \
                    Mongoose.HOVER_HIGHLIGHT_DISALLOWED_COLOUR

                if self.hovering_in_region(region):
                    highlight_s = pygame.Surface((int(region[2] * self.screen_size[0]),
                                                  int(region[3] * self.screen_size[1])))
                    highlight_s.set_alpha(col[3])
                    highlight_s.fill(col[:3])
                    self.screen.blit(highlight_s, (int((region[0] - region[2] / 2) * self.screen_size[0]),
                                                   int((region[1] - region[3] / 2) * self.screen_size[1])))

            # draw this card
            mouse_x, mouse_y = pygame.mouse.get_pos()
            self.__holding_card.render(self.screen,
                                       (mouse_x / self.screen_size[0], mouse_y / self.screen_size[1]),
                                       Mongoose.CARD_SIZE)

        self.__which_players_turn_label.render(self.screen, (0.1, 0.1))
        self.__feed.render(self.screen)

        Button.render_all("main", self.screen)

        if self.active_player().down_empty() and self.active_player() == self.current_player() and \
                self.__holding_card is None:
            Button.render_all("flip", self.screen)

        pygame.display.flip()

    def render_pile(self, pile, center, size):
        for i, card in enumerate(pile.cards):
            cx = center[0]
            cy = center[1] + (i - (len(pile.cards) - 1) / 2) * Mongoose.CARD_STACK_SIZE
            card.render(self.screen, (cx, cy), size)

    def handle_instructions(self):
        while self.__inst_queue:
            self.__inst_queue.pop(0)()

    def current_turn(self):
        current_player_index = self.__turn % self.n_players

        if current_player_index != self.__active_player:
            return

        current_player = self.players[current_player_index]

        cp_screen_index = (current_player_index + self.n_players - self.__active_player) % self.n_players

        if not self.is_holding_card():
            card, source = current_player.choose_card(calc_nth_player_center(cp_screen_index,
                                                                             self.n_players,
                                                                             Mongoose.PLAYER_SPREAD_RADIUS),
                                                      Mongoose.PLAYER_REGION_SIZE, self.left_clicked_in_region)

            if card is not None:
                self.pick_up_card(card, source.deck_id)
                self.__last_move = [card, source, None]

        else:
            # check for placement
            # check centers
            for i, cp in enumerate(self.center_piles):
                cx = 0.5 - (i - 1.5) * 0.08
                cy = 0.5
                h = Mongoose.CARD_SIZE * self.get_aspect_ratio() / Mongoose.CARD_ASPECT_RATIO + \
                    Mongoose.CARD_STACK_SIZE * max(len(cp.cards) - 1, 0)
                region = (cx, cy, Mongoose.CARD_SIZE, h)

                valid = self.is_valid_center_move(cp)
                if self.left_clicked_in_region(region) and valid:
                    self.place_card(cp)
                    return

            # check other piles
            for i, player in enumerate(self.players):
                screen_index = (i + self.n_players - self.__active_player) % self.n_players
                region = player.get_face_up_region(calc_nth_player_center(screen_index,
                                                                          self.n_players,
                                                                          Mongoose.PLAYER_SPREAD_RADIUS),
                                                   Mongoose.PLAYER_REGION_SIZE)
                if self.left_clicked_in_region(region) and (len(player.face_up.cards) != 0 or
                                                            player == self.current_player()):
                    self.place_card(player.face_up)
                    return

    def is_valid_center_move(self, deck):
        if len(deck.cards) == 0:
            return self.__holding_card.value == 7

        max_val = max(map(lambda x: x.value, deck.cards))
        min_val = min(map(lambda x: x.value, deck.cards))

        valid = self.__holding_card.value == max_val + 1 or self.__holding_card.value == min_val - 1

        return valid

    def pick_up_card(self, card, deck_id):
        if self.__holding_card is None:
            self.__holding_card = card
            self.__has_started_move = True

            message = f"{Instruction.Game.PICKUP_CARD}:'{deck_id}'"
            self.client_socket.sendall(Message.new_send_message(message.encode("utf-8")).encode())

    def place_card(self, target_deck):

        if self.__holding_card is None:
            return

        valid_move = self.check_for_auto_mongoose(self.__holding_card, target_deck)

        if not valid_move:
            message = f"{Instruction.Game.PLACE_CARD}:'{self.__last_move[1].deck_id}':'{self.current_player().face_up.deck_id}'"
            self.client_socket.sendall(Message.new_send_message(message.encode("utf-8")).encode())
            self.current_player().face_up.add_card_to_top(self.__holding_card)

            self.__holding_card = None
            self.__last_move = None

            return

        target_deck.add_card_to_top(self.__holding_card)

        self.__holding_card = None

        self.__last_move[2] = target_deck

        message = f"{Instruction.Game.PLACE_CARD}:'{self.__last_move[1].deck_id}':'{target_deck.deck_id}'"
        self.client_socket.sendall(Message.new_send_message(message.encode("utf-8")).encode())

        # if the target deck was the player's face up deck, that was the end of their turn.
        if target_deck == self.current_player().face_up:
            self.next_turn()

            message = f"{Instruction.Game.MOVE_ENDED}"
            self.client_socket.sendall(Message.new_send_message(message.encode("utf-8")).encode())

        self.sort_centers()

    def flip_deck(self):
        flip_message = f"{Instruction.Game.FLIP_DECK}:'{self.__active_player}'"
        self.client_socket.sendall(Message.new_send_message(flip_message.encode("utf-8")).encode())

    def is_holding_card(self):
        return self.__holding_card is not None

    def left_clicked_in_region(self, region):
        if self.__lmd_event_registered:
            return False

        if pygame.mouse.get_pressed()[0]:
            mouse_x, mouse_y = pygame.mouse.get_pos()
            sx = (region[0] - region[2] / 2) * self.screen_size[0]
            ex = (region[0] + region[2] / 2) * self.screen_size[0]
            sy = (region[1] - region[3] / 2) * self.screen_size[1]
            ey = (region[1] + region[3] / 2) * self.screen_size[1]
            self.__lmd_event_registered = sx <= mouse_x <= ex and sy <= mouse_y <= ey
            return self.__lmd_event_registered
        return False

    def hovering_in_region(self, region):
        mouse_x, mouse_y = pygame.mouse.get_pos()
        sx = (region[0] - region[2] / 2) * self.screen_size[0]
        ex = (region[0] + region[2] / 2) * self.screen_size[0]
        sy = (region[1] - region[3] / 2) * self.screen_size[1]
        ey = (region[1] + region[3] / 2) * self.screen_size[1]
        return sx <= mouse_x <= ex and sy <= mouse_y <= ey

    def call_mongoose(self):
        if self.__has_started_move:
            target = self.current_player()
        else:
            target = self.previous_player()

        check = self.check_move(self.__last_move, target)

        if check:
            self.sync_send_chat_message(f"{self.active_player().name} mongoosed themselves!!")
            self.mongoose_player(self.active_player(), False)
        else:
            self.sync_send_chat_message(f"{self.active_player().name} mongoosed {target.name}!")
            self.mongoose_player(target, target == self.current_player())

    def check_move(self, move, player):
        # true means the move was fine, false means it was not
        if not move:
            return True

        card, src, dst = move

        if dst is None:
            # did they pick from the wrong deck?
            if src == player.face_up:
                if card.value == 7:
                    return True

                for p in self.center_piles:
                    if len(p.cards) != 0:
                        max_val = max(map(lambda x: x.value, p.cards))
                        min_val = min(map(lambda x: x.value, p.cards))
                        suit = p.cards[0].suit
                        if card.suit == suit and card.value in (max_val + 1, min_val - 1):
                            return True

                for p in self.players:
                    if p == player or len(p.face_up.cards) == 0:
                        continue
                    if p.face_up.top().value + 1 == card.value:
                        return True

                return False
            else:
                if len(player.face_up.cards) != 0:
                    top_card = player.face_up.top()

                    if top_card.value == 7:
                        return False

                    for p in self.center_piles:
                        if len(p.cards) != 0:
                            max_val = max(map(lambda x: x.value, p.cards))
                            min_val = min(map(lambda x: x.value, p.cards))
                            suit = p.cards[0].suit
                            if top_card.suit == suit and top_card.value in (max_val + 1, min_val - 1):
                                return False

                    for p in self.players:
                        if p == player or len(p.face_up.cards) == 0:
                            continue
                        if p.face_up.top().value + 1 == top_card.value:
                            return False

                return True

        # by this point, we know that a complete move was made, so we must check if it was the right one.

        if src == player.face_up:
            # if we managed to put the card in the center without being auto mongoosed, that was the correct move
            if dst in self.center_piles:
                return True

        for p in self.center_piles:
            if len(p.cards) != 0:
                max_val = max(map(lambda x: x.value, p.cards))
                min_val = min(map(lambda x: x.value, p.cards))
                suit = p.cards[0].suit
                if card.suit == suit and card.value in (max_val + 1, min_val - 1):
                    return False

        for p_id in range(self.__turn + 1, self.__turn + self.n_players):
            up_pile = self.players[p_id % self.n_players].face_up
            if len(up_pile.cards) == 0:
                continue
            if up_pile == dst:
                break
            if up_pile.top().value + 1 == card.value:
                return False

        if src == player.face_up:
            if src == dst:
                return False

            if dst.top().value != dst.cards[1].value + 1:
                return False

        else:
            if len(player.face_up.cards) != 0:
                # check that there was no valid move with the face up pile
                top_card = player.face_up.top()

                if top_card.value == 7:
                    return False

                for p in self.center_piles:
                    if len(p.cards) != 0:
                        max_val = max(map(lambda x: x.value, p.cards))
                        min_val = min(map(lambda x: x.value, p.cards))
                        suit = p.cards[0].suit
                        if top_card.suit == suit and top_card.value in (max_val + 1, min_val - 1):
                            return False

                for p in self.players:
                    if p == player or len(p.face_up.cards) == 0:
                        continue
                    if p.face_up.top().value + 1 == top_card.value:
                        return False

            if dst != player.face_up:
                if dst.top().value != dst.cards[1].value + 1:
                    return False

        # if nothing was caught during the whole analysis, the call was correct.
        return True

    def sync_send_chat_message(self, message):
        send_message = Message.new_send_message(f"{Instruction.Update.CHAT_MESSAGE}:'{message}'".encode("utf-8"))
        self.client_socket.sendall(send_message.encode())

    def check_for_auto_mongoose(self, card, pile):
        if pile in self.center_piles:
            # if this move was invalid, we need to retract the card so as not to break the game.
            if len(pile.cards) == 0:
                return True
            for c in pile.cards:
                if c.suit != card.suit:
                    # the move was invalid (we already know that the card is adjacent)
                    self.sync_send_chat_message(f"{self.current_player().name} was auto-mongoosed!")
                    # self.current_player().face_up.add_card_to_top(card)
                    # pile.cards.remove(card)
                    self.mongoose_player(self.current_player(), True)

                    return False
        return True

    def mongoose_player(self, target, skip=True):
        message = f"{Instruction.Game.CALL_MONGOOSE}:'{target.player_id}':'{1 if skip else 0}'"
        self.client_socket.sendall(Message.new_send_message(message.encode("utf-8")).encode())

    def pass_cards_to_player(self, target_id, skip_turn):
        for i, player in enumerate(self.players):
            if i != target_id:
                self.players[target_id].face_down.add_card_to_bottom(player.face_down.take_bottom())

        if skip_turn:
            self.next_turn()

    def handle_server_io(self):
        if not self.__connected_to_server:
            return

        try:
            message = Message.new_recv_message()

            buffer = self.client_socket.recv(Message.BUFFER_SIZE)

            if not buffer:
                self.client_socket.close()

                self.__connected_to_server = False

            while not message.decode(buffer):
                buffer = self.client_socket.recv(Message.BUFFER_SIZE)

            self.decode_instruction(message.message.decode("utf-8"))

        except IOError as e:
            if e.errno != errno.EAGAIN and e.errno != errno.EWOULDBLOCK:
                self.client_socket.close()

                self.__connected_to_server = False

    def sort_centers(self):
        for p in self.center_piles:
            p.sort(True)

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

        if instruction == Instruction.Game.PICKUP_CARD:
            assert len(operands) == 1

            deck_id = int(operands[0])

            card = self.flip_foreign_card(deck_id)

            self.__last_move = [card, self.get_deck_by_id(deck_id), None]
            self.__has_started_move = True

        if instruction == Instruction.Game.PLACE_CARD:
            assert len(operands) == 2

            src_player = self.players[int(operands[0]) // 2]
            dst_deck = self.get_deck_by_id(int(operands[1]))

            src_player.place_flipped_card(dst_deck)

            self.__last_move[2] = dst_deck

            self.sort_centers()

        if instruction == Instruction.Game.MOVE_ENDED:
            self.next_turn()

        if instruction == Instruction.Game.CALL_MONGOOSE:
            assert len(operands) == 2

            target_player = int(operands[0])
            skip_turn = bool(int(operands[1]))

            self.pass_cards_to_player(target_player, skip_turn)

        if instruction == Instruction.Game.FLIP_DECK:
            assert len(operands) == 1

            flip_player = int(operands[0])
            self.players[flip_player].flip_deck()

        if instruction == Instruction.Update.CHAT_MESSAGE:
            assert len(operands) == 1

            self.__feed.add_line(operands[0])

    def get_deck_by_id(self, deck_id):
        if deck_id < self.n_players * 2:
            p = self.players[deck_id // 2]
            return p.face_down if deck_id % 2 == 0 else p.face_up
        else:
            return self.center_piles[deck_id - self.n_players * 2]

    def flip_foreign_card(self, deck_id):
        f_p = self.players[deck_id // 2]
        card = f_p.flip_foreign_top_card(deck_id % 2)
        return card

    def get_aspect_ratio(self):
        return self.screen_size[0] / self.screen_size[1]

    def next_turn(self, __c_esc=0):
        if self.current_player().has_finished():
            self.sync_send_chat_message(f"Player {self.current_player().name} has finished in position {self.__win_place_count}!")
            self.__win_place_count += 1

        self.__turn += 1
        self.update_turn_label()
        self.__has_started_move = False

        if __c_esc == self.n_players - 1:
            self.sync_send_chat_message("Game finished!")
            return

        if self.current_player().has_finished():
            self.next_turn(__c_esc + 1)

    def quit(self):
        if self.__connected_to_server:
            self.client_socket.sendall(Message.new_send_message(Instruction.Update.QUIT_GAME.encode("utf-8")).encode())
        # self.__server_handling_thread.join(0.5)
        pygame.quit()
        quit()
