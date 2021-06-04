import json
import os

# defines constants for the game on an object


class Config:
    @staticmethod
    def update_dynamic_values():
        Config.gameplay.game_tick_sec = 1 / Config.gameplay.ticks_per_second
        Config.gameplay.game_tick_millis = 1000 / Config.gameplay.ticks_per_second
        Config.graphics.screen_update_sec = 1 / Config.graphics.frames_per_second
        Config.graphics.screen_update_millis = 1000 / Config.graphics.frames_per_second


# creates classes and writes attributes on them recursively from an input dictionary
def write_attributes(curr_class, curr_dict):
    for (dict_key, dict_value) in curr_dict.items():
        if isinstance(dict_value, dict):  # its another dictionary, recurse
            new_type = type(curr_class.__name__ + dict_key, (object,), {"__init__": lambda _: None})
            setattr(curr_class, dict_key, new_type())
            write_attributes(new_type, dict_value)
        else:
            setattr(curr_class, dict_key, dict_value)


# next line from StackOverflow, resolves getting correct path on multiple operating systems
__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
with open(os.path.join(__location__, 'config.json')) as config_file:
    data = json.load(config_file)
    write_attributes(Config, data)
    Config.update_dynamic_values()

