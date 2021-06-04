from snake_impl.util import Periodic
from snake_impl.view.game_view import GameView
import numpy as np


class ConsoleView(GameView):

    def __init__(self, controller):
        self.symbols = {'food': 'X', 'empty': '·', 'snake': 'o'}  # ☐
        self.controller = controller
        self._console_listener = Periodic(self.trigger_console_inputs, 0.01)

    def update(self, game):
        print()
        for y in range(game.height):
            for x in range(game.width):
                cell = np.array([x, y])
                value = 'food' if np.array_equal(cell, game.food_pos) else 'empty'
                if game.snake_contains(cell):
                    value = 'snake'
                print(self.symbols[value], end="")
            print()

    async def initialize(self):
        print('starting console reading')
        
        await self._console_listener.start()
