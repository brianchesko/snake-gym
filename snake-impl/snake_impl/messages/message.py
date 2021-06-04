from snake_impl.model.game import Game
from time import time


class Message:
    def __init__(self, name, payload):
        self.name = name
        self.payload = payload
        self.creation_time = time()


class StateUpdated(Message):
    def __init__(self, payload):
        super().__init__('UpdateState', payload)


class GameAction(Message):
    def __init__(self, action_name, payload):
        super().__init__('GameAction', payload)
        self.action_name = action_name

    RESTART = lambda: GameAction('Restart', None)
    DO_NOTHING = lambda: GameAction('DoNothing', None)


class Move(GameAction):
    def __init__(self, dir_name, direction_array):
        super().__init__('Move', direction_array)
        self.dir_array = direction_array
        self.dir_name = dir_name

    LEFT = lambda: Move('Left', Game.LEFT)
    RIGHT = lambda: Move('Right', Game.RIGHT)
    UP = lambda: Move('Up', Game.UP)
    DOWN = lambda: Move('Down', Game.DOWN)
