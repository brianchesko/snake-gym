from abc import ABC, abstractmethod


class GameView(ABC):
    @abstractmethod
    def refresh(self, game_model):
        pass
