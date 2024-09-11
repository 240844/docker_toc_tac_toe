import socket
import json
import random
import time


def send_request(packet_type, token=None, square=None):
    request = {
        "packet_type": packet_type,
    }

    if token:
        request["token"] = token
    if square is not None:
        request["square"] = square

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(("localhost", 12345))  # Ensure the same port is used as your game server

    client.send(json.dumps(request).encode())

    response = client.recv(4096).decode()
    client.close()

    return json.loads(response)


def choose_random_move(board):
    open_moves = [i for i, square in enumerate(board) if square == " "]
    if open_moves:
        return random.choice(open_moves)
    return None


def main():
    token = input("Enter AI's token: ")  # Each AI should have its unique token

    # Start the game or get the game state
    print("AI connecting to the game...")

    # Loop until the game is finished
    while True:
        # Get the current game state
        response = send_request("get_game_state", token)
        game = response.get("game", {})
        disc = response.get("disconnect")
        print(response)
        if disc:
            break
        board = game.get("board", [])
        turn = game.get("turn", None)
        winner = game.get("winner", None)

        # Display the current board and turn
        print(f"Board: {board}")
        print(f"Turn: {turn}")

        # Check if the game is over
        if winner is not None:
            if winner == "draw":
                print("Game over! It's a draw.")
            else:
                print(f"Game over! Winner: {winner}")

        # If it's the AI's turn (assuming the AI is "O")
        if turn == "O":
            print("AI's turn! Choosing a move...")
            move = choose_random_move(board)

            if move is not None:
                print(f"AI chose move: {move}")
                response = send_request("make_move", token, move)
                print("Move response: ", response)
            else:
                print("No valid moves left!")
                break
        else:
            print("Waiting for the opponent's move...")

        # Wait before checking the game state again to give time for the client to move
        time.sleep(2)


if __name__ == "__main__":
    main()
