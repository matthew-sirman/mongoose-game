import pygame


class Text:
    def __init__(self, text="", font_size=32, font_hierarchy=(), text_colour=(0, 0, 0)):
        self.text = text
        self.font_size = font_size
        self.font_hierarchy = font_hierarchy
        self.text_colour = text_colour

        self.__font = self.create_font()
        self.__render_image = self.__font.render(self.text, True, self.text_colour)

    def create_font(self):
        available_fonts = pygame.font.get_fonts()
        choices = map(lambda x: x.replace(" ", "").lower(), self.font_hierarchy)

        for choice in choices:
            if choice in available_fonts:
                return pygame.font.SysFont(choice, self.font_size)
        return pygame.font.Font(None, self.font_size)

    def update(self):
        self.__font = self.create_font()
        self.__render_image = self.__font.render(self.text, True, self.text_colour)

    def render(self, render_target, center):
        screen_size = render_target.get_size()
        sc_s_x = int(screen_size[0] * center[0] - self.__render_image.get_width() / 2)
        sc_s_y = int(screen_size[1] * center[1] - self.__render_image.get_height() / 2)

        render_target.blit(self.__render_image, (sc_s_x, sc_s_y))

    def render_from_corner(self, render_target, pos):
        render_target.blit(self.__render_image, pos)

    def get_height(self):
        return self.__render_image.get_height()


class TextFeed:
    def __init__(self, center, size, max_lines=5, font_size=24, font_hierarchy=(), padding=0.01):
        self.center = center
        self.size = size
        self.max_lines = max_lines
        self.font_size = font_size
        self.font_hierarchy = font_hierarchy
        self.padding = padding

        self.__texts = []

    def add_line(self, new_line, colour=(0, 0, 0)):
        new_text = Text(new_line, self.font_size, self.font_hierarchy, colour)
        self.__texts = [new_text] + self.__texts

    def render(self, render_target):
        screen_size = render_target.get_size()
        sc_s_x = (self.center[0] - self.size[0] / 2) * screen_size[0]
        sc_s_y = (self.center[1] - self.size[1] / 2) * screen_size[1]

        for line in self.__texts[:self.max_lines][::-1]:
            line.render_from_corner(render_target, (sc_s_x, sc_s_y))
            sc_s_y += line.get_height() + self.padding * screen_size[1]
