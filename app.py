from flask import Flask, render_template, redirect, url_for, request, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_very_secret_key_here'  # Замените на реальный секретный ключ!

# Конфигурация БД
DATABASE = 'database.db'

# Мок-данные
matches = [
    {
        'id': 1,
        'team1': 'NaVi',
        'team2': 'Vitality',
        'time': '2023-10-15 19:00',
        'event': 'IEM Cologne 2023'
    },
    {
        'id': 2,
        'team1': 'Faze Clan',
        'team2': 'Heroic',
        'time': '2023-10-16 20:00',
        'event': 'ESL Pro League S18'
    }
]

news = [
    {
        'title': 'Major announcement: New CS2 tournament',
        'date': '2023-10-10',
        'content': 'Valve announces new championship series...'
    }
]

teams = [
    {'name': 'NaVi', 'rank': 1},
    {'name': 'Vitality', 'rank': 2},
    {'name': 'Faze Clan', 'rank': 3}
]


# Инициализация БД
def init_db():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()

        # Таблица пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Таблица матчей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team1 TEXT NOT NULL,
                team2 TEXT NOT NULL,
                score1 INTEGER DEFAULT 0,
                score2 INTEGER DEFAULT 0,
                time TEXT,
                event TEXT,
                map TEXT,
                status TEXT DEFAULT 'upcoming',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Таблица комментариев
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(match_id) REFERENCES matches(id)
            )
        ''')

        # Добавим тестовые матчи, если таблица пуста
        if cursor.execute('SELECT COUNT(*) FROM matches').fetchone()[0] == 0:
            test_matches = [
                (1, 'NaVi', 'Vitality', 0, 0, '2023-10-15 19:00', 'IEM Cologne 2023', 'Mirage', 'upcoming'),
                (2, 'Faze Clan', 'Heroic', 0, 0, '2023-10-16 20:00', 'ESL Pro League S18', 'Inferno', 'upcoming')
            ]
            cursor.executemany('''
                INSERT INTO matches (id, team1, team2, score1, score2, time, event, map, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', test_matches)

        conn.commit()


# Вспомогательные функции БД
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# Декоратор для проверки авторизации
def login_required(f):
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)

    return decorated_function


# Маршруты аутентификации
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        email = request.form.get('email', '').strip()

        if not username or not password:
            flash('Username and password are required!', 'danger')
            return redirect(url_for('register'))

        try:
            with get_db() as conn:
                hashed_pw = generate_password_hash(password)
                conn.execute('INSERT INTO users (username, password, email) VALUES (?, ?, ?)',
                             (username, hashed_pw, email))
                conn.commit()

            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already taken!', 'danger')

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()

        with get_db() as conn:
            user = conn.execute(
                'SELECT * FROM users WHERE username = ?',
                (username,)
            ).fetchone()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash(f'Welcome, {user["username"]}!', 'success')
            return render_template('profile.html')
        else:
            flash('Invalid username or password', 'danger')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('home'))


# Основные маршруты
@app.route('/')
def home():
    return render_template('base.html', matches=matches, news=news)


@app.route('/matches')
def matches_list():
    return render_template('matches.html', matches=matches)


@app.route('/teams')
def teams_list():
    return render_template('teams.html', teams=teams)


@app.route('/news')
def news_list():
    return render_template('news.html', news=news)


@app.route('/match/<int:match_id>', methods=['GET', 'POST'])
def match_detail(match_id):
    match = next((m for m in matches if m['id'] == match_id), None)
    if not match:
        flash('Match not found', 'danger')
        return redirect(url_for('matches_list'))

    # Получаем комментарии
    with get_db() as conn:
        comments = conn.execute('''
            SELECT comments.*, users.username 
            FROM comments 
            JOIN users ON comments.user_id = users.id 
            WHERE match_id = ? 
            ORDER BY created_at DESC
        ''', (match_id,)).fetchall()

    # Обработка нового комментария
    if request.method == 'POST':
        if 'user_id' not in session:
            flash('Please login to comment', 'warning')
            return redirect(url_for('login', next=url_for('match_detail', match_id=match_id)))

        comment_text = request.form.get('comment', '').strip()
        if not comment_text:
            flash('Comment cannot be empty', 'danger')
        else:
            try:
                with get_db() as conn:
                    conn.execute(
                        'INSERT INTO comments (match_id, user_id, text) VALUES (?, ?, ?)',
                        (match_id, session['user_id'], comment_text)
                    )
                    conn.commit()
                flash('Comment added', 'success')
                return redirect(url_for('match_detail', match_id=match_id))
            except Exception as e:
                flash('Error adding comment', 'danger')
                print(f"Error adding comment: {e}")

    return render_template('match_detail.html',
                           match=match,
                           comments=comments,
                           user_id=session.get('user_id'))


# Добавленный маршрут профиля
@app.route('/profile')
@login_required
def profile():
    with get_db() as conn:
        try:
            user_comments = conn.execute('''
                SELECT comments.*, matches.team1, matches.team2 
                FROM comments 
                JOIN matches ON comments.match_id = matches.id
                WHERE comments.user_id = ? 
                ORDER BY comments.created_at DESC 
                LIMIT 5
            ''', (session['user_id'],)).fetchall()
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            user_comments = []

    return render_template('profile.html',
                           username=session.get('username'),
                           comments=user_comments)

if __name__ == '__main__':
    app.run(debug=True)