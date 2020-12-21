import pygame
from cards import Deck
from text import Text


class Pile:
    DOWN = 0
    UP = 1


class Player:
    HAND_BOUND_COLOUR = (235, 213, 52)
    HAND_BOUND_ASPECT_RATIO = 1.41
    CARD_ASPECT_RATIO = 500 / 726
    HAND_BOUND_WIDTH = 3
    PICKUP_V_OFFSET = 0.02

    def __init__(self, cards, name, player_id, local_active_player=False):
        self.face_down = cards
        self.face_up = Deck.empty()

        self.player_id = player_id
        self.face_down.deck_id = 2 * player_id
        self.face_up.deck_id = 2 * player_id + 1

        self.name = name
        self.__name_text = Text(self.name, font_hierarchy=["Verdana"])

        self.local_active_player = local_active_player

        self.__flipped_card = None

    def render_hand(self, render_target, center, active_player, size=0.15):
        screen_size = render_target.get_size()

        # draw the bounding box of the player's hand
        sc_w = int(screen_size[0] * size)
        sc_h = int(sc_w / Player.HAND_BOUND_ASPECT_RATIO)
        sc_s_x = screen_size[0] * center[0] - sc_w / 2
        sc_s_y = screen_size[1] * center[1] - sc_h / 2

        pygame.draw.rect(render_target, Player.HAND_BOUND_COLOUR, (sc_s_x, sc_s_y, sc_w, sc_h), Player.HAND_BOUND_WIDTH)

        card_size = size * 0.46

        # draw the face down pile
        top_d_card = self.face_down.top()

        if top_d_card is not None:
            top_d_card.render(render_target, (center[0] - size / 4, center[1]), card_size, False)

        # draw the face up pile
        top_u_card = self.face_up.top()

        if top_u_card is not None:
            top_u_card.render(render_target, (center[0] + size / 4, center[1]), card_size, True)

        if self.__flipped_card is not None:
            cx = center[0] + (-size if self.__flipped_card[1] == 0 else size) / 4
            cy = center[1] - Player.PICKUP_V_OFFSET
            self.__flipped_card[0].render(render_target, (cx, cy), card_size, True)

        # draw the player's name
        if active_player:
            self.__name_text.text_colour = (107, 235, 52)
        else:
            self.__name_text.text_colour = (255, 255, 255)
        self.__name_text.update()
        self.__name_text.render(render_target, (center[0], center[1] + (6 * size / Player.HAND_BOUND_ASPECT_RATIO) / 5))

    def choose_card(self, active_center, active_size, click_test_fn):
        region_down = [active_center[0] - active_size / 4, active_center[1],
                       active_size * 0.46, active_size / Player.CARD_ASPECT_RATIO * 0.8]
        region_up = [active_center[0] + active_size / 4, active_center[1],
                     active_size * 0.46, active_size / Player.CARD_ASPECT_RATIO * 0.8]

        pickup_deck = None
        if click_test_fn(region_down):
            pickup_deck = self.face_down
        if click_test_fn(region_up):
            pickup_deck = self.face_up

        return None if pickup_deck is None else pickup_deck.take_top(), pickup_deck

    def flip_deck(self):
        self.face_down = Deck(self.face_up.cards[::-1])
        self.face_up = Deck.empty()

        self.face_down.deck_id = 2 * self.player_id
        self.face_up.deck_id = 2 * self.player_id + 1

    def flip_foreign_top_card(self, deck_id):
        deck = self.face_down if deck_id == 0 else self.face_up

        self.__flipped_card = (deck.take_top(), deck_id)

        return self.__flipped_card[0]

    def place_flipped_card(self, dst):
        dst.add_card_to_top(self.__flipped_card[0])
        self.__flipped_card = None

    def down_empty(self):
        return len(self.face_down.cards) == 0

    def has_finished(self):
        return len(self.face_up.cards) + len(self.face_down.cards) == 0

    @staticmethod
    def get_face_up_region(active_center, active_size):
        return [active_center[0] + active_size / 4, active_center[1],
                active_size * 0.46, active_size / Player.CARD_ASPECT_RATIO * 0.8]
