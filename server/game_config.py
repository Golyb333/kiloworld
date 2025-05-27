import random

ip = '127.0.0.1'
port = 55555

class GameConfig:
    GAME_WIDTH = 1200
    GAME_HEIGHT = 900
    PLAYER_SIZE = 25
    PLAYER_VEL = 5
    MAX_HP = 30
    MIN_COMMAND_INTERVAL = 30
    CHAT_COOLDOWN = 2
    MATH_QUESTION_COOLDOWN = 60
    GRID_SIZE = 25
    
    RANDOM_NAMES = [
        'John', 'Masha', 'Vova', 'Sasha', 'Ivan', 'Petr', 'Olga', 'Sergey', 'Andrey', 'Natalia',
        'Victor', 'Lena', 'Dasha', 'Slava', 'Ilya', 'Kristina', 'Yana', 'Nikita', 'Artem', 'Denis',
        'Tanya', 'Roman', 'Marina', 'Oleg', 'Elena', 'Vadim', 'Alexey', 'Nastya', 'Maxim', 'Anya',
        'Daniil', 'Inna', 'Evgeniy', 'Svetlana', 'Konstantin', 'Irina', 'Timur', 'Galina', 'Dmitriy', 'Alina',
    ]
    
    PLAYER_COLORS = [
        [255, 0, 0], [0, 255, 0], [0, 0, 255], [255, 255, 0], [255, 0, 255],
        [0, 255, 255], [255, 128, 0], [128, 0, 255], [0, 128, 255], [128, 255, 0],
        [255, 128, 128], [128, 255, 128], [128, 128, 255], [192, 192, 192], [128, 128, 128]
    ]
    
    @staticmethod
    def get_random_name():
        return random.choice(GameConfig.RANDOM_NAMES)
    
    @staticmethod
    def get_random_color():
        return random.choice(GameConfig.PLAYER_COLORS)