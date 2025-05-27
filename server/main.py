from game_server import GameServer
from game_config import ip, port

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
            elif cmd.lower() == 'tps':
                print(f"Internal TPS: {server.internal_tps:.2f} (packet processing)")
                print(f"External TPS: {server.external_tps:.2f} (broadcast updates)")
            else:
                print(f"Unknown command: {cmd}. Type 'help' for available commands.")
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.stop_server()

if __name__ == "__main__":
    main()