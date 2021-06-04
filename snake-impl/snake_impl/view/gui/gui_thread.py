import threading
from snake_impl.view.gui.gui import Gui
from snake_impl.view.gui.gui_view import GuiView


class GuiThread(threading.Thread):
    # game width and height in cells, not actual px
    def __init__(self, view_queue, controller_queue, game_loop, game_width, game_height):
        threading.Thread.__init__(self)
        self.view_queue = view_queue
        self.controller_queue = controller_queue
        self.game_width = game_width
        self.game_height = game_height
        self.game_loop = game_loop
        self.start()

    def run(self):
        gui = Gui(self.game_loop)
        view = GuiView(gui, self.view_queue, self.controller_queue, self.game_width, self.game_height)
        view.enter_view_refresh_loop()
        gui.mainloop()
