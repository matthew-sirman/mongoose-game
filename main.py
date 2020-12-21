from mongoose import Mongoose
from title_screen import TitleScreen


def main():
    t_screen = TitleScreen()
    active_id, players, client_socket, deck = t_screen.run()

    game = Mongoose(client_socket, deck)
    game.setup_game(active_id, players)

    game.run()


if __name__ == "__main__":
    main()
