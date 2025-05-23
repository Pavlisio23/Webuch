import os
from flask import *
from flask_restful import Api
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

from werkzeug.utils import secure_filename

from data import db_session
from data import teams_api
from data.mathes import Match
import logging
from data.news import News
import requests

app = Flask(__name__)
app.secret_key = 'd2f#a1!9xZv3@8cQ'
api = Api(app)
logging.basicConfig(level=logging.DEBUG)

app.config.update(
    SESSION_COOKIE_SECURE=False,    # True для HTTPS, False для HTTP
    SESSION_COOKIE_SAMESITE='Lax'   # Или 'None' (если нужен кросс-доменный доступ)
)

# Конфигурация БД
DATABASE = 'db/database.db'


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
            return redirect(url_for('profile'))  # Изменено на redirect
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
    db_sess = db_session.create_session()
    matches = db_sess.query(Match).all()
    db_sess = db_session.create_session()
    news = db_sess.query(News).all()
    return render_template('main.html', matches=matches, news=news)


@app.route('/matches')
def matches_list():
    db_sess = db_session.create_session()
    matches = db_sess.query(Match).all()
    return render_template('matches.html', matches=matches)


@app.route('/teams')
def teams_list():
    response = requests.get(f'https://hltv-api.vercel.app/api/player.json')
    teams = response.json()
    return render_template('teams.html', teams=teams)


@app.route('/set_language/<language>')
def set_language(language):
    if language in ['en', 'ru']:
        session['language'] = language
    return redirect(request.referrer or url_for('home'))


@app.route('/news')
def news_list():
    # db_sess = db_session.create_session()
    # news = db_sess.query(News).all()
    response = requests.get(f'https://hltv-api.vercel.app/api/news.json')
    news = response.json()
    db_sess = db_session.create_session()
    matches = db_sess.query(Match).all()
    return render_template('news.html', news=news, matches=matches)


@app.route('/match/<int:match_id>', methods=['GET', 'POST'])
def match_detail(match_id):
    db_sess = db_session.create_session()
    matches = db_sess.query(Match).all()
    match = next((m for m in matches if m.id == match_id), None)
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
def profile():
    with get_db() as conn:
        user_comments = conn.execute('''
            SELECT * FROM comments 
            WHERE user_id = ? 
            ORDER BY created_at DESC 
            LIMIT 5
        ''', (session['user_id'],)).fetchall()
    return render_template('profile.html', username=session['username'], comments=user_comments)


# Обновление профиля
@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    try:
        logging.debug("Received profile update request")
        logging.debug(f"Form data: {request.form}")
        logging.debug(f"Files: {request.files}")

        new_username = request.form.get('username')
        avatar = request.files.get('avatar')

        with get_db() as conn:
            conn.execute('UPDATE users SET username = ? WHERE id = ?',
                         (new_username, session['user_id']))

            if avatar and allowed_file(avatar.filename):
                filename = secure_filename(f"user_{session['user_id']}.jpg")
                avatar.save(os.path.join('static/uploads', filename))

            conn.commit()

        session['username'] = new_username
        logging.debug("Profile updated successfully")
        return jsonify(success=True)

    except Exception as e:
        logging.error(f"Profile update error: {str(e)}", exc_info=True)
        return jsonify(success=False, message=str(e))


# Удаление комментария
@app.route('/delete_comment/<int:comment_id>', methods=['POST'])
def delete_comment(comment_id):
    try:
        with get_db() as conn:
            conn.execute('DELETE FROM comments WHERE id = ? AND user_id = ?',
                         (comment_id, session['user_id']))
            conn.commit()
        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, message=str(e))


# Редактирование комментария
@app.route('/update_comment/<int:comment_id>', methods=['POST'])
def update_comment(comment_id):
    new_text = request.json.get('text')
    if not new_text:
        return jsonify(success=False, message="Text cannot be empty")

    try:
        with get_db() as conn:
            conn.execute('UPDATE comments SET text = ? WHERE id = ? AND user_id = ?',
                         (new_text, comment_id, session['user_id']))
            conn.commit()
        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, message=str(e))


# Проверка расширения файла
def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg'}


@app.errorhandler(400)
def bad_request(_):
    return make_response(jsonify({'error': 'Bad Request'}), 400)


def main():
    db_session.global_init("db/news_match_teams.db")
    app.register_blueprint(teams_api.blueprint)
    app.run(port=5000, host='127.0.0.1')


if __name__ == '__main__':
    init_db()
    main()
