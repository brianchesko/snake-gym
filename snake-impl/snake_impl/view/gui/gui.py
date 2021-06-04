import tkinter
import asyncio


class Gui(tkinter.Tk):
    def on_close(self, game_loop):
        self.quit()
        self.destroy()
        game_loop.stop()

    def __init__(self, game_loop):
        super().__init__()
        self.title('Snake Environment')
        self.protocol("WM_DELETE_WINDOW", lambda: self.on_close(game_loop))
