import socket
import threading
import time
import json
import random
from datetime import datetime

class GameServer:
    def __init__(self):
        self.server_running = False
        self.server_thread = None
        self.players = {}
        self.lock = threading.Lock()
        
        self.MIN_COMMAND_INTERVAL = 30
        self.CHAT_LAST_MESSAGE_TIME = 0
        self.GAME_WIDTH = 1200
        self.GAME_HEIGHT = 900
        self.PLAYER_SIZE = 25
        self.PLAYER_VEL = 5
        self.MAX_HP = 30
        self.last_command_time = {}
        self.inventory = {}
        self.player_messages = {}
        
        self.player_gems = {}
        self.current_math_question = None
        self.math_question_time = 0
        self.math_question_cooldown = 60
        self.last_math_question_time = 0
        
        self.grid_cells = {}
        self.grid_size = 25
        
        self.random_names = [
            'John', 'Masha', 'Vova', 'Sasha', 'Ivan', 'Petr', 'Olga', 'Sergey', 'Andrey', 'Natalia',
            'Victor', 'Lena', 'Dasha', 'Slava', 'Ilya', 'Kristina', 'Yana', 'Nikita', 'Artem', 'Denis',
            'Tanya', 'Roman', 'Marina', 'Oleg', 'Elena', 'Vadim', 'Alexey', 'Nastya', 'Maxim', 'Anya',
            'Daniil', 'Inna', 'Evgeniy', 'Svetlana', 'Konstantin', 'Irina', 'Timur', 'Galina', 'Dmitriy', 'Alina',
        ]
        
        self.player_colors = [
            [255, 0, 0], [0, 255, 0], [0, 0, 255], [255, 255, 0], [255, 0, 255],
            [0, 255, 255], [255, 128, 0], [128, 0, 255], [0, 128, 255], [128, 255, 0],
            [255, 128, 128], [128, 255, 128], [128, 128, 255], [192, 192, 192], [128, 128, 128]
        ]
    
    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
    
    def update_client_list(self):
        with self.lock:
            self.log(f"Connected Clients ({len(self.players)}): {', '.join([f"{pid} - {p.get('name', 'Unknown')}" for pid, p in self.players.items()])}")
    
    def start_server(self):
        if not self.server_running:
            self.server_thread = threading.Thread(target=self.run_server, daemon=True)
            self.server_thread.start()
            self.log(f"Server started on {ip}:{port}")
            return True
        return False
    
    def stop_server(self):
        if self.server_running:
            self.server_running = False
            with self.lock:
                for player in list(self.players.values()):
                    try:
                        player['socket'].close()
                    except:
                        pass
                self.players.clear()
            self.update_client_list()
            self.log("Server stopped")
            return True
        return False
    
    def broadcast(self, message, exclude=None, color=None):
        if not message.endswith('\n'):
            message += '\n'
        with self.lock:
            for p in self.players.values():
                if p['socket'] != exclude:
                    try:
                        if color and message.startswith('[SERVER]'):
                            colored_msg = f"/server_msg {color} {message}"
                            p['socket'].sendall(colored_msg.encode())
                        else:
                            p['socket'].sendall(message.encode())
                    except:
                        continue
    
    def send_popup(self, message, color="#FFFFFF"):
        with self.lock:
            for p in self.players.values():
                try:
                    p['socket'].sendall(f"/popup {color} {message}\n".encode())
                except:
                    continue
    
    def handle_client(self, client_socket, address):
        client_id = f"{address[0]}:{address[1]}"
        self.log(f"New connection from {client_id}")
        
        try:
            with self.lock:
                random_name = random.choice(self.random_names)
                random_color = random.choice(self.player_colors)
                
                self.players[client_id] = {
                    'socket': client_socket,
                    'address': address,
                    'name': f"{random_name}_{len(self.players)+1}",
                    'x': random.randint(50, self.GAME_WIDTH - self.PLAYER_SIZE - 50),
                    'y': random.randint(50, self.GAME_HEIGHT - self.PLAYER_SIZE - 50),
                    'color': random_color,
                    'hp': self.MAX_HP,
                    'last_command': time.time(),
                    'message': None,
                    'message_time': 0
                }
                self.inventory[client_id] = []
                self.last_command_time[client_id] = 0
                self.player_gems[client_id] = 0
            
            try:
                client_socket.sendall(b"/server_msg #00FF00 [SERVER] Welcome to the game! Type /help for commands.\n")
                state = json.dumps({
                    'players': {n: {
                        'x': p['x'], 
                        'y': p['y'], 
                        'color': p['color'],
                        'name': p['name'],
                        'hp': p['hp'],
                        'message': p.get('message'),
                        'message_time': p.get('message_time', 0)
                    } for n, p in self.players.items()},
                    'grid_cells': self.grid_cells
                })
                client_socket.sendall(f"/state {state}\n".encode())
            except Exception as e:
                self.log(f"Error sending initial data to {client_id}: {e}")
            
            self.update_client_list()
            
            while self.server_running:
                try:
                    data = client_socket.recv(1024).decode().strip()
                    if not data:
                        break
                    
                    if data.startswith('/chat '):
                        msg = data[6:]
                        if msg == "":
                            continue
                        if msg == "/help" or msg == "/h" or msg == "/?":
                            client_socket.sendall(b"/server_msg #FF0000 [SERVER] Available commands:\n")
                            client_socket.sendall(b"/server_msg #00AA00 [SERVER] /inventory - show your inventory\n")
                            client_socket.sendall(b"/server_msg #00AA00 [SERVER] /time - show current time\n")
                            continue
                        if msg == "/time":
                            client_socket.sendall(f"/server_msg #00AAFF [SERVER] {time.strftime('%H:%M:%S')}\n".encode())
                            continue
                        if msg == "/inventory" or msg == "/inv":
                            client_socket.sendall(f"/server_msg #FFAA00 [SERVER] Your inventory: {self.inventory[client_id]}\n".encode())
                            client_socket.sendall(f"/server_msg #FFAA00 [SERVER] Your gems: {self.player_gems[client_id]}\n".encode())
                            continue
                        if msg == "/lukva":
                            client_socket.sendall(f"/server_msg #FFAA00 [SERVER] You found a lukva!\n".encode())
                            client_socket.sendall(f"/popup #FFAA00 You found a lukva!\n".encode())
                            continue
                        if msg.startswith("/"):
                            client_socket.sendall(b"/server_msg #FF0000 [SERVER] Unknown command. Type /help for available commands.\n")
                            continue
                        if len(msg) > 40:
                            msg = msg[:40]
                            client_socket.sendall(b"/server_msg #FF5500 [SERVER] Your message too long. It has been cut lol.\n")
                            
                        with self.lock:
                            player_name = self.players[client_id]['name']
                            self.players[client_id]['message'] = msg
                            self.players[client_id]['message_time'] = time.time()
                        
                        if self.current_math_question and msg.strip().isdigit():
                            try:
                                user_answer = int(msg.strip())
                                correct_answer = self.current_math_question['answer']
                                
                                if user_answer == correct_answer:
                                    reward = random.randint(1, 15)
                                    self.player_gems[client_id] += reward
                                    self.broadcast(f"[Gem Game] {player_name} correctly answered the math question and earned {reward} gems!", color="#00FF00")
                                    client_socket.sendall(f"/server_msg #00FF00 [Gem Game] You now have {self.player_gems[client_id]} gems.\n".encode())
                                    
                                    self.current_math_question = None
                                    self.last_math_question_time = time.time()
                                    
                                    for cell_key in list(self.grid_cells.keys()):
                                        if self.grid_cells[cell_key] == "#FFFF00":
                                            self.grid_cells[cell_key] = "#00FF00"
                                    
                                    x = random.randint(0, 15) * self.grid_size
                                    y = random.randint(0, 11) * self.grid_size
                                    cell_key = f"{x},{y}"
                                    self.grid_cells[cell_key] = "#FF00FF"
                                    
                                    state = json.dumps({
                                        'players': {n: {
                                            'x': p['x'], 
                                            'y': p['y'], 
                                            'color': p['color'],
                                            'name': p['name'],
                                            'hp': p['hp'],
                                            'message': p.get('message'),
                                            'message_time': p.get('message_time', 0)
                                        } for n, p in self.players.items()},
                                        'grid_cells': self.grid_cells
                                    })
                                    self.broadcast(f"/state {state}")
                                else:
                                    self.broadcast(f"[CHAT] {player_name}: {msg} (wrong answer)")
                                    
                                    for cell_key in list(self.grid_cells.keys()):
                                        if self.grid_cells[cell_key] == "#FFFF00":
                                            self.grid_cells[cell_key] = "#FF0000"
                                    
                                    state = json.dumps({
                                        'players': {n: {
                                            'x': p['x'], 
                                            'y': p['y'], 
                                            'color': p['color'],
                                            'name': p['name'],
                                            'hp': p['hp'],
                                            'message': p.get('message'),
                                            'message_time': p.get('message_time', 0)
                                        } for n, p in self.players.items()},
                                        'grid_cells': self.grid_cells
                                    })
                                    self.broadcast(f"/state {state}")
                            except ValueError:
                                self.broadcast(f"[CHAT] {player_name}: {msg}")
                        else:
                            self.broadcast(f"[CHAT] {player_name}: {msg}")
                        
                        state = json.dumps({
                            'players': {n: {
                                'x': p['x'], 
                                'y': p['y'], 
                                'color': p['color'],
                                'name': p['name'],
                                'hp': p['hp'],
                                'message': p.get('message'),
                                'message_time': p.get('message_time', 0)
                            } for n, p in self.players.items()},
                            'grid_cells': self.grid_cells
                        })
                        self.broadcast(f"/state {state}")
                    elif data.startswith('/move '):
                        now = int(time.time() * 1000)
                        if now - self.last_command_time[client_id] < self.MIN_COMMAND_INTERVAL:
                            continue
                        self.last_command_time[client_id] = now
                        direction = data[6:]
                        with self.lock:
                            px, py = self.players[client_id]['x'], self.players[client_id]['y']
                            if direction == 'upleft':
                                px -= self.PLAYER_VEL
                                py -= self.PLAYER_VEL
                            elif direction == 'upright':
                                px += self.PLAYER_VEL
                                py -= self.PLAYER_VEL
                            elif direction == 'downleft':
                                px -= self.PLAYER_VEL
                                py += self.PLAYER_VEL
                            elif direction == 'downright':
                                px += self.PLAYER_VEL
                                py += self.PLAYER_VEL
                            elif direction == 'left':
                                px -= self.PLAYER_VEL
                            elif direction == 'right':
                                px += self.PLAYER_VEL
                            elif direction == 'up':
                                py -= self.PLAYER_VEL
                            elif direction == 'down':
                                py += self.PLAYER_VEL
                            px = max(0, min(self.GAME_WIDTH-self.PLAYER_SIZE, px))
                            py = max(0, min(self.GAME_HEIGHT-self.PLAYER_SIZE, py))
                            self.players[client_id]['x'] = px
                            self.players[client_id]['y'] = py
                        state = json.dumps({
                            'players': {n: {
                                'x': p['x'], 
                                'y': p['y'], 
                                'color': p['color'],
                                'name': p['name'],
                                'hp': p['hp'],
                                'message': p.get('message'),
                                'message_time': p.get('message_time', 0)
                            } for n, p in self.players.items()},
                            'grid_cells': self.grid_cells
                        })
                        self.broadcast(f"/state {state}")
                except ConnectionResetError:
                    break
                except Exception as e:
                    self.log(f"Error with {client_id}: {str(e)}")
                    break
                    
        finally:
            with self.lock:
                if client_id in self.players:
                    del self.players[client_id]
                    del self.inventory[client_id]
                    del self.last_command_time[client_id]
                    if client_id in self.player_gems:
                        del self.player_gems[client_id]
            client_socket.close()
            self.log(f"Client {client_id} disconnected")
            self.update_client_list()
    
    def generate_math_question(self):
        if self.current_math_question is not None:
            return
        
        if time.time() - self.last_math_question_time < self.math_question_cooldown:
            return
            
        self.math_question_time = time.time()
        
        num1 = random.randint(1, 20)
        num2 = random.randint(1, 20)
        operation = random.choice(['+', '-', '*'])
        
        if operation == '+':
            answer = num1 + num2
        elif operation == '-':
            answer = num1 - num2
        else:
            answer = num1 * num2
            
        self.current_math_question = {
            'question': f"{num1} {operation} {num2}",
            'answer': answer
        }
        
        self.broadcast(f"[Gem Game] Math question: {self.current_math_question['question']} = ?", color="#FFFF00")
        
        x = random.randint(0, 15) * self.grid_size
        y = random.randint(0, 11) * self.grid_size
        cell_key = f"{x},{y}"
        self.grid_cells[cell_key] = "#FFFF00"
        
        state = json.dumps({
            'players': {n: {
                'x': p['x'], 
                'y': p['y'], 
                'color': p['color'],
                'name': p['name'],
                'hp': p['hp'],
                'message': p.get('message'),
                'message_time': p.get('message_time', 0)
            } for n, p in self.players.items()},
            'grid_cells': self.grid_cells
        })
        self.broadcast(f"/state {state}")

    def check_and_send_math_question(self):
        now = time.time()
        
        if (self.current_math_question is None and 
            now - self.last_math_question_time > self.math_question_cooldown and
            len(self.players) > 0):
            
            self.generate_math_question()
            self.broadcast(f"[Gem Game] Math question for gems: {self.current_math_question['question']} First to answer correctly wins!")
            self.last_math_question_time = now

            if self.current_math_question is not None and now - self.last_math_question_time > self.math_question_cooldown:
                self.broadcast(f"[Gem Game] No one answer correctly!")
                self.last_math_question_time = now
                self.current_math_question = None
    
    def run_server(self):
        self.server_running = True
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.server.bind((ip, port))
            self.server.listen(5)
            self.log(f"Server listening on {ip}:{port}")
            
            periodic_thread = threading.Thread(target=self.periodic_tasks, daemon=True)
            periodic_thread.start()
            
            while self.server_running:
                try:
                    client_socket, address = self.server.accept()
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, address),
                        daemon=True
                    )
                    client_thread.start()
                except OSError:
                    break
                except Exception as e:
                    self.log(f"Error accepting connection: {e}")
        finally:
            self.server.close()
            self.server_running = False
    
    def periodic_tasks(self):
        while self.server_running:
            try:
                self.check_and_send_math_question()
                time.sleep(5)
            except Exception as e:
                self.log(f"Error in periodic tasks: {e}")

def main():
    server = GameServer()
    server.start_server()
    
    try:
        while True:
            cmd = input("> ")
            if cmd.lower() in ['stop', 'exit', 'quit']:
                server.stop_server()
                break
            elif cmd.lower() in ['help', '?']:
                print("Available commands:")
                print("  help, ? - Show this help")
                print("  stop, exit, quit - Stop the server")
                print("  list - List connected clients")
                print("  gems - Show gems for all players")
                print("  question - Force a new math question")
            elif cmd.lower() == 'list':
                server.update_client_list()
            elif cmd.lower() == 'gems':
                print("Player gems:")
                for pid, player in server.players.items():
                    print(f"  {player['name']}: {server.player_gems.get(pid, 0)} gems")
            elif cmd.lower() == 'question':
                server.current_math_question = None
                server.last_math_question_time = 0
                server.check_and_send_math_question()
                print("New math question sent!")
            else:
                print(f"Unknown command: {cmd}. Type 'help' for available commands.")
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.stop_server()

ip = '127.0.0.1'
port = 55555

if __name__ == "__main__":
    main()
