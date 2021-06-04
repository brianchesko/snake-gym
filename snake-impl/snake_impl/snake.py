import asyncio
import queue

from snake_impl.model import Game
from snake_impl import GameController
from snake_impl.config import Config as Cfg
from snake_impl.view.gui import GuiThread

from threading import Thread


class Snake:
    def __init__(self, intermediate=False, out_view=True,
                 width=Cfg.gameplay.board.width, height=Cfg.gameplay.board.height):
        self.v_out_queue = queue.Queue() if out_view else None  # visual display queue, for final human reading
        # intermediate view queue, does preprocessing on view and forwards to v_out
        self.v_int_queue = queue.Queue() if intermediate else self.v_out_queue
        self.c_queue = queue.Queue()  # controller queue, used to send messages to controller
        self.has_out_view = out_view
        self.game_width = width
        self.game_height = height
        self.secondary_event_loop = asyncio.new_event_loop()

    async def initialize_system(self, loop):
        game = Game(self.game_width, self.game_height)
        controller = GameController(self.v_int_queue, self.c_queue, game)
        controller.start_controller(loop)

        if self.has_out_view:
            GuiThread(self.v_out_queue, self.c_queue, loop, self.game_width, self.game_height)

    def start(self):
        # new_loop = asyncio.new_event_loop()
        t = Thread(target=self._start, args=(self.secondary_event_loop,))
        t.start()

    def _start(self, loop):
        asyncio.set_event_loop(loop)
        asyncio.ensure_future(self.initialize_system(loop))
        loop.run_forever()

    # a one-time use method that will create a gui after the game has already started if it doesn't have one
    # returns the queue object that
    def create_gui(self):
        if self.has_out_view:
            return

        self.has_out_view = True
        self.v_out_queue = queue.Queue()
        GuiThread(self.v_out_queue, self.c_queue, self.secondary_event_loop, self.game_width, self.game_height)
        return self.v_out_queue


if __name__ == '__main__':
    snake = Snake()
    snake.start()
