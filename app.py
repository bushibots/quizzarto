from flask import Flask, render_template, request, redirect, session, url_for
from flask_socketio import SocketIO, emit, join_room
import time
import threading
import random
import string
from models import db, User, Lobby, Score, QuestionSet, Question# Import from your new file
from werkzeug.security import generate_password_hash, check_password_hash
import os  # NEW: For environment variables
from flask import Flask, render_template, request, redirect, session, url_for
# ... rest of imports ...



app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'quizzarto_cyber_secret')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///quizzarto.db')
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
        session['user_id'] = new_user.id
        session['nickname'] = new_user.nickname
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
    # 1. Security Check: Only logged-in Coaches can access this
    if not session.get('user_id') or not session.get('is_host'):
        return redirect(url_for('host_auth'))

    user_id = session['user_id']
    
    # 2. PIN Management: Look for an existing permanent PIN for this coach
    existing_lobby = Lobby.query.filter_by(host_id=user_id, is_active=True).first()
    
    if existing_lobby:
        pin = existing_lobby.pin
    else:
        # Generate a new permanent PIN if they don't have one
        pin = ''.join(random.choices(string.digits, k=4))
        while Lobby.query.filter_by(pin=pin).first():
            pin = ''.join(random.choices(string.digits, k=4))
            
        new_lobby = Lobby(pin=pin, host_id=user_id)
        db.session.add(new_lobby)
        db.session.commit()

    # 3. Live State: Initialize the game state in memory if it doesn't exist
    if pin not in active_games:
        active_games[pin] = {
            "players": [], 
            "current_q": -1, 
            "state": "LOBBY",
            "scores": {},
            "questions": [] # Will be populated when quiz is selected
        }

    # 4. Data Loading: Fetch this coach's saved quizzes for the dropdown
    my_quizzes = QuestionSet.query.filter_by(host_id=user_id).all()
    
    return render_template('host.html', pin=pin, quizzes=my_quizzes)

@app.route('/host/auth', methods=['GET', 'POST'])
def host_auth():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        # This handles both Register and Login for simplicity in this portal
        user = User.query.filter_by(email=email).first()

        if user:
            # LOGIN logic
            if check_password_hash(user.password, password) and user.is_host:
                session['user_id'] = user.id
                session['nickname'] = user.nickname
                session['is_host'] = True
                return redirect(url_for('host'))
        else:
            # REGISTER logic (First time Coach signup)
            nickname = request.form.get('nickname')
            new_host = User(
                nickname=nickname,
                email=email,
                password=generate_password_hash(password),
                is_host=True,
                is_guest=False
            )
            db.session.add(new_host)
            db.session.commit()
            session['user_id'] = new_host.id
            session['nickname'] = new_host.nickname
            session['is_host'] = True
            return redirect(url_for('host'))
            
    return render_template('host_auth.html')
# --- SOCKET LOGIC ---

@socketio.on('join')
def on_join(data):
    nickname = data.get('nickname')
    pin = data.get('pin')

    # UPDATED: Check if PIN exists and send error if it doesn't
    if not pin or pin not in active_games:
        emit('join_error', {"message": "INVALID SESSION PIN"}) # Send only to the sender
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
def handle_start(data):
    pin = data.get('pin')
    set_id = data.get('set_id') # New: The ID of the selected quiz

    if pin not in active_games:
        return

    room = active_games[pin]
    if room.get("timer_active"): return

    # NEW: If this is the first question, load the selected quiz into the room
    if room["current_q"] == -1:
        quiz_set = QuestionSet.query.get(set_id)
        if not quiz_set: return

        # Convert DB questions to the format the game expects
        room["questions"] = []
        for q in quiz_set.questions:
            room["questions"].append({
                "text": q.text,
                "options": [q.option_a, q.option_b, q.option_c, q.option_d],
                "correct": q.correct_index
            })

    room["current_q"] += 1

    if room["current_q"] < len(room["questions"]):
        room["state"] = "QUESTION"
        room["timer_active"] = True
        q_data = room["questions"][room["current_q"]]

        emit('new_question', {
            "question": q_data["text"],
            "options": q_data["options"],
            "q_index": room["current_q"],
            "time_limit": 15
        }, to=pin)

        threading.Thread(target=run_timer, args=(pin, 15)).start()
    else:
        room["state"] = "FINAL"
        emit('game_over', {"leaderboard": get_leaderboard(pin)}, to=pin)


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

@app.route('/host/editor', methods=['GET', 'POST'])
def question_editor():
    if not session.get('user_id') or not session.get('is_host'):
        return redirect(url_for('host_auth'))

    user_id = session['user_id']

    if request.method == 'POST':
        title = request.form.get('quiz_title')
        new_set = QuestionSet(title=title, host_id=user_id)
        db.session.add(new_set)
        db.session.flush() # Gets the ID for the new set

        # Logic to extract multiple questions from the form
        texts = request.form.getlist('q_text[]')
        opts_a = request.form.getlist('q_a[]')
        opts_b = request.form.getlist('q_b[]')
        opts_c = request.form.getlist('q_c[]')
        opts_d = request.form.getlist('q_d[]')
        corrects = request.form.getlist('q_correct[]')

        for i in range(len(texts)):
            q = Question(
                set_id=new_set.id,
                text=texts[i],
                option_a=opts_a[i],
                option_b=opts_b[i],
                option_c=opts_c[i],
                option_d=opts_d[i],
                correct_index=int(corrects[i])
            )
            db.session.add(q)
        
        db.session.commit()
        return redirect(url_for('host'))

    # Get existing sets to display
    my_sets = QuestionSet.query.filter_by(host_id=user_id).all()
    return render_template('editor.html', sets=my_sets)

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