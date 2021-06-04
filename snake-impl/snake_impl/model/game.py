from enum import Enum
import numpy as np
from snake_impl.config import Config as Cfg
import random


# Class for the game model
class Game:
    LEFT = np.array([-1, 0])
    RIGHT = np.array([1, 0])
    UP = np.array([0, -1])
    DOWN = np.array([0, 1])
    DIR_MAP = {'LEFT': LEFT, 'RIGHT': RIGHT, 'UP': UP, 'DOWN': DOWN}

    def __init__(self, width, height):
        self.score = 0
        self.width = width
        self.height = height
        self.growth_rate = Cfg.gameplay.growth_rate
        self.segments = [np.array([width // 2, height // 2])]
        initial_dir = Cfg.gameplay.initial_direction
        self.dir = self.DIR_MAP[initial_dir] if initial_dir != 'RANDOM' else random.choice(list(self.DIR_MAP.values()))
        self.next_dir = self.dir
        self.state = State.NOT_STARTED
        self.growth_queued = Cfg.gameplay.initial_size - 1
        self.food_eaten = 0
        self.food_pos = None
        self.game_start_time = -1
        self.last_update_time = -1

    def is_in_bounds(self, cell):
        [x, y] = cell
        return 0 <= x < self.width and 0 <= y < self.height

    def snake_contains(self, cell):
        for snake_cell in self.segments:
            if np.array_equal(snake_cell, cell):
                return True
        return False

    def started(self):
        return self.state != State.NOT_STARTED

    def ended(self):
        return self.state == State.LOST or self.state == State.WON

    def won(self):
        return self.state == State.WON

    def lost(self):
        return self.state == State.LOST


class State(Enum):
    NOT_STARTED = 0
    IN_PROGRESS = 1
    LOST = 2
    WON = 3
