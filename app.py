from flask import Flask, render_template
from flask_socketio import SocketIO, emit, join_room

app = Flask(__name__)
app.config['SECRET_KEY'] = 'quizzarto_secret'
socketio = SocketIO(app, cors_allowed_origins="*")

# Game Data
QUESTIONS = [
    {
        "text": "Which planet is known as the Red Planet?",
        "options": ["Earth", "Mars", "Jupiter", "Venus"],
        "correct": 1
    },
    {
        "text": "What is the largest ocean on Earth?",
        "options": ["Atlantic", "Indian", "Arctic", "Pacific"],
        "correct": 3
    }
]

# Track game state
active_games = {}

@app.route('/')
def index():
    # This will serve the Player page
    return "<h1>Player Join Page (Coming Next)</h1>"

@app.route('/host')
def host():
    # This will serve the Host page
    return "<h1>Host Dashboard (Coming Next)</h1>"

@socketio.on('join')
def on_join(data):
    nickname = data.get('nickname')
    pin = data.get('pin')
    join_room(pin)
    
    if pin not in active_games:
        active_games[pin] = {"players": [], "started": False}
    
    active_games[pin]["players"].append(nickname)
    print(f"--- {nickname} joined room {pin} ---")
    
    emit('update_lobby', active_games[pin]["players"], to=pin)

if __name__ == '__main__':
    # Run the server
    socketio.run(app, port=5000, debug=True)