import numpy as np

import random
import asyncio
from time import time

from snake_impl.config.config import Config as Cfg
from snake_impl.model.game import Game
from snake_impl.model.game import State as GameState
import snake_impl.messages.message as Msg


# controller for the game object
class GameController:

    def __init__(self, view_queue, controller_queue, game):
        self.view_queue = view_queue
        self.controller_queue = controller_queue
        self.game = game
        self.generate_food()  # must be before the tick is sent out so we don't send out stale data
        self.view_queue.put(Msg.StateUpdated(game))

    def restart(self):
        if Cfg.debug.console_debug_info:
            print('Restart request acknowledged')
        # clear the event queues
        while not self.view_queue.empty():
            self.view_queue.get()
        while not self.controller_queue.empty():
            self.controller_queue.get()

        self.game = Game(self.game.width, self.game.height)
        self.generate_food()
        self.view_queue.put(Msg.StateUpdated(self.game))

    # advances the game by one tick, perform all necessary game actions
    def tick(self):
        # if we should only update when asked and there's no requests, skip this tick
        if Cfg.gameplay.block_until_action and self.controller_queue.empty():
            return

        # print('View queue:', self.view_queue.qsize(), 'control queue:', self.controller_queue.qsize())
        dir_request = self.game.next_dir
        while not self.controller_queue.empty():
            msg = self.controller_queue.get()

            if isinstance(msg, Msg.Move) and not self.game.ended():
                dir_request = msg.payload
                current_time = time()
                if not self.game.started():
                    self.start_game()
                # print('\tdir change honored:', current_time - msg.creation_time)
            elif isinstance(msg, Msg.GameAction):
                if msg.action_name == 'Restart':
                    if self.game.started():
                        self.restart()
                    else:
                        self.start_game()

            self.controller_queue.task_done()

        self.change_dir(dir_request)

        if not self.game.started() or self.game.ended():
            return

        self.game.last_update_time = time()

        snake = self.game.segments
        self.game.dir = self.game.next_dir
        head = snake[0]
        new_head = head + self.game.dir

        # only advance game state if we didn't just die
        if self.game.is_in_bounds(new_head):
            if self.np_arr_in_list(snake, new_head):  # snake will collide with itself
                self.game_over()
                return

            if self.game.growth_queued > 0:  # check whether to lengthen snake or just move it
                self.game.growth_queued -= 1
            else:
                snake.pop()

            snake.insert(0, new_head)  # move head of snake

            if np.array_equal(self.game.food_pos, new_head):
                self.game.food_eaten += 1
                self.game.score += Cfg.gameplay.scoring.food_eaten
                board_size = self.game.width * self.game.height
                if len(self.game.segments) == board_size:  # board is full, we won
                    self.game.score += int(board_size / 2) + Cfg.gameplay.scoring.winning_extra
                    self.game.state = GameState.WON
                    self.game.food_pos = None
                else:
                    self.game.growth_queued += self.game.growth_rate
                    self.generate_food()

        else:
            self.game_over()
            return

        self.view_queue.put(Msg.StateUpdated(self.game))

    def game_over(self):
        if Cfg.debug.console_debug_info:
            print("""Game over.
            Final score: %d
            Final length: %d
            Food eaten: %d
            Time survived: %.2f seconds""" %
                  (self.game.score,
                   len(self.game.segments),
                   self.game.food_eaten,
                   time() - self.game.game_start_time))
        self.game.state = GameState.LOST
        self.view_queue.put(Msg.StateUpdated(self.game))

    def generate_food(self):
        legal_spaces = []
        for i in range(self.game.width):
            for j in range(self.game.height):
                cell = np.array([i, j])
                if not self.np_arr_in_list(self.game.segments, cell):
                    legal_spaces.append(cell)
        new_food = random.choice(legal_spaces)
        self.game.food_pos = new_food
        return new_food

    @staticmethod
    def np_arr_in_list(coll, arr):
        for item in coll:
            if np.array_equal(item, arr):
                return True
        return False

    # adapted from a StackOverflow answer
    async def periodic(self, loop, period):
        def game_tick_gen():
            t = loop.time()
            prev_period = period
            count = 0
            while True:
                new_period = Cfg.gameplay.game_tick_sec
                # reset period counter if the period was changed for some reason (happens when going from
                # training to visualization for RL project)
                if new_period is not prev_period:
                    print('Game controller tick rate modified, now looping every', new_period, 'seconds')
                    prev_period = new_period
                    count = 0
                    t = loop.time()
                count += 1
                yield max(t + count * prev_period - loop.time(), 0)

        gen = game_tick_gen()

        while True:
            self.tick()
            await asyncio.sleep(next(gen))

    def start_controller(self, event_loop):
        # start_time = time.time()
        print('Initializing game controller')

        event_loop.create_task(self.periodic(event_loop, Cfg.gameplay.game_tick_sec))
        # await self._periodic.start()

    def start_game(self):
        self.game.state = GameState.IN_PROGRESS
        self.game.game_start_time = time()
        if Cfg.debug.console_debug_info:
            print('New game started at time', self.game.game_start_time)

    def change_dir(self, new_dir):
        opposite_game_dir = self.game.dir * -1
        if (not np.array_equal(new_dir, opposite_game_dir) and not np.array_equal(self.game.dir, new_dir)) \
                or len(self.game.segments) is 1:
            self.game.next_dir = new_dir
