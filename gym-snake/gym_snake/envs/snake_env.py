import gym
from gym import error, spaces, utils
import numpy as np
import math
from gym.utils import seeding
from snake_impl import Snake
from snake_impl.config import Config as GameConfig
import snake_impl.messages.message as msg


# no info for you
class SnakeInfo(object):
    def items(self):
        return {}


class SnakeEnv(gym.Env):
    metadata = {'render.modes': ['rgb_array', 'human']}

    food_encoding = -1
    # uses default reward space of (-inf, inf) float
    _action_set = [msg.Move.LEFT, msg.Move.RIGHT, msg.Move.UP, msg.Move.DOWN]
    action_space = spaces.Discrete(len(_action_set))
    empty_info = SnakeInfo()
    # observation space question: how to encode a possible (nxn) where each cell is {-1 (food), 0 (empty),
    # x = [0 OR 1 OR ... food_growth - 1 OR food_growth], x + 1, ... x + len(snake) - 1]}? is it necessary here?

    # if board shape is None, default to whatever the snake game impl picks
    def __init__(self, show=True, time_penalty=0.2, loss_penalty=50, board_shape=None):
        if board_shape is not None:
            self.snake = Snake(intermediate=True, out_view=show, width=board_shape[0], height=board_shape[1])
        else:
            self.snake = Snake(intermediate=True, out_view=show)
        self.snake.start()
        self.run_before = False
        self.new_state_queue = self.snake.v_int_queue
        self.update_view_queue = self.snake.v_out_queue
        self.send_action_queue = self.snake.c_queue
        self.previous_score = 0
        self.observation_space = spaces.Box(low=-math.inf, high=math.inf, shape=board_shape, dtype=np.int)
        self.game_over = False
        self.time_penalty = time_penalty  # penalty per tick (step)
        self.loss_penalty = loss_penalty  # penalty if it hits a wall or itself
        self.last_obs = None

    # action is 0 1 2 or 3 corresponding to either left right up or down
    def step(self, action):
        next_move_msg = SnakeEnv._action_set[action]()  # ignore warning, it's a discrete int
        self.send_action_queue.put(next_move_msg)  # put the message into the controller

        next_update = self.get_and_forward_state()
        game_state = next_update.payload

        obs = self.process_game_state(game_state)
        done = game_state.ended()
        reward = game_state.score - self.previous_score - self.time_penalty
        info = self.empty_info

        if done and game_state.lost():
            reward -= self.loss_penalty

        self.game_over = done
        self.previous_score = game_state.score

        self.last_obs = obs

        return np.copy(obs), reward, done, info

    def reset(self):
        if self.run_before:  # at least one game has been started
            self.previous_score = 0
            self.send_action_queue.put(msg.GameAction.RESTART())
            while not self.send_action_queue.empty():  # should REALLY be using task_done and join instead, but o well
                pass
        else:
            self.run_before = True

        # get the visual of the first game frame,
        update_msg = self.get_and_forward_state()
        processed_state = self.process_game_state(update_msg.payload)

        self.last_obs = processed_state

        return np.copy(processed_state)

    def render(self, mode='rgb_array', close=False):
        if mode == 'rgb_array':
            line_width = 3
            cell_width = 15
            gw = self.snake.game_width
            gh = self.snake.game_height
            drawing_width = ((cell_width + line_width) * gw) + line_width
            drawing_height = ((cell_width + line_width) * gh) + line_width
            num_seg = np.count_nonzero(self.last_obs >= 1)
            out = np.ones(shape=(drawing_width, drawing_height, 3))
            min_green = 0  # used to gradient the snake across blue shades
            max_green = 100
            for row in range(gh):
                for col in range(gw):
                    value = self.last_obs[col, row]
                    if value == SnakeEnv.food_encoding:
                        color = [255, 0, 0]
                    elif value == 0:
                        color = [0, 0, 0]
                    elif value > 0:
                        color = [0, int(min_green + (max_green - min_green) / num_seg * value), 255]
                    else:
                        color = [127, 127, 127]

                    out[col, row, :] = color
            return out

    def process_game_state(self, game_state):
        width = game_state.width
        height = game_state.height
        food = game_state.food_pos
        segs = game_state.segments
        buffer_inc = game_state.growth_queued  # number of growths buffered, so must be incremented to time alive
        snake_len = len(segs)

        self.game_over = game_state.ended()

        obs = np.zeros(shape=(width, height, 2))
        # note, index 0 is the head of the snake
        for i, seg in enumerate(segs):
            # put the amount of time each cell will be "turned on" in the matrix, head max number
            # obs[tuple(seg)] = (snake_len - i) + buffer_inc

            # put just the index and growth in, head will always be lowest
            # obs[tuple(seg)] = i + buffer_inc + 1

            # make the first channel of segments always 1, the second channel is the normalized index where head = 1
            seg_tuple = tuple(seg)
            obs[(*seg_tuple, 0)] = 1
            obs[(*seg_tuple, 1)] = 1 - (i / snake_len)

        obs[(*tuple(food), 0)] = SnakeEnv.food_encoding

        return obs

    def get_and_forward_state(self):
        new_state = self.new_state_queue.get(block=True)  # wait for an update
        # forward the update to the gui (if there is one)
        if self.update_view_queue is not None:
            self.update_view_queue.put(new_state)
        return new_state

    def enable_view(self):
        self.update_view_queue = self.snake.create_gui()
        self.human_visible_speed()

    def human_visible_speed(self):
        GameConfig.gameplay.ticks_per_second = 6
        GameConfig.update_dynamic_values()
