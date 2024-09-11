import json
import socket
import uuid
from pymongo import MongoClient, errors


# MongoDB's connection details
endpoints = {
    "mongo_db": {
        "ip": 'db_ttt',
        "port": 27017
    },
    "mongo_api": {
        "ip": 'mongo_client_container',
        "port": 12345
    }
}

db_endpoint = endpoints["mongo_db"]
mongo_db_port = db_endpoint["port"]
mongo_db_ip = db_endpoint["ip"]

mongo_api_endpoint = endpoints["mongo_api"]
mongo_api_port = mongo_api_endpoint["port"]
mongo_api_ip = mongo_api_endpoint["ip"]

sessions = {}  # token: token (used as a substitute for usernames)

users = None


# Function to register a new user using only a token
def register_token(token, client):
    if users.find_one({"token": token}):
        response_json = json.dumps({"packet_type": "error", "response": "user already exists"})
        client.send(response_json.encode())
        print("Register failed: User already exists")
    else:
        users.insert_one({"token": token, "wins": 0, "losses": 0, "draws": 0})
        response_json = json.dumps({"packet_type": "response", "response": "success", "token": token})
        client.send(response_json.encode())
        print("User registered with token")


# Function to update the game stats (wins, losses, draws)
def update_stats(token, result):
    user = users.find_one({"token": token})
    if user:
        if result == "win":
            users.update_one({"token": token}, {"$inc": {"wins": 1}})
        elif result == "loss":
            users.update_one({"token": token}, {"$inc": {"losses": 1}})
        elif result == "draw":
            users.update_one({"token": token}, {"$inc": {"draws": 1}})
        print(f"Updated stats for token {token}: {result}")


# Function to get the user history (stats)
def get_history(token, client):
    user = users.find_one({"token": token})
    if user:
        history = {
            "wins": user.get("wins", 0),
            "losses": user.get("losses", 0),
            "draws": user.get("draws", 0)
        }
        response_json = json.dumps({"packet_type": "history", "response": "success", "history": history})
        client.send(response_json.encode())
        print(f"Sent history for token {token}")
    else:
        response_json = json.dumps({"packet_type": "error", "response": "invalid token"})
        client.send(response_json.encode())


# Main server loop
def main():
    while True:
        try:
            print("connecting to mongo")
            client = MongoClient(mongo_db_ip, port=mongo_db_port, username='mongoadmin', password='hunter2', connectTimeoutMS=5000, socketTimeoutMS=5000, authSource="admin")

            wordle_db = client.wordle_db
            global users
            users = wordle_db.users

            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.bind(("0.0.0.0", mongo_api_port))
            server.listen()

            test_connection = client.server_info()
            print("Connected to mongo:", test_connection)
            break

        except errors.ServerSelectionTimeoutError as e:
            print("Could not connect to mongo:", e)

    while True:
        try:
            print("Database client is waiting for connections...")
            client, addr = server.accept()
            print("Connection from:", addr)

            request_json = client.recv(4096).decode()
            data = json.loads(request_json)
            packet_type = data["packet_type"]

            print(f"Request type: \"{packet_type}\"")

            if packet_type == "register":
                token = str(uuid.uuid4())  # Generate a new token
                register_token(token, client)
            elif packet_type == "add_history":
                token = data["token"]
                result = data["result"]  # Expecting "win", "loss", or "draw"
                update_stats(token, result)
            elif packet_type == "get_history":
                token = data["token"]
                get_history(token, client)
            else:
                print("Invalid request")
                client.send(json.dumps({"packet_type": "error", "response": "invalid request"}).encode())
        except (socket.timeout, errors.ServerSelectionTimeoutError) as e:
            print("Could not connect to mongo:", e)


if __name__ == '__main__':
    main()
