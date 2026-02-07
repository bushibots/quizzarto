from flask import Flask, render_template
from flask_socketio import SocketIO, emit, join_room
import time
import threading

app = Flask(__name__)
app.config['SECRET_KEY'] = 'quizzarto_cyber_secret'
socketio = SocketIO(app, cors_allowed_origins="*")

# --- GAME DATA ---
QUESTIONS = [
    {
        "text": "WHICH PLANET IS KNOWN AS THE RED PLANET?",
        "options": ["EARTH", "MARS", "JUPITER", "VENUS"],
        "correct": 1
    },
    {
        "text": "WHAT IS THE LARGEST OCEAN ON EARTH?",
        "options": ["ATLANTIC", "INDIAN", "ARCTIC", "PACIFIC"],
        "correct": 3
    },
    {
        "text": "IDENTIFY THE CHEMICAL SYMBOL FOR OXYGEN.",
        "options": ["G", "OX", "O", "OM"],
        "correct": 2
    }
]

# --- STATE MANAGEMENT ---
# active_games[pin] = { players: [], current_q: -1, state: 'LOBBY', timer_active: False }
active_games = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/host')
def host():
    return render_template('host.html')

# --- SOCKET LOGIC ---

@socketio.on('join')
def on_join(data):
    nickname = data.get('nickname')
    pin = data.get('pin')
    
    if not pin:
        return
        
    join_room(pin)
    
    if pin not in active_games:
        active_games[pin] = {
            "players": [], 
            "current_q": -1, 
            "state": "LOBBY",
            "scores": {} 
        }
    
    if nickname not in active_games[pin]["players"] and nickname != "HOST":
        active_games[pin]["players"].append(nickname)
        active_games[pin]["scores"][nickname] = 0
        
    print(f"DEBUG: {nickname} joined {pin}")
    emit('update_lobby', active_games[pin]["players"], to=pin)

@socketio.on('start_quiz')
def handle_start(pin):
    if pin not in active_games:
        return
        
    room = active_games[pin]
    room["current_q"] += 1
    
    if room["current_q"] < len(QUESTIONS):
        room["state"] = "QUESTION"
        q_data = QUESTIONS[room["current_q"]]
        
        # Broadcast the question to everyone in the room
        emit('new_question', {
            "question": q_data["text"],
            "options": q_data["options"],
            "q_index": room["current_q"],
            "time_limit": 15
        }, to=pin)
        
        # Start the background timer
        threading.Thread(target=run_timer, args=(pin, 15)).start()
    else:
        room["state"] = "FINAL"
        emit('game_over', {"leaderboard": get_leaderboard(pin)}, to=pin)

def run_timer(pin, seconds):
    for i in range(seconds, -1, -1):
        time.sleep(1)
        socketio.emit('timer_update', i, to=pin)
        if i == 0:
            room = active_games.get(pin)
            if room:
                room["state"] = "RESULTS"
                correct_idx = QUESTIONS[room["current_q"]]["correct"]
                socketio.emit('show_results', {
                    "correct_index": correct_idx,
                    "leaderboard": get_leaderboard(pin)
                }, to=pin)

@socketio.on('submit_answer')
def handle_answer(data):
    pin = data.get('pin')
    nickname = data.get('nickname')
    answer_idx = data.get('answer')
    
    room = active_games.get(pin)
    if room and room["state"] == "QUESTION":
        correct_idx = QUESTIONS[room["current_q"]]["correct"]
        if int(answer_idx) == correct_idx:
            room["scores"][nickname] += 1000
            print(f"DEBUG: {nickname} correct. Score: {room['scores'][nickname]}")

def get_leaderboard(pin):
    room = active_games.get(pin)
    if not room: return []
    # Sort players by score descending
    sorted_scores = sorted(room["scores"].items(), key=lambda x: x[1], reverse=True)
    return [{"nickname": name, "score": score} for name, score in sorted_scores]

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)