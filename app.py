from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from waitress import serve
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-very-secure-secret-key-12345'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- CONFIGURATION: SURVEY QUESTIONS ---
SURVEY_DATA = {
    'easy': [
        {"q": "Who is the most famous video game character of all time?", "options": ["Steve", "Mario", "Sonic", "Link"], "answer": 1},
        {"q": "Who is the elven, sword-wielding hero dressed in green in the Legend of Zelda series?", "options": ["Luigi", "Ganon", "Zelda", "Link"], "answer": 3},
        {"q": "Which of these is not a Rockstar-developed game?", "options": ["Grand Theft Auto 5", "Sakiro: Shadow Die Twice", "Bully", "Red Dead Redemption 2"], "answer": 1},
        {"q": "What is the name of the fictional city where the Grand Theft Auto series is primarily set?", "options": ["Los Santos", "Liberty City", "Night City", "San Fierro"], "answer": 0},
        {"q": "In which game do players compete in a battle royale on an island called Erangel?", "options": ["Apex Legends", "Fortnite", "PUBG", "Call of Duty: Warzone"], "answer": 2},
        {"q": "Which game involves catching creatures called ‘Pocket Monsters’?", "options": ["Digital Monster", "Master Chief", "Valorant", "Pokemon"], "answer": 3},
        {"q": "What is the background of Battlefield 5?", "options": ["World War I", "World War II", "Cold War", "Nova Battlefront"], "answer": 1},
        {"q": "Which is impossible in Terraria?", "options": ["Drunk", "Fly", "Summon", "Teleport"], "answer": 0},
        {"q": "Which video game franchise features the characters Master Chief, Cortana, and the Covenant?", "options": ["Call of Duty", "Halo", "Gears of War", "Destiny"], "answer": 1},
        {"q": "What city does forza horizon 5 take place", "options": ["Dublin, Ireland", "Ankara, Turkey", "Guanajuato, Mexico", "Paris, France"], "answer": 2},
    ],
    'medium': [
        {"q": "Kratos is the main character of which game?", "options": ["God of War", "God Hand", "ELDEN RING", "Assassin's Creed"], "answer": 0},
        {"q": "What was the first home video game console?", "options": ["Sega Genisis", "Atari 1320", "Atari 2600", "Odyssey"], "answer": 3},
        {"q": "Which is not one of the victories in Sid Meier's Civilization VI?", "options": ["Domination Victory", "Prestige Victory", "Science Victory", "Culture Victory"], "answer": 1},
        {"q": "Which map is not from Counter-Strike?", "options": ["Dust 2", "Inferno", "Ancient", "Haven"], "answer": 3},
        {"q": "In the game 'Dark Souls', what is the name of the final boss in the base game?", "options": ["Gwyn, Lord of Cinder", "Seath the Scaleless", "The Bed of Chaos", "Nito, First of the Dead"], "answer": 0},
    ],
    'hard': [
        {"q": "How long does it take for the bomb to explode in CS:GO? (Unit: second)", "options": ["30", "45", "60", "40"], "answer": 3},
        {"q": "In 2006, Electronic Arts released FIFA Street 2 and made it available for all major video game consoles at the time. What professional football player did the cover feature?", "options": ["Ryan Giggs", "John Terry", "Cristiano Ronaldo", "David Beckham"], "answer": 2},
        {"q": "In The Elder Scrolls V: Skyrim, what shout does the Dragonborn use to launch enemies into the air?", "options": ["Fus Ro Dah", "Yol Toor Shul", "Laas Yah Nir", "Od Ah Viing"], "answer": 0},
        {"q": "Which material is not the ingredient of The Jackie Welles in Afterlife in Night City?", "options": ["Vodka", "Ginger beer", "Soda", "Lime juice"], "answer": 2},
        {"q": "What country does the achievement 'Let's Do The Time Warp Again' related to in Sid Meier's Civilization VI? ", "options": ["Egypt", "France", "Rome", "Babylon"], "answer": 3},
    ]
}

# --- DATABASE MODELS ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)
    
    # ROLE COLUMNS
    is_admin = db.Column(db.Boolean, default=False)       # Can view Admin Panel
    is_super_admin = db.Column(db.Boolean, default=False) # Can assign Roles
    
    results = db.relationship('SurveyResult', backref='student', lazy=True)

class SurveyResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    difficulty = db.Column(db.String(50), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    max_score = db.Column(db.Integer, nullable=False)
    time_taken = db.Column(db.Float, nullable=False)
    date_taken = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if User.query.filter_by(username=username).first():
            flash("Username exists.", 'danger')
            return redirect(url_for('register'))
        
        hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, password=hashed_pw)
        
        # --- SUPER ADMIN LOGIC ---
        # The very first user becomes the Super Admin
        if User.query.count() == 0:
            new_user.is_admin = True
            new_user.is_super_admin = True
            
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and check_password_hash(user.password, request.form.get('password')):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Login failed.', 'danger')
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    my_results = SurveyResult.query.filter_by(user_id=current_user.id).order_by(SurveyResult.date_taken.desc()).all()
    return render_template('dashboard.html', results=my_results)

# --- SURVEY ROUTES ---
@app.route('/setup_survey', methods=['GET', 'POST'])
@login_required
def setup_survey():
    if request.method == 'POST':
        gaming_time = request.form.get('gaming_time')
        difficulty = 'easy'
        if gaming_time == 'medium_time': difficulty = 'medium'
        elif gaming_time == 'high_time': difficulty = 'hard'
        
        session['start_time'] = time.time()
        session['difficulty'] = difficulty
        session['current_question'] = 0 
        session['answers'] = [] 
        
        return redirect(url_for('take_survey'))
    return render_template('setup_survey.html')

@app.route('/survey', methods=['GET', 'POST'])
@login_required
def take_survey():
    difficulty = session.get('difficulty', 'easy')
    questions = SURVEY_DATA.get(difficulty)
    current_idx = session.get('current_question', 0)
    
    if current_idx >= len(questions):
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        selected = request.form.get('option')
        current_answers = session.get('answers', [])
        current_answers.append(int(selected) if selected else -1)
        session['answers'] = current_answers
        session['current_question'] = current_idx + 1
        
        if session['current_question'] >= len(questions):
            return calculate_results(questions)
        return redirect(url_for('take_survey'))

    question = questions[current_idx]
    return render_template('survey.html', 
                         question=question, 
                         index=current_idx, 
                         total=len(questions), 
                         difficulty=difficulty,
                         start_timestamp=session.get('start_time'))

def calculate_results(questions):
    score = 0
    user_answers = session.get('answers', [])
    for i, user_ans in enumerate(user_answers):
        if i < len(questions) and user_ans == questions[i]['answer']:
            score += 1
    
    time_taken = round(time.time() - session.get('start_time'), 2)
    result = SurveyResult(
        user_id=current_user.id,
        difficulty=session.get('difficulty'),
        score=score,
        max_score=len(questions),
        time_taken=time_taken
    )
    db.session.add(result)
    db.session.commit()
    flash(f'Survey Complete! Score: {score}/{len(questions)}', 'success')
    return redirect(url_for('dashboard'))

# --- ADMIN ROUTES ---

@app.route('/admin')
@login_required
def admin():
    # Allow both Admins and Super Admins to view the panel
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    
    users = User.query.all()
    all_results = SurveyResult.query.order_by(SurveyResult.date_taken.desc()).all()
    return render_template('admin.html', users=users, results=all_results)

@app.route('/change_role/<int:user_id>/<action>')
@login_required
def change_role(user_id, action):
    # SECURITY: Only Super Admin can change roles
    if not current_user.is_super_admin:
        flash("Access Denied: Only Super Admin can change roles.", "danger")
        return redirect(url_for('admin'))
        
    user_to_edit = User.query.get(user_id)
    if not user_to_edit:
        return redirect(url_for('admin'))
        
    # Prevent Super Admin from demoting themselves
    if user_to_edit.id == current_user.id:
        flash("You cannot change your own role.", "warning")
        return redirect(url_for('admin'))

    if action == 'promote':
        user_to_edit.is_admin = True
        flash(f"{user_to_edit.username} is now an Admin.", "success")
    elif action == 'demote':
        user_to_edit.is_admin = False
        flash(f"{user_to_edit.username} is no longer an Admin.", "info")
        
    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    serve(app, debug=True)