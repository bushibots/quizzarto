from flask import Flask, render_template, request, redirect, session, url_for
from flask_socketio import SocketIO, emit, join_room
import time
import threading
import random
import string
from models import db, User, Lobby, Score # Import from your new file
from werkzeug.security import generate_password_hash, check_password_hash



app = Flask(__name__)
app.config['SECRET_KEY'] = 'quizzarto_cyber_secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///quizzarto.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
socketio = SocketIO(app, cors_allowed_origins="*")

with app.app_context():
    db.create_all()

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

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nickname = request.form.get('nickname')
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')

        # Check if email exists
        if User.query.filter_by(email=email).first():
            return "Email already registered", 400

        new_user = User(
            nickname=nickname,
            email=email,
            phone=phone,
            password=generate_password_hash(password),
            is_guest=False
        )
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('index'))
    
    return render_template('register.html')

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')
    user = User.query.filter_by(email=email).first()

    if user and check_password_hash(user.password, password):
        session['user_id'] = user.id
        session['nickname'] = user.nickname
        return redirect(url_for('index'))
    
    return "Invalid Credentials", 401

@app.route('/host')
def host():
    # Generate a unique 4-digit PIN
    pin = ''.join(random.choices(string.digits, k=4))
    
    # Ensure the PIN is unique among active games
    while pin in active_games:
        pin = ''.join(random.choices(string.digits, k=4))
        
    # Initialize the game state as soon as the host loads the page
    active_games[pin] = {
        "players": [], 
        "current_q": -1, 
        "state": "LOBBY",
        "scores": {} 
    }
    return render_template('host.html', pin=pin)
# --- SOCKET LOGIC ---

@socketio.on('join')
def on_join(data):
    nickname = data.get('nickname')
    pin = data.get('pin')

    if not pin or pin not in active_games:
        return

    join_room(pin)

    if pin not in active_games:
        active_games[pin] = {"players": [], "current_q": -1, "state": "LOBBY", "scores": {}}

    # Check if the joining user is in our database to get their private info
    user_info = {"nickname": nickname, "email": "GUEST", "phone": "N/A"}
    db_user = User.query.filter_by(nickname=nickname).first()
    if db_user:
        user_info["email"] = db_user.email
        user_info["phone"] = db_user.phone if db_user.phone else "N/A"

    # Prevent duplicates but update the list with full info objects
    player_exists = any(p['nickname'] == nickname for p in active_games[pin]["players"])

    if not player_exists and nickname != "HOST":
        active_games[pin]["players"].append(user_info) # Store the full object
        active_games[pin]["scores"][nickname] = 0

    print(f"DEBUG: {nickname} joined {pin}")
    # Send the full player objects back to the room
    emit('update_lobby', active_games[pin]["players"], to=pin)

# Inside app.py

@socketio.on('start_quiz')
def handle_start(pin):
    if pin not in active_games:
        return
        
    room = active_games[pin]
    
    # NEW: Check if a timer is already active to prevent double-triggering
    if room.get("timer_active"):
        print(f"DEBUG: Timer already running for {pin}. Ignoring request.")
        return

    room["current_q"] += 1
    
    if room["current_q"] < len(QUESTIONS):
        room["state"] = "QUESTION"
        room["timer_active"] = True  # Set flag to True
        q_data = QUESTIONS[room["current_q"]]
        
        emit('new_question', {
            "question": q_data["text"],
            "options": q_data["options"],
            "q_index": room["current_q"],
            "time_limit": 15
        }, to=pin)
        
        threading.Thread(target=run_timer, args=(pin, 15)).start()
    else:
        room["state"] = "FINAL"
        leaderboard_data = get_leaderboard(pin)

        # --- NEW: SAVE TO DATABASE ---
        current_month = datetime.utcnow().strftime('%Y-%m') # e.g., "2026-02"

        for entry in leaderboard_data:
            # Find the user in the DB by nickname
            user = User.query.filter_by(nickname=entry['nickname']).first()
            if user and not user.is_guest:
                # Add score to their permanent record
                new_score = Score(
                    user_id=user.id,
                    points=entry['score'],
                    month_year=current_month
                )
                db.session.add(new_score)

        db.session.commit()
        # -----------------------------

        emit('game_over', {"leaderboard": leaderboard_data}, to=pin)

def run_timer(pin, seconds):
    for i in range(seconds, -1, -1):
        time.sleep(1)
        socketio.emit('timer_update', i, to=pin)
        
        # Check if the room still exists (e.g., if the host didn't disconnect)
        room = active_games.get(pin)
        if not room:
            break

        if i == 0:
            room["state"] = "RESULTS"
            room["timer_active"] = False  # Reset flag when question ends
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

@app.route('/leaderboard')
def global_leaderboard():
    current_month = datetime.utcnow().strftime('%Y-%m')

    # Query: Sum scores for each user for the current month, join with User table for names
    top_scores = db.session.query(
        User.nickname, 
        db.func.sum(Score.points).label('total_points')
    ).join(Score).filter(
        Score.month_year == current_month
    ).group_by(User.id).order_by(db.text('total_points DESC')).limit(10).all()

    return render_template('leaderboard.html', scores=top_scores, month=current_month)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)