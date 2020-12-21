import pygame
from text import Text


class Button:
    DEFAULT_BORDER_COL = (255, 255, 255)
    DEFAULT_BORDER_WIDTH = 2
    DEFAULT_FOREGROUND_COL = (64, 116, 194)
    DEFAULT_PRESSED_COL = (52, 83, 130)
    DEFAULT_HOVER_COL = (71, 128, 214)
    DEFAULT_TEXT_COL = (255, 255, 255)
    DEFAULT_FONT_SIZE = 24
    DEFAULT_FONT_HIERARCHY = ()

    REGISTERED_BUTTONS = {}

    class State:
        DEFAULT = 0
        HOVER = 1
        PRESSED = 2

    def __init__(self, text, center, size, register_group="main", **kwargs):
        self.text = text
        self.center = center
        self.size = size

        if register_group is not None:
            if register_group in Button.REGISTERED_BUTTONS:
                Button.REGISTERED_BUTTONS[register_group].append(self)
            else:
                Button.REGISTERED_BUTTONS[register_group] = [self]

        if "border_colour" in kwargs:
            self.border_colour = kwargs["border_colour"]
        else:
            self.border_colour = Button.DEFAULT_BORDER_COL

        if "border_width" in kwargs:
            self.border_width = kwargs["border_width"]
        else:
            self.border_width = Button.DEFAULT_BORDER_WIDTH

        if "foreground_colour" in kwargs:
            self.foreground_colour = kwargs["foreground_colour"]
        else:
            self.foreground_colour = Button.DEFAULT_FOREGROUND_COL

        if "pressed_colour" in kwargs:
            self.pressed_colour = kwargs["pressed_colour"]
        else:
            self.pressed_colour = Button.DEFAULT_PRESSED_COL

        if "hover_colour" in kwargs:
            self.hover_colour = kwargs["hover_colour"]
        else:
            self.hover_colour = Button.DEFAULT_HOVER_COL

        if "text_colour" in kwargs:
            self.text_colour = kwargs["text_colour"]
        else:
            self.text_colour = Button.DEFAULT_TEXT_COL

        if "font_size" in kwargs:
            self.font_size = kwargs["font_size"]
        else:
            self.font_size = Button.DEFAULT_FONT_SIZE

        if "font_hierarchy" in kwargs:
            self.font_hierarchy = kwargs["font_hierarchy"]
        else:
            self.font_hierarchy = Button.DEFAULT_FONT_HIERARCHY

        self.__text = Text(self.text, self.font_size, self.font_hierarchy, self.text_colour)

        self.__state = Button.State.DEFAULT
        self.__event_callbacks = []

    def render(self, render_target):
        foreground = None

        if self.__state == Button.State.DEFAULT:
            foreground = self.foreground_colour
        elif self.__state == Button.State.HOVER:
            foreground = self.hover_colour
        elif self.__state == Button.State.PRESSED:
            foreground = self.pressed_colour

        screen_size = render_target.get_size()

        sc_s_x = (self.center[0] - self.size[0] / 2) * screen_size[0]
        sc_s_y = (self.center[1] - self.size[1] / 2) * screen_size[1]
        sc_w = self.size[0] * screen_size[0]
        sc_h = self.size[1] * screen_size[1]
        button_rect = (int(sc_s_x), int(sc_s_y), int(sc_w), int(sc_h))

        # draw the button itself
        pygame.draw.rect(render_target, foreground, button_rect)

        # draw the border
        pygame.draw.rect(render_target, self.border_colour, button_rect, self.border_width)

        # draw the text
        self.__text.render(render_target, self.center)

    def update_state(self, screen_size, mouse_pos, mouse_pressed):
        sc_s_x = (self.center[0] - self.size[0] / 2) * screen_size[0]
        sc_s_y = (self.center[1] - self.size[1] / 2) * screen_size[1]
        sc_e_x = (self.center[0] + self.size[0] / 2) * screen_size[0]
        sc_e_y = (self.center[1] + self.size[1] / 2) * screen_size[1]
        if sc_s_x <= mouse_pos[0] <= sc_e_x and sc_s_y <= mouse_pos[1] <= sc_e_y:
            if mouse_pressed[0]:
                if self.__state != Button.State.PRESSED:
                    self.on_press()
                self.__state = Button.State.PRESSED
            else:
                self.__state = Button.State.HOVER
        else:
            if mouse_pressed[0] and self.__state == Button.State.PRESSED:
                self.__state = Button.State.PRESSED
            else:
                self.__state = Button.State.DEFAULT

    def subscribe_event(self, event):
        self.__event_callbacks.append(event)

    def on_press(self):
        for event in self.__event_callbacks:
            event()

    @staticmethod
    def render_all(group, render_target):
        for b in Button.REGISTERED_BUTTONS[group]:
            b.render(render_target)

    @staticmethod
    def update_all(group, screen_size, mouse_pos, mouse_pressed):
        for b in Button.REGISTERED_BUTTONS[group]:
            b.update_state(screen_size, mouse_pos, mouse_pressed)
