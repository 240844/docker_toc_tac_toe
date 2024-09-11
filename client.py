import socket
import json


def send_request(packet_type, token=None, square=None):
    request = {
        "packet_type": packet_type,
    }

    if token:
        request["token"] = token
    if square is not None:
        request["square"] = square

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(("localhost", 12345))  # Use the same IP/port as server

    client.send(json.dumps(request).encode())

    response = client.recv(4096).decode()
    client.close()

    return json.loads(response)


def print_board(board):
    for i in range(0, 9, 3):
        print(" | ".join(board[i:i + 3]))
        if i < 6:
            print("-" * 9)
    return None


def handle_response(response):
    if response is None:
        print("Response is None")
        return None

    if response["packet_type"] == "error":
        print("Error")
        print(response["response"])
        return None
    if response["packet_type"] == "game_over":
        print("\nGame Over")
        print_board(response.get("board"))
        print(f"\n\033[31m{response['response']}\033[0m")
        return None
    game = response.get("game")
    #print("Board: ", game.get("board"))
    print_board(game.get("board"))


def main():
    token = input("Enter your token: ")  # You can use a unique identifier like a username, etc.
    run = True
    while True:
        if run:
            response = send_request("start_game", token)
            handle_response(response)
            run = False
        print("\n1. Start a new game")
        print("2. Make a move")
        print("3. Get game state")
        print("4. Quit")
        choice = input("Choose an option: ")

        if choice == "1":
            response = send_request("start_game", token)
            handle_response(response)
        elif choice == "2":
            square = int(input("Enter the square number (0-8): "))
            response = send_request("make_move", token, square)
            handle_response(response)
        elif choice == "3":
            response = send_request("get_game_state", token)
            handle_response(response)
        elif choice == "4":
            response = send_request("quit", token)
            break
        else:
            print("Invalid choice!")


if __name__ == "__main__":
    main()
