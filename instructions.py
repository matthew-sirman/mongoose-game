class Instruction:
    SET_PROPERTY = "setp"
    START_GAME = "start"

    class Update:
        PLAYER_JOINED = "u_join"
        GAME_RUNNING = "u_running"
        QUIT_GAME = "u_quit"
        CHAT_MESSAGE = "u_message"

    class Game:
        PICKUP_CARD = "g_pickup"
        PLACE_CARD = "g_place"
        SEND_DECK = "g_send"
        MOVE_ENDED = "g_ended"
        CALL_MONGOOSE = "g_mongoose"
        FLIP_DECK = "g_flip"
