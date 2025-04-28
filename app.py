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
        'score1': 0,
        'score2': 0,
        'time': '2023-10-15 19:00',
        'event': 'IEM Cologne 2023',
        'map': 'Mirage',
        'status': 'upcoming'
    },
    {
        'id': 2,
        'team1': 'Faze Clan',
        'team2': 'Heroic',
        'score1': 0,
        'score2': 0,
        'time': '2023-10-16 20:00',
        'event': 'ESL Pro League S18',
        'map': 'Inferno',
        'status': 'upcoming'
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

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')

        conn.commit()


init_db()


# Вспомогательные функции БД
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# Декоратор для проверки авторизации
def login_required(f):
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Пожалуйста, войдите для доступа к этой странице', 'warning')
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
            flash('Имя пользователя и пароль обязательны!', 'danger')
            return redirect(url_for('register'))

        try:
            with get_db() as conn:
                hashed_pw = generate_password_hash(password)
                conn.execute('INSERT INTO users (username, password, email) VALUES (?, ?, ?)',
                             (username, hashed_pw, email))
                conn.commit()

            flash('Регистрация успешна! Теперь вы можете войти.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Это имя пользователя уже занято!', 'danger')

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
            flash(f'Добро пожаловать, {user["username"]}!', 'success')
            return redirect(url_for('profile'))
        else:
            flash('Неверное имя пользователя или пароль', 'danger')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Вы успешно вышли из системы', 'info')
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
        flash('Матч не найден', 'danger')
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
            flash('Войдите, чтобы оставлять комментарии', 'warning')
            return redirect(url_for('login', next=url_for('match_detail', match_id=match_id)))

        comment_text = request.form.get('comment', '').strip()
        if not comment_text:
            flash('Комментарий не может быть пустым', 'danger')
        else:
            try:
                with get_db() as conn:
                    conn.execute(
                        'INSERT INTO comments (match_id, user_id, text) VALUES (?, ?, ?)',
                        (match_id, session['user_id'], comment_text)
                    )
                    conn.commit()
                flash('Комментарий добавлен', 'success')
                return redirect(url_for('match_detail', match_id=match_id))
            except Exception as e:
                flash('Ошибка при добавлении комментария', 'danger')
                print(f"Error adding comment: {e}")

    return render_template('match_detail.html',
                           match=match,
                           comments=comments,
                           user_id=session.get('user_id'))


@app.route('/profile')
@login_required
def profile():
    with get_db() as conn:
        user_comments = conn.execute('''
            SELECT * FROM comments 
            WHERE user_id = ? 
            ORDER BY created_at DESC 
            LIMIT 5
        ''', (session['user_id'],)).fetchall()

    return render_template('profile.html',
                           username=session.get('username'),
                           comments=user_comments)


if __name__ == '__main__':
    app.run(debug=True)