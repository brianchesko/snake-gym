from tkinter import *
from time import time

import snake_impl.messages.message as Msg
from snake_impl.config import Config as Cfg
from snake_impl.view.game_view import GameView


def game_info_string(model, fps):
    return """Score: %d
Length: %d
Food eaten: %d
Time survived: %.2f seconds
FPS: %.2f""" % (model.score,
                len(model.segments),
                model.food_eaten,
                time() - model.game_start_time if model.started() and not model.ended() else model.last_update_time -
                                                                                             model.game_start_time,
                fps)


class GuiView(GameView, Canvas):
    fps_time_window = Cfg.debug.fps_time_window_ms / 1000

    def handle_other_keys(self, char):
        if char == 'w':
            self.controller_queue.put(Msg.Move.UP())
        elif char == 'a':
            self.controller_queue.put(Msg.Move.LEFT())
        elif char == 's':
            self.controller_queue.put(Msg.Move.DOWN())
        elif char == 'd':
            self.controller_queue.put(Msg.Move.RIGHT())
        else:
            if Cfg.debug.console_debug_info:
                print('Keypress', char, 'received')

    def toggle_show_info(self):
        curr_value = self.palette.text.info.show
        if curr_value:
            self.delete("info_text")
        print('Info toggled', 'off' if curr_value else 'on')
        self.palette.text.info.show = not curr_value

    def attempt_send_restart(self):
        self.controller_queue.put(Msg.GameAction.RESTART())

    def __init__(self, root, view_queue, controller_queue, board_width, board_height,
                 cell_size=Cfg.graphics.cell_size):
        Canvas.__init__(self, root, width=cell_size * board_width, height=cell_size * board_height)
        self.last_state = None
        self.root = root
        self.view_queue = view_queue
        self.controller_queue = controller_queue
        self.cell_size = cell_size
        self.board_width = board_width
        self.board_height = board_height
        self.canvas_width = cell_size * board_width
        self.canvas_height = cell_size * board_height
        self.palette = Cfg.graphics.palette
        self._line_width = self.palette.borders.thickness_px
        root.bind('<Left>', lambda _: self.controller_queue.put(Msg.Move.LEFT()))
        root.bind('<Right>', lambda _: self.controller_queue.put(Msg.Move.RIGHT()))
        root.bind('<Up>', lambda _: self.controller_queue.put(Msg.Move.UP()))
        root.bind('<Down>', lambda _: self.controller_queue.put(Msg.Move.DOWN()))
        root.bind('<Return>', lambda _: self.attempt_send_restart())
        root.bind('<space>', lambda _: self.attempt_send_restart())
        root.bind('<Escape>', lambda _: self.toggle_show_info())
        root.bind('<Key>', lambda event: self.handle_other_keys(event.char))
        self.fps_list = []  # a list of times frames were drawn in the last 3 seconds. can be utilized to determine FPS
        self.fps = -1
        self.draw_background()
        self.pack()
        self.focus_set()

    def enter_view_refresh_loop(self):
        self.after(int(Cfg.graphics.screen_update_millis), self.enter_view_refresh_loop)  # update again

        update_message = None
        count = 0
        while not self.view_queue.empty():
            count += 1
            update_message = self.view_queue.get()
        if count > 0:
            self.last_state = update_message.payload
            # print('\tdraw after:', time() - update_message.creation_time)
            self.refresh(self.last_state)  # perform the draw associated with the task
            for _ in range(count):  # finalize each of the updates
                self.view_queue.task_done()
        if self.palette.text.info.show:
            self.update_fps()
            self.delete("info_text")
            self.create_outlined_text(20, 20, text=game_info_string(self.last_state, self.fps),
                                      outline_color=self.palette.text.info.outline_color, offset=1,
                                      anchor="nw", font=('Arial', 16), fill=self.palette.text.info.main_color,
                                      tags="info_text")

    def draw_background(self):
        offset = self._line_width / 2
        self.create_rectangle(0, 0, self.canvas_width, self.canvas_height, fill=self.palette.main_background,
                              tags="background")

        for row in range(self.board_height + 1):
            y_pos = row * self.cell_size
            self.create_line(0, y_pos, self.canvas_width, y_pos, fill=self.palette.borders.color_major,
                             width=self._line_width, tags="gridlines")
        for col in range(self.board_width + 1):
            x_pos = col * self.cell_size
            self.create_line(x_pos, 0, x_pos, self.canvas_height,
                             fill=self.palette.borders.color_major, width=self._line_width, tags="gridlines")
        for row in range(self.board_height + 1):
            y_pos = row * self.cell_size
            self.create_line(0, y_pos, self.canvas_width, y_pos,
                             fill=self.palette.borders.color_minor, width=1, tags="gridlines")
        for col in range(self.board_width + 1):
            x_pos = col * self.cell_size
            self.create_line(x_pos, 0, x_pos, self.canvas_height,
                             fill=self.palette.borders.color_minor, width=1, tags="gridlines")

    def refresh(self, game):
        offset = self._line_width / 2
        self.delete("snake", "food", "text", "dot")

        for seg in game.segments:  # draw snake on screen
            self.draw_cell(seg, offset, self.palette.snake.color, tags="snake")

        self.draw_direction_dot(game.segments[0], 5, game.next_dir, radius_px=int(self.cell_size / 8))

        if game.food_pos is not None:
            self.draw_cell(game.food_pos, offset, self.palette.food.color, tags="food")

        if game.ended():
            self.fps_list.clear()
            if game.lost():
                self.create_outlined_text(self.canvas_width / 2, self.canvas_height / 2,
                                          outline_color=self.palette.text.game_over.outline_color, offset=1,
                                          anchor='center', text='Game Over',
                                          font=('Arial', 36), fill=self.palette.text.game_over.main_color, tags="text")
            else:  # game won
                self.create_outlined_text(self.canvas_width / 2, self.canvas_height / 2,
                                          outline_color=self.palette.text.victory.outline_color, offset=1,
                                          anchor='center', text='You win!',
                                          font=('Arial', 36), fill=self.palette.text.victory.main_color, tags="text")
            self.create_outlined_text(self.canvas_width / 2, self.canvas_height / 2 + 55,
                                      outline_color='black', offset=1,
                                      anchor='center', text='Final score: ' + str(game.score),
                                      font=('Arial', 24), fill='gold', tags="text")
        elif not game.started():  # game not started yet
            self.create_outlined_text(self.canvas_width / 2, self.canvas_height / 2,
                                      outline_color=self.palette.text.start_game.outline_color, offset=1,
                                      anchor='center', text='Press <Enter> to Play', font=('Arial', 22, 'bold'),
                                      fill=self.palette.text.start_game.main_color, tags="text")

    def update_fps(self):
        time_threshold = time() - GuiView.fps_time_window  # time before which to not consider

        self.fps_list.append(time())

        while len(self.fps_list) > 0 and self.fps_list[0] < time_threshold:
            self.fps_list.pop(0)

        # now only the last 3 seconds are in the list

        delta_time = self.fps_list[-1] - self.fps_list[0]
        self.fps = len(self.fps_list) / delta_time if len(self.fps_list) > 1 and delta_time > 0 else -1

    def draw_cell(self, nominal_cell, inward_scale_px, fill='black', tags=None):
        [x, y] = nominal_cell * self.cell_size
        # self.create_rectangle(x + inward_scale_px, y + inward_scale_px,
        #                       x + self.cell_size - inward_scale_px,
        #                       y + self.cell_size - inward_scale_px,
        #                       fill=fill, tags=tags)
        self.create_rectangle(x + inward_scale_px, y + inward_scale_px,
                              x + self.cell_size - inward_scale_px,
                              y + self.cell_size - inward_scale_px,
                              fill=fill, tags=tags)

    def create_outlined_text(self, *args, outline_color='black', offset=1, **kwargs):
        self.create_text(args[0] - offset, args[1] - offset, kwargs, fill=outline_color)
        self.create_text(args, kwargs)

    def draw_direction_dot(self, nominal_cell, dist_from_edge, direction, fill='white', radius_px=3):
        mid_dist = (self.cell_size - 2 * dist_from_edge) / 2
        [x, y] = nominal_cell * self.cell_size + self.cell_size / 2 + direction * mid_dist
        self.create_oval(x - radius_px, y - radius_px, x + radius_px, y + radius_px, fill=fill, tags='dot')
