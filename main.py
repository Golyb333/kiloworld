import pygame
import socket
import threading
import json
import time
BASE_WIDTH = 1200
BASE_HEIGHT = 900
width = BASE_WIDTH
height = BASE_HEIGHT
PLAYER_SIZE = 25
pygame.init()
pygame.font.init()
win = pygame.display.set_mode((width, height), pygame.RESIZABLE)
pygame.display.set_caption("kiloworld")
ip = '127.0.0.1'
port = 55555
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((ip, port))
players = {}
visual_players = {}
chat_messages = []
grid_cells = {}
current_message = ""
chat_active = False
server_message = {
    'text': '',
    'color': (255, 255, 255),
    'end_time': 0
}
font = pygame.font.SysFont('Arial', 16)
MOVEMENT_INTERPOLATION_SPEED = 0.15
message_history = []
history_index = -1
temp_message = ""
cursor_pos = 0
MAX_HISTORY = 50
MAX_CHAT_MESSAGES = 50
chat_scroll = 0
CHAT_FADE_TIME = 5.0
last_chat_activity = time.time()

def scale_x(x):
    return int(x * width / BASE_WIDTH)
def scale_y(y):
    return int(y * height / BASE_HEIGHT)
def scale_font_size(size):
    scale_factor = min(width / BASE_WIDTH, height / BASE_HEIGHT)
    return int(size * scale_factor)
def receive():
    global players, chat_messages, last_chat_activity
    while True:
        try:
            data = s.recv(1024).decode()
            for line in data.split('\n'):
                if not line.strip():
                    continue
                if line.startswith('/state '):
                    state = json.loads(line[7:])
                    players = state['players']
                    if 'grid_cells' in state:
                        global grid_cells
                        grid_cells = state['grid_cells']
                    for player_id, player_data in players.items():
                        if player_id not in visual_players:
                            visual_players[player_id] = player_data.copy()
                        else:
                            visual_players[player_id]['name'] = player_data.get('name', 'Unknown')
                            visual_players[player_id]['hp'] = player_data.get('hp', 100)
                            visual_players[player_id]['message'] = player_data.get('message')
                            visual_players[player_id]['message_time'] = player_data.get('message_time', 0)
                elif line.startswith('/server_msg ') or line.startswith('[CHAT]') or line.startswith('[SERVER]') or line.startswith('[Gem Game]'):
                    last_chat_activity = time.time()
                    if len(chat_messages) >= MAX_CHAT_MESSAGES:
                        chat_messages.pop(0)
                    if line.startswith('/server_msg '):
                        parts = line.split(' ', 2)
                        if len(parts) == 3:
                            color_hex = parts[1]
                            message = parts[2]
                            chat_messages.append({
                                'text': message,
                                'color': color_hex,
                                'time': time.time()
                            })
                    else:
                        chat_messages.append({
                            'text': line,
                            'color': None,
                            'time': time.time()
                        })
                elif line.startswith('/popup '):
                    parts = line.split(' ', 2)
                    if len(parts) == 3:
                        color_hex = parts[1]
                        message = parts[2]
                        r = int(color_hex[1:3], 16)
                        g = int(color_hex[3:5], 16)
                        b = int(color_hex[5:7], 16)
                        server_message['text'] = message
                        server_message['color'] = (r, g, b)
                        server_message['end_time'] = time.time() + 5
        except Exception as e:
            print(f"Error in receive: {e}")
            break
receive_thread = threading.Thread(target=receive, daemon=True)
receive_thread.start()
def update_visual_positions():
    for player_id, player_data in players.items():
        if player_id in visual_players:
            visual_players[player_id]['x'] += (player_data['x'] - visual_players[player_id]['x']) * MOVEMENT_INTERPOLATION_SPEED
            visual_players[player_id]['y'] += (player_data['y'] - visual_players[player_id]['y']) * MOVEMENT_INTERPOLATION_SPEED
            visual_players[player_id]['color'] = player_data['color']
        else:
            visual_players[player_id] = player_data.copy()
    for player_id in list(visual_players.keys()):
        if player_id not in players:
            del visual_players[player_id]
def draw_chat():
    chat_font = pygame.font.SysFont('Arial', scale_font_size(16))
    line_height = scale_y(20)
    chat_padding = scale_x(10)
    chat_width = width // 3
    chat_height = scale_y(220)
    chat_x = scale_x(10)
    chat_y = height - chat_height - scale_y(10)
    base_alpha = 255
    if not chat_active:
        fade_time = time.time() - last_chat_activity - CHAT_FADE_TIME
        if fade_time > 0:
            base_alpha = max(40, 255 - int((fade_time * 195) ** 0.7))
    chat_surface = pygame.Surface((chat_width, chat_height), pygame.SRCALPHA)
    bg_color = (40, 44, 52, min(180, int(base_alpha * 0.7)))
    border_color = (70, 75, 85, min(100, int(base_alpha * 0.4)))
    pygame.draw.rect(chat_surface, bg_color, 
                    (0, 0, chat_width, chat_height), 
                    border_radius=scale_x(8))
    pygame.draw.rect(chat_surface, border_color,
                    (0, 0, chat_width, chat_height),
                    scale_x(1), border_radius=scale_x(8))
    visible_messages = chat_messages[max(0, len(chat_messages) - 10 - chat_scroll):len(chat_messages) - chat_scroll]
    for i, msg in enumerate(visible_messages):
        if isinstance(msg, dict):
            if msg['color']:
                try:
                    r = int(msg['color'][1:3], 16)
                    g = int(msg['color'][3:5], 16)
                    b = int(msg['color'][5:7], 16)
                    color = (r, g, b, base_alpha)
                except ValueError:
                    color = (220, 223, 228, base_alpha)
            else:
                color = (220, 223, 228, base_alpha)
            text = msg['text']
        else:
            color = (220, 223, 228, base_alpha)
            text = msg
        shadow_color = (20, 22, 26, min(100, base_alpha // 2))
        shadow_surface = chat_font.render(text, True, shadow_color)
        text_surface = chat_font.render(text, True, color)
        y_pos = chat_height - (len(visible_messages) - i) * line_height - scale_y(5)
        chat_surface.blit(shadow_surface, (chat_padding + 1, y_pos + 1))
        chat_surface.blit(text_surface, (chat_padding, y_pos))
    if len(chat_messages) > 10:
        scroll_width = scale_x(4)
        scroll_height = chat_height * (10 / len(chat_messages))
        scroll_pos = chat_height - scroll_height - (chat_height - scroll_height) * (chat_scroll / (len(chat_messages) - 10))
        pygame.draw.rect(chat_surface, (70, 75, 85, min(40, base_alpha)),
                        (chat_width - scroll_width - scale_x(4), 0,
                         scroll_width, chat_height),
                        border_radius=scroll_width//2)
        pygame.draw.rect(chat_surface, (100, 105, 115, min(120, base_alpha)),
                        (chat_width - scroll_width - scale_x(4), scroll_pos,
                         scroll_width, scroll_height),
                        border_radius=scroll_width//2)
    win.blit(chat_surface, (chat_x, chat_y))
    if chat_active:
        input_height = line_height + chat_padding
        input_surface = pygame.Surface((chat_width, input_height), pygame.SRCALPHA)
        input_bg_color = (50, 55, 65, 230)
        input_border_color = (80, 85, 95, 60)
        pygame.draw.rect(input_surface, input_bg_color,
                        (0, 0, chat_width, input_height),
                        border_radius=scale_x(6))
        pygame.draw.rect(input_surface, input_border_color,
                        (0, 0, chat_width, input_height),
                        scale_x(1), border_radius=scale_x(6))
        text_color = (230, 233, 238)
        if current_message:
            text_before_cursor = chat_font.render("> " + current_message[:cursor_pos], True, text_color)
            text = chat_font.render("> " + current_message, True, text_color)
            input_surface.blit(text, (chat_padding, chat_padding // 2))
            if time.time() % 1 > 0.5:
                cursor_x = chat_padding + text_before_cursor.get_width()
                cursor_y = chat_padding // 2
                cursor_color = (200, 203, 208, 200)
                pygame.draw.line(input_surface, cursor_color,
                               (cursor_x, cursor_y + 2),
                               (cursor_x, cursor_y + line_height - 2))
        else:
            text = chat_font.render("> ", True, text_color)
            input_surface.blit(text, (chat_padding, chat_padding // 2))
            if time.time() % 1 > 0.5:
                cursor_x = chat_padding + text.get_width()
                cursor_y = chat_padding // 2
                cursor_color = (200, 203, 208, 200)
                pygame.draw.line(input_surface, cursor_color,
                               (cursor_x, cursor_y + 2),
                               (cursor_x, cursor_y + line_height - 2))
        win.blit(input_surface, (chat_x, chat_y - input_height - scale_y(5)))

def redrawWindow():
    win.fill((255, 255, 255))
    grid_size = scale_x(25)
    cells_x = width // grid_size
    cells_y = height // grid_size
    max_cells_x = BASE_WIDTH // 25
    max_cells_y = BASE_HEIGHT // 25
    cells_x = min(cells_x, max_cells_x)
    cells_y = min(cells_y, max_cells_y)
    for y in range(cells_y):
        for x in range(cells_x):
            screen_x = x * grid_size
            screen_y = y * grid_size
            base_x = x * 25
            base_y = y * 25
            cell_key = f"{base_x},{base_y}"
            if cell_key in grid_cells:
                color_hex = grid_cells[cell_key]
                r = int(color_hex[1:3], 16)
                g = int(color_hex[3:5], 16)
                b = int(color_hex[5:7], 16)
                pygame.draw.rect(win, (r, g, b), (screen_x, screen_y, grid_size, grid_size))
    for x in range(cells_x + 1):
        pygame.draw.line(win, (230, 230, 230), (x * grid_size, 0), (x * grid_size, cells_y * grid_size))
    for y in range(cells_y + 1):
        pygame.draw.line(win, (230, 230, 230), (0, y * grid_size), (cells_x * grid_size, y * grid_size))
    update_visual_positions()
    scaled_player_size = scale_x(PLAYER_SIZE)
    current_time = time.time()
    for player_id, p in list(visual_players.items()):
        scaled_x = scale_x(p['x'])
        scaled_y = scale_y(p['y'])
        pygame.draw.rect(win, p['color'], (scaled_x, scaled_y, scaled_player_size, scaled_player_size))
        scaled_font = pygame.font.SysFont('Arial', scale_font_size(16))
        player_name = p.get('name', f'Player {player_id[-1]}')
        name_text = scaled_font.render(player_name, True, (50, 50, 50))
        win.blit(name_text, (scaled_x + scaled_player_size//2 - name_text.get_width()//2, scaled_y - scale_y(30)))
        hp = p.get('hp', 30)
        hp_width = scaled_player_size
        hp_height = scale_y(5)
        if hp > 0:
            pygame.draw.rect(win, (0, 255, 0), (scaled_x, scaled_y - scale_y(10), int(hp_width * (hp / 30)), hp_height))
            for i in range(1, 3):
                divider_pos = scaled_x + int((hp_width / 3) * i)
                pygame.draw.rect(win, (0, 0, 0), (divider_pos, scaled_y - scale_y(10), 1, hp_height))
        message = p.get('message')
        message_time = p.get('message_time', 0)
        if message and current_time - message_time < 2:
            msg_text = scaled_font.render(message, True, (0, 0, 0))
            msg_bg = pygame.Surface((msg_text.get_width() + scale_x(10), msg_text.get_height() + scale_y(6)), pygame.SRCALPHA)
            msg_bg.fill((255, 255, 255, 200))
            pygame.draw.rect(msg_bg, (0, 0, 0), (0, 0, msg_bg.get_width(), msg_bg.get_height()), 2)
            win.blit(msg_bg, (scaled_x + scaled_player_size//2 - msg_text.get_width()//2 - scale_x(5), scaled_y - scale_y(60)))
            win.blit(msg_text, (scaled_x + scaled_player_size//2 - msg_text.get_width()//2, scaled_y - scale_y(57)))
    draw_chat()
    current_time = time.time()
    if server_message['text'] and current_time < server_message['end_time']:
        popup_font = pygame.font.SysFont('Arial', scale_font_size(24), bold=True)
        popup_text = popup_font.render(server_message['text'], True, (0, 0, 0))
        padding = scale_x(30)
        popup_surface = pygame.Surface((popup_text.get_width() + padding * 2, 
                                      popup_text.get_height() + padding), 
                                     pygame.SRCALPHA)
        pygame.draw.rect(popup_surface, (255, 255, 255, 230), 
                        (0, 0, popup_surface.get_width(), popup_surface.get_height()), 
                        border_radius=10)
        pygame.draw.rect(popup_surface, (0, 0, 0, 200), 
                        (0, 0, popup_surface.get_width(), popup_surface.get_height()), 
                        3, border_radius=10)
        popup_surface.blit(popup_text, 
                         (popup_surface.get_width()//2 - popup_text.get_width()//2, 
                          popup_surface.get_height()//2 - popup_text.get_height()//2))
        win.blit(popup_surface, 
                (width//2 - popup_surface.get_width()//2, 
                 scale_y(40)))
    pygame.display.update()
def main():
    global current_message, chat_active, width, height, win, history_index, temp_message, cursor_pos, chat_scroll, last_chat_activity
    run = True
    clock = pygame.time.Clock()
    movement_buffer = {"left": False, "right": False, "up": False, "down": False}
    last_movement_time = 0
    movement_cooldown = 30
    while run:
        clock.tick(60)
        current_time = pygame.time.get_ticks()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
                pygame.quit()
                s.close()
                break
            if event.type == pygame.VIDEORESIZE:
                width, height = event.size
                win = pygame.display.set_mode((width, height), pygame.RESIZABLE)
            if event.type == pygame.MOUSEWHEEL:
                if chat_active or time.time() - last_chat_activity < CHAT_FADE_TIME:
                    chat_scroll = max(0, min(len(chat_messages) - 10, chat_scroll - event.y))
                    last_chat_activity = time.time()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    if chat_active and current_message:
                        s.sendall(f"/chat {current_message}\n".encode())
                        if not message_history or message_history[-1] != current_message:
                            message_history.append(current_message)
                            if len(message_history) > MAX_HISTORY:
                                message_history.pop(0)
                        history_index = -1
                        current_message = ""
                        cursor_pos = 0
                        chat_active = False
                    else:
                        movement_buffer = {"left": False, "right": False, "up": False, "down": False}
                        chat_active = True
                elif event.key == pygame.K_ESCAPE:
                    if chat_active:
                        chat_active = False
                        current_message = ""
                        cursor_pos = 0
                        history_index = -1
                elif chat_active:
                    mods = pygame.key.get_mods()
                    if event.key == pygame.K_UP:
                        if history_index == -1:
                            temp_message = current_message
                        if message_history and history_index < len(message_history) - 1:
                            history_index += 1
                            current_message = message_history[-(history_index + 1)]
                            cursor_pos = len(current_message)
                    elif event.key == pygame.K_DOWN:
                        if history_index > 0:
                            history_index -= 1
                            current_message = message_history[-(history_index + 1)]
                            cursor_pos = len(current_message)
                        elif history_index == 0:
                            history_index = -1
                            current_message = temp_message
                            cursor_pos = len(current_message)
                    elif event.key == pygame.K_LEFT:
                        if mods & pygame.KMOD_CTRL:
                            while cursor_pos > 0 and current_message[cursor_pos-1].isspace():
                                cursor_pos -= 1
                            while cursor_pos > 0 and not current_message[cursor_pos-1].isspace():
                                cursor_pos -= 1
                        else:
                            cursor_pos = max(0, cursor_pos - 1)
                    elif event.key == pygame.K_RIGHT:
                        if mods & pygame.KMOD_CTRL:
                            while cursor_pos < len(current_message) and current_message[cursor_pos].isspace():
                                cursor_pos += 1
                            while cursor_pos < len(current_message) and not current_message[cursor_pos].isspace():
                                cursor_pos += 1
                        else:
                            cursor_pos = min(len(current_message), cursor_pos + 1)
                    elif event.key == pygame.K_HOME:
                        cursor_pos = 0
                    elif event.key == pygame.K_END:
                        cursor_pos = len(current_message)
                    elif event.key == pygame.K_BACKSPACE:
                        if mods & pygame.KMOD_CTRL:
                            temp_pos = cursor_pos
                            while cursor_pos > 0 and current_message[cursor_pos-1].isspace():
                                cursor_pos -= 1
                            while cursor_pos > 0 and not current_message[cursor_pos-1].isspace():
                                cursor_pos -= 1
                            current_message = current_message[:cursor_pos] + current_message[temp_pos:]
                        elif cursor_pos > 0:
                            current_message = current_message[:cursor_pos-1] + current_message[cursor_pos:]
                            cursor_pos -= 1
                    elif event.key == pygame.K_DELETE:
                        if cursor_pos < len(current_message):
                            current_message = current_message[:cursor_pos] + current_message[cursor_pos+1:]
                    elif event.unicode and event.unicode.isprintable():
                        current_message = current_message[:cursor_pos] + event.unicode + current_message[cursor_pos:]
                        cursor_pos += 1
                        history_index = -1
                if not chat_active:
                    if event.key == pygame.K_a:
                        movement_buffer["left"] = True
                    if event.key == pygame.K_d:
                        movement_buffer["right"] = True
                    if event.key == pygame.K_w:
                        movement_buffer["up"] = True
                    if event.key == pygame.K_s:
                        movement_buffer["down"] = True
                    if event.key == pygame.K_q:
                        movement_buffer["up"] = True
                        movement_buffer["left"] = True
                    if event.key == pygame.K_e:
                        movement_buffer["up"] = True
                        movement_buffer["right"] = True
                    if event.key == pygame.K_z:
                        movement_buffer["down"] = True
                        movement_buffer["left"] = True
                    if event.key == pygame.K_c:
                        movement_buffer["down"] = True
                        movement_buffer["right"] = True
            if event.type == pygame.KEYUP:
                if event.key == pygame.K_a:
                    movement_buffer["left"] = False
                if event.key == pygame.K_d:
                    movement_buffer["right"] = False
                if event.key == pygame.K_w:
                    movement_buffer["up"] = False
                if event.key == pygame.K_s:
                    movement_buffer["down"] = False
                if event.key == pygame.K_q or event.key == pygame.K_z:
                    if not pygame.key.get_pressed()[pygame.K_LEFT] and not pygame.key.get_pressed()[pygame.K_a]:
                        movement_buffer["left"] = False
                    if not pygame.key.get_pressed()[pygame.K_UP] and not pygame.key.get_pressed()[pygame.K_w]:
                        movement_buffer["up"] = False
                if event.key == pygame.K_e or event.key == pygame.K_c:
                    if not pygame.key.get_pressed()[pygame.K_RIGHT] and not pygame.key.get_pressed()[pygame.K_d]:
                        movement_buffer["right"] = False
                    if not pygame.key.get_pressed()[pygame.K_DOWN] and not pygame.key.get_pressed()[pygame.K_s]:
                        movement_buffer["down"] = False
        if not chat_active and current_time - last_movement_time > movement_cooldown:
            if movement_buffer["left"] and movement_buffer["up"]:
                s.sendall(b"/move upleft\n")
                last_movement_time = current_time
            elif movement_buffer["left"] and movement_buffer["down"]:
                s.sendall(b"/move downleft\n")
                last_movement_time = current_time
            elif movement_buffer["right"] and movement_buffer["up"]:
                s.sendall(b"/move upright\n")
                last_movement_time = current_time
            elif movement_buffer["right"] and movement_buffer["down"]:
                s.sendall(b"/move downright\n")
                last_movement_time = current_time
            elif movement_buffer["left"]:
                s.sendall(b"/move left\n")
                last_movement_time = current_time
            elif movement_buffer["right"]:
                s.sendall(b"/move right\n")
                last_movement_time = current_time
            elif movement_buffer["up"]:
                s.sendall(b"/move up\n")
                last_movement_time = current_time
            elif movement_buffer["down"]:
                s.sendall(b"/move down\n")
                last_movement_time = current_time
        redrawWindow()
if __name__ == "__main__":
    main()