import pygame
from text import Text

pygame.init()


class TextBox:
    DEFAULT_ACTIVE_COLOUR = (255, 255, 255)
    DEFAULT_INACTIVE_COLOUR = (150, 150, 150)
    BORDER_COLOUR = (0, 0, 0)
    BORDER_WIDTH = 2

    REGISTERED_TEXTBOXES = {}

    def __init__(self, center, size, text=Text(), shadow_text=Text(), active_colour=None, inactive_colour=None, register_group="main"):
        self.center = center
        self.size = size
        self.active_colour = active_colour if active_colour is not None else TextBox.DEFAULT_ACTIVE_COLOUR
        self.inactive_colour = inactive_colour if inactive_colour is not None else TextBox.DEFAULT_INACTIVE_COLOUR
        self.text = text.text
        self.shadow_text = shadow_text
        self.__display_text = text
        self.active = False

        if register_group is not None:
            if register_group in TextBox.REGISTERED_TEXTBOXES:
                TextBox.REGISTERED_TEXTBOXES[register_group].append(self)
            else:
                TextBox.REGISTERED_TEXTBOXES[register_group] = [self]

    def update(self, screen_size, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            mp_x, mp_y = event.pos
            if (self.center[0] - self.size[0] / 2) <= mp_x / screen_size[0] <= (self.center[0] + self.size[0] / 2) and \
                    (self.center[1] - self.size[1] / 2) <= mp_y / screen_size[1] <= (self.center[1] + self.size[1] / 2):
                self.active = not self.active
            else:
                self.active = False

        if event.type == pygame.KEYDOWN:
            if self.active:
                if event.key == pygame.K_RETURN:
                    pass
                elif event.key == pygame.K_BACKSPACE:
                    self.text = self.text[:-1]
                else:
                    self.text += event.unicode
                # Re-render the text.
                self.__display_text.text = self.text
                self.__display_text.update()

    def render(self, render_target):
        screen_size = render_target.get_size()
        pygame.draw.rect(render_target, self.active_colour if self.active else self.inactive_colour,
                         ((self.center[0] - self.size[0] / 2) * screen_size[0],
                          (self.center[1] - self.size[1] / 2) * screen_size[1],
                          self.size[0] * screen_size[0],
                          self.size[1] * screen_size[1]))

        self.__display_text.render(render_target, self.center)

        if self.text == "":
            self.shadow_text.render(render_target, self.center)

        pygame.draw.rect(render_target, TextBox.BORDER_COLOUR,
                         ((self.center[0] - self.size[0] / 2) * screen_size[0],
                          (self.center[1] - self.size[1] / 2) * screen_size[1],
                          self.size[0] * screen_size[0],
                          self.size[1] * screen_size[1]),
                         TextBox.BORDER_WIDTH)

    @staticmethod
    def render_all(group, render_target):
        for tb in TextBox.REGISTERED_TEXTBOXES[group]:
            tb.render(render_target)

    @staticmethod
    def update_all(group, screen_size, event):
        for tb in TextBox.REGISTERED_TEXTBOXES[group]:
            tb.update(screen_size, event)