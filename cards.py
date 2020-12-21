import random
import os
import pygame


def load_texture(tex_name, resource):
    assert (os.path.exists(os.path.join(resource, tex_name)))
    texture = pygame.image.load(os.path.join(resource, tex_name))

    return texture


def resize_texture(texture, target_width):
    _, _, w, h = texture.get_rect()
    s_factor = target_width / w

    resized = pygame.transform.scale(texture, (int(w * s_factor), int(h * s_factor)))

    return resized


def rescale_back(texture):
    _, _, w, h = texture.get_rect()
    return pygame.transform.scale(texture, (w, int(w * 726 / 500)))


class Card:
    RES_LOCATION = "./res/textures/cards"
    # TODO: make this more flexible
    CARD_BACK_TEXTURE = rescale_back(load_texture("card_back.png", RES_LOCATION))

    def __init__(self, suit, value):
        self.suit = suit
        self.value = value

        self.__texture_name = self.__str__().replace(" ", "_").lower() + ".png"
        self.texture = load_texture(self.__texture_name, Card.RES_LOCATION)

        _, _, w, h = self.texture.get_rect()
        self.__aspect_ratio = w / h

    def render(self, render_target, center, size, face=True):
        screen_size = render_target.get_size()
        sc_w = int(screen_size[0] * size)
        sc_h = int(sc_w / self.__aspect_ratio)
        sc_s_x = screen_size[0] * center[0] - sc_w / 2
        sc_s_y = screen_size[1] * center[1] - sc_h / 2

        target_texture = resize_texture(self.texture if face else Card.CARD_BACK_TEXTURE, sc_w)

        render_target.blit(target_texture, (sc_s_x, sc_s_y))

    def __str__(self):
        val = ""
        if self.value == 1:
            val = "Ace"
        elif 1 < self.value <= 10:
            val = str(self.value)
        elif self.value == 11:
            val = "Jack"
        elif self.value == 12:
            val = "Queen"
        elif self.value == 13:
            val = "King"

        return f"{val} of {self.suit}"

    def __repr__(self):
        return self.__str__()


class Deck:
    def __init__(self, cards):
        self.cards = cards
        self.deck_id = -1

    @staticmethod
    def empty():
        return Deck([])

    @staticmethod
    def full():
        return Deck(Deck.get_all_cards())

    @staticmethod
    def get_all_cards():
        cards = []
        for suit in ["Spades", "Diamonds", "Clubs", "Hearts"]:
            for value in range(1, 14):
                cards.append(Card(suit, value))

        return cards

    def shuffle(self):
        random.shuffle(self.cards)

    def deal(self, n_players):
        piles = [Deck.empty() for _ in range(n_players)]

        for i, card in enumerate(self.cards):
            piles[i % n_players].add_card_to_bottom(card)

        return piles

    def add_card_to_top(self, card):
        if card is not None:
            self.cards = [card] + self.cards

    def add_card_to_bottom(self, card):
        if card is not None:
            self.cards.append(card)

    def top(self):
        if len(self.cards) == 0:
            return None
        return self.cards[0]

    def take_top(self):
        if len(self.cards) == 0:
            return None
        card = self.cards[0]
        self.cards = self.cards[1:]
        return card

    def bottom(self):
        if len(self.cards) == 0:
            return None
        return self.cards[-1]

    def take_bottom(self):
        if len(self.cards) == 0:
            return None
        card = self.cards[-1]
        self.cards = self.cards[:-1]
        return card

    def sort(self, reverse=False):
        self.cards.sort(key=lambda x: x.value, reverse=reverse)

    def __str__(self):
        return str(self.cards)

    def __repr__(self):
        return self.__str__()