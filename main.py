import pygame
import socket
import threading
import json
import time

width = 800
height = 600
PLAYER_SIZE = 30
pygame.init()
pygame.font.init()
win = pygame.display.set_mode((width, height))
pygame.display.set_caption("kiloworld")

ip = '127.0.0.1'
port = 55555
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((ip, port))
players = {}
visual_players = {}
chat_messages = []
current_message = ""
chat_active = False
font = pygame.font.SysFont('Arial', 16)
MOVEMENT_INTERPOLATION_SPEED = 0.15

def receive():
    global players
    while True:
        try:
            data = s.recv(1024).decode()
            for line in data.split('\n'):
                if not line.strip():
                    continue
                if line.startswith('/state '):
                    state = json.loads(line[7:])
                    players = state['players']
                    for player_id, player_data in players.items():
                        if player_id not in visual_players:
                            visual_players[player_id] = player_data.copy()
                        else:
                            visual_players[player_id]['name'] = player_data.get('name', 'Unknown')
                            visual_players[player_id]['hp'] = player_data.get('hp', 100)
                            visual_players[player_id]['message'] = player_data.get('message')
                            visual_players[player_id]['message_time'] = player_data.get('message_time', 0)
                elif line.startswith('[CHAT]') or line.startswith('[SERVER]'):
                    chat_messages.append(line)
                    if len(chat_messages) > 10:
                        chat_messages.pop(0)
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

def redrawWindow():
    win.fill((255, 255, 255))
    
    grid_size = 50
    for x in range(0, width, grid_size):
        pygame.draw.line(win, (230, 230, 230), (x, 0), (x, height))
    for y in range(0, height, grid_size):
        pygame.draw.line(win, (230, 230, 230), (0, y), (width, y))
    
    update_visual_positions()
    
    current_time = time.time()
    for player_id, p in visual_players.items():
        pygame.draw.rect(win, p['color'], (p['x'], p['y'], PLAYER_SIZE, PLAYER_SIZE))
        
        player_name = p.get('name', f'Player {player_id[-1]}')
        name_text = font.render(player_name, True, (50, 50, 50))
        win.blit(name_text, (p['x'] + PLAYER_SIZE//2 - name_text.get_width()//2, p['y'] - 30))
        
        hp = p.get('hp', 30)
        hp_width = PLAYER_SIZE
        hp_height = 5
        if hp > 0:
            pygame.draw.rect(win, (0, 255, 0), (p['x'], p['y'] - 10, int(hp_width * (hp / 30)), hp_height))
            for i in range(1, 3):
                divider_pos = p['x'] + int((hp_width / 3) * i)
                pygame.draw.rect(win, (0, 0, 0), (divider_pos, p['y'] - 10, 1, hp_height))
        
        message = p.get('message')
        message_time = p.get('message_time', 0)
        
        if message and current_time - message_time < 2:
            msg_text = font.render(message, True, (0, 0, 0))
            msg_bg = pygame.Surface((msg_text.get_width() + 10, msg_text.get_height() + 6), pygame.SRCALPHA)
            msg_bg.fill((255, 255, 255, 200))
            pygame.draw.rect(msg_bg, (0, 0, 0), (0, 0, msg_bg.get_width(), msg_bg.get_height()), 2)
            win.blit(msg_bg, (p['x'] + PLAYER_SIZE//2 - msg_text.get_width()//2 - 5, p['y'] - 60))
            win.blit(msg_text, (p['x'] + PLAYER_SIZE//2 - msg_text.get_width()//2, p['y'] - 57))
    
    for i, msg in enumerate(chat_messages):
        text = font.render(msg, True, (0, 0, 0))
        win.blit(text, (10, height - 200 + i * 20))
    
    if chat_active and current_message:
        text = font.render("> " + current_message, True, (0, 0, 0))
        win.blit(text, (10, height - 220))
    elif chat_active:
        text = font.render("> ", True, (0, 0, 0))
        win.blit(text, (10, height - 220))
    
    pygame.display.update()

def main():
    global current_message, chat_active
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
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    if chat_active and current_message:
                        s.sendall(f"/chat {current_message}\n".encode())
                        current_message = ""
                        chat_active = False
                    else:
                        chat_active = True
                elif event.key == pygame.K_ESCAPE:
                    chat_active = False
                    current_message = ""
                elif event.key == pygame.K_BACKSPACE and chat_active:
                    current_message = current_message[:-1]
                elif chat_active:
                    current_message += event.unicode
                
                if event.key == pygame.K_LEFT:
                    movement_buffer["left"] = True
                if event.key == pygame.K_RIGHT:
                    movement_buffer["right"] = True
                if event.key == pygame.K_UP:
                    movement_buffer["up"] = True
                if event.key == pygame.K_DOWN:
                    movement_buffer["down"] = True
            
            if event.type == pygame.KEYUP:
                if event.key == pygame.K_LEFT:
                    movement_buffer["left"] = False
                if event.key == pygame.K_RIGHT:
                    movement_buffer["right"] = False
                if event.key == pygame.K_UP:
                    movement_buffer["up"] = False
                if event.key == pygame.K_DOWN:
                    movement_buffer["down"] = False
        
        if current_time - last_movement_time > movement_cooldown:
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