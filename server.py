import socket
import json
from pymongo import MongoClient, errors

# MongoDB's connection settings
mongo_db_ip = 'mongo_wordle'
mongo_db_port = 27017

games = {}  # Store ongoing games, keyed by token
disc = {}


# Connect to MongoDB
def connect_mongo():
    try:
        client = MongoClient(mongo_db_ip, mongo_db_port, username='mongoadmin', password='hunter2', authSource="admin")
        db = client.wordle_db  # Replace with your database name
        users = db.users        # Collection to store user data
        return users
    except errors.ServerSelectionTimeoutError as e:
        print(f"Could not connect to MongoDB: {e}")
        return None


# Function to create a new game
def create_new_game():
    return {
        "board": [" " for _ in range(9)],  # A list to represent the board
        "turn": "X",  # X always starts first
        "winner": None,  # No winner yet
        "moves_count": 0
    }


# Check for a winner
def check_winner(board):
    win_conditions = [(0, 1, 2), (3, 4, 5), (6, 7, 8),  # Rows
                      (0, 3, 6), (1, 4, 7), (2, 5, 8),  # Columns
                      (0, 4, 8), (2, 4, 6)]  # Diagonals
    for a, b, c in win_conditions:
        if board[a] == board[b] == board[c] and board[a] != " ":
            return board[a]
    return None


# Check if the board is full
def is_board_full(board):
    return all(square != " " for square in board)


# Start a new game for a given token
def start_game(client, token):
    games[token] = create_new_game()
    disc[token] = False
    response = json.dumps({"packet_type": "start_game", "response": "success", "game": games[token]})
    client.send(response.encode())
    print(f"Game started for token: {token}")


# Make a move in the game
def make_move(client, request, users):
    token = request["token"]
    square = request["square"]

    if token not in games:
        response = json.dumps({"packet_type": "error", "response": "No active game found for token"})
        client.send(response.encode())
        return

    game = games[token]
    board = game["board"]

    if game["winner"] is not None:
        response = json.dumps({"packet_type": "error", "response": f"Game already won by {game['winner']}"})
        client.send(response.encode())
        return

    if board[square] != " ":
        response = json.dumps({"packet_type": "error", "response": "Square already occupied"})
        client.send(response.encode())
        return

    # Make the move
    board[square] = game["turn"]
    game["moves_count"] += 1

    # Check for a winner
    winner = check_winner(board)
    if winner:
        game["winner"] = winner
        """update_stats(token, winner, users)  # Update MongoDB stats Nie działa """
        response = json.dumps({"packet_type": "game_over", "response": f"{winner} wins!", "board": board})
        print(response)
    elif is_board_full(board):
        """update_stats(token, "draw", users)  # Update for a draw Nie działa """
        response = json.dumps({"packet_type": "game_over", "response": "It's a draw!", "board": board})
    else:
        # Switch turns
        game["turn"] = "O" if game["turn"] == "X" else "X"
        response = json.dumps({"packet_type": "move_made", "response": "success", "game": game})

    client.send(response.encode())


# Get the current game state
def get_game_state(client, token):
    if token not in games:
        response = json.dumps({"packet_type": "error", "response": "No active game found for token"})
    else:
        response = json.dumps({"packet_type": "game_state", "response": "success", "disconnect": disc[token], "game": games[token]})

    client.send(response.encode())


# Disconnect from the game
def disconnect_game(client, token):
    if token in games:
        disc[token] = True
        response = json.dumps(
            {"packet_type": "disconnected", "response": "success", "message": f"{token} has disconnected."})
        client.send(response.encode())
        client.close()
        print(f"{token} has disconnected from the game.")
    else:
        response = json.dumps({"packet_type": "error", "response": "invalid token"})
        client.send(response.encode())
        client.close()


# Update user statistics in MongoDB (wins, losses, draws)
def update_stats(token, result, users):
    user = users.find_one({"token": token})
    if user:
        if result == "X":  # X wins
            users.update_one({"token": token}, {"$inc": {"wins": 1}})
        elif result == "O":  # O wins
            users.update_one({"token": token}, {"$inc": {"losses": 1}})
        elif result == "draw":  # Draw
            users.update_one({"token": token}, {"$inc": {"draws": 1}})
        print(f"Updated stats for token {token}: {result}")
    else:
        # If the token doesn't exist, create a new entry
        users.insert_one({"token": token, "wins": 0, "losses": 0, "draws": 0})
        print(f"New user created for token {token}")


# Main server loop
def main():
    # Connect to MongoDB
    users = connect_mongo()
    if users is None:
        print("MongoDB connection failed. Exiting...")
        return

    # Set up the server
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("0.0.0.0", 12346))  # Replace with your desired port
    server.listen()

    print("Server is running and waiting for connections...")

    while True:
        client, addr = server.accept()
        print(f"Connected to {addr}")

        try:
            request_json = client.recv(4096).decode()
            data = json.loads(request_json)
            packet_type = data["packet_type"]
            token = data.get("token", None)

            if packet_type == "start_game":
                start_game(client, token)
            elif packet_type == "make_move":
                make_move(client, data, users)
            elif packet_type == "get_game_state":
                get_game_state(client, token)
            elif packet_type == "quit":
                disconnect_game(client, token)
            else:
                response = json.dumps({"packet_type": "error", "response": "Invalid packet type"})
                client.send(response.encode())

        except Exception as e:
            print(f"Error: {e}")
            response = json.dumps({"packet_type": "error", "response": str(e)})
            client.send(response.encode())

        finally:
            client.close()


if __name__ == '__main__':
    main()
