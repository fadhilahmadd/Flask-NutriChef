import os, json, pymysql
import random
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from features.image_classifier import classify_image
from flask_mail import Mail, Message

from routes.categories import categories_blueprint
from routes.meals import meals_blueprint
from routes.recipe import recipe_blueprint
from routes.categories_detect import categories_detect_blueprint
from routes.meals_detect import meals_detect_blueprint
from routes.all_categories_detect import all_categories_detect_blueprint
from routes.all_meals_detect import all_meals_detect_blueprint

app = Flask(__name__, static_folder='img')
CORS(app)

app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

app.config['SECRET_KEY'] = 'fdlahmd'
app.config['JWT_SECRET_KEY'] = 'fdlahmd'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = False
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'lalaland88'
app.config['MYSQL_DB'] = 'nutrichef'

jwt = JWTManager(app)

db = pymysql.connect(
    host=app.config['MYSQL_HOST'],
    user=app.config['MYSQL_USER'],
    password=app.config['MYSQL_PASSWORD'],
    db=app.config['MYSQL_DB']
)
cursor = db.cursor()

def get_db_connection():
    return pymysql.connect(
        host='localhost',
        user='root',
        password='lalaland88',
        db='nutrichef',
        cursorclass=pymysql.cursors.DictCursor
    )

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'fadhilhidayat27@gmail.com'
app.config['MAIL_PASSWORD'] = 'xppq olrz jsby kiiw'
app.config['MAIL_DEFAULT_SENDER'] = 'fadhilhidayat27@gmail.com'

mail = Mail(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/img/<path:filename>')
def send_file(filename):
    return send_from_directory(app.static_folder, filename)

@app.route('/upload', methods=['POST'])
def upload_files():
    if 'files[]' not in request.files:
        return jsonify({'error': 'No files part'})

    files = request.files.getlist('files[]')
    results = []

    for file in files:
        if file.filename == '':
            continue

        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        predicted_class = classify_image(file_path)

        predicted_class = predicted_class.replace('_', ' ')

        results.append({'class': predicted_class})

    return jsonify({'results': results})

# ----Auth----

def insert_user(username, email, password):
    sql = "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)"
    cursor.execute(sql, (username, email, password))
    db.commit()

def get_user(email):
    sql = "SELECT * FROM users WHERE email = %s"
    cursor.execute(sql, (email,))
    return cursor.fetchone()

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if get_user(email):
        return jsonify({'error': 'Email sudah ada'}), 400

    password_hash = generate_password_hash(password)
    insert_user(username, email, password_hash)
    return jsonify({'message': 'User registered successfully'}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    user = get_user(email)
    if not user or not check_password_hash(user[3], password):
        return jsonify({'error': 'Invalid email or password'}), 401

    token = create_access_token(identity=email, additional_claims={"sub": email}, expires_delta=False)
    return jsonify({'token': token}), 200

@app.route('/logout', methods=['POST'])
def logout():
    return jsonify({'message': 'Logout successful'}), 200

def get_username(email):
    sql = "SELECT username FROM users WHERE email = %s"
    cursor.execute(sql, (email,))
    return cursor.fetchone()

@app.route('/username/<string:email>', methods=['GET'])
def get_username_by_email(email):
    try:
        username = get_username(email)
        if username:
            return jsonify({'username': username[0]}), 200
        else:
            return jsonify({'error': 'User not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- Penyakit ---

@app.route('/penyakit', methods=['POST'])
@jwt_required()
def create_penyakit():
    data = request.get_json()
    nama = data.get('nama')
    data_json = json.dumps(data.get('data'))

    sql = "INSERT INTO penyakit (nama, data) VALUES (%s, %s)"
    try:
        cursor.execute(sql, (nama, data_json))
        db.commit()
        return jsonify({'message': 'Data inserted successfully'}), 201
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/penyakit', methods=['GET'])
@jwt_required()
def get_all_penyakit():
    sql = "SELECT * FROM penyakit"
    try:
        cursor.execute(sql)
        results = cursor.fetchall()
        penyakit_list = []
        for result in results:
            penyakit = {
                'id': result[0],
                'nama': result[1],
                'data': json.loads(result[2])
            }
            penyakit_list.append(penyakit)
        return jsonify(penyakit_list), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/nama-penyakit', methods=['GET'])
@jwt_required()
def get_nama_penyakit():
    sql = "SELECT id, nama FROM penyakit"
    try:
        cursor.execute(sql)
        results = cursor.fetchall()
        penyakit_list = []
        for result in results:
            penyakit = {
                'id': result[0],
                'nama': result[1]
            }
            penyakit_list.append(penyakit)
        return jsonify(penyakit_list), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/penyakit/<int:id>', methods=['GET'])
@jwt_required()
def get_penyakit(id):
    sql = "SELECT * FROM penyakit WHERE id = %s"
    try:
        cursor.execute(sql, (id,))
        result = cursor.fetchone()
        if result:
            penyakit = {
                'id': result[0],
                'nama': result[1],
                'data': json.loads(result[2])
            }
            return jsonify(penyakit), 200
        else:
            return jsonify({'error': 'Data not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- penyakit user ----

@app.route('/penyakit_user', methods=['POST'])
@jwt_required()
def create_penyakit_user():
    data = request.get_json()
    user_email = get_jwt_identity()

    # Fetch the user id from the email
    user_sql = "SELECT id FROM users WHERE email = %s"
    cursor.execute(user_sql, (user_email,))
    user = cursor.fetchone()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    user_id = user[0]
    penyakit_id = data.get('penyakit_id')

    sql = "INSERT INTO penyakit_user (user_id, penyakit_id) VALUES (%s, %s)"
    try:
        cursor.execute(sql, (user_id, penyakit_id))
        db.commit()
        return jsonify({'message': 'Association created successfully'}), 201
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/penyakit_user', methods=['GET'])
@jwt_required()
def get_penyakit_user():
    user_email = get_jwt_identity()

    # Fetch the user id from the email
    user_sql = "SELECT id FROM users WHERE email = %s"
    cursor.execute(user_sql, (user_email,))
    user = cursor.fetchone()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    user_id = user[0]

    sql = """
    SELECT penyakit.id, penyakit.nama FROM penyakit
    INNER JOIN penyakit_user ON penyakit.id = penyakit_user.penyakit_id
    WHERE penyakit_user.user_id = %s
    """
    try:
        cursor.execute(sql, (user_id,))
        results = cursor.fetchall()
        penyakit_list = []
        for result in results:
            penyakit = {
                'id': result[0],
                'nama': result[1]
            }
            penyakit_list.append(penyakit)
        return jsonify(penyakit_list), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/user/penyakit', methods=['GET'])
@jwt_required()
def get_user_penyakit():
    user_email = get_jwt_identity()

    try:
        db = get_db_connection()
        cursor = db.cursor()

        sql_user = "SELECT id FROM users WHERE email = %s"
        cursor.execute(sql_user, (user_email,))
        user = cursor.fetchone()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        user_id = user['id']

        sql_penyakit_user = """
        SELECT pu.id AS penyakit_user_id, pu.penyakit_id, p.nama, p.data
        FROM penyakit_user pu
        JOIN penyakit p ON pu.penyakit_id = p.id
        WHERE pu.user_id = %s
        """
        cursor.execute(sql_penyakit_user, (user_id,))
        results = cursor.fetchall()

        penyakit_user_list = []
        for result in results:
            penyakit_user = {
                'penyakit_user_id': result['penyakit_user_id'],
                'penyakit_id': result['penyakit_id'],
                'nama': result['nama'],
                'data': json.loads(result['data'])
            }
            penyakit_user_list.append(penyakit_user)

        cursor.close()
        db.close()

        return jsonify(penyakit_user_list), 200
    except Exception as e:
        print(f"Error fetching user diseases: {str(e)}")
        return jsonify({'error': str(e)}), 500

otp_storage = {}

def generate_otp():
    return str(random.randint(100000, 999999))

@app.route('/send-otp', methods=['POST'])
def send_otp():
    data = request.get_json()
    email = data.get('email')
    user = get_user(email)

    if not user:
        return jsonify({'error': 'Email tidak ditemukan'}), 404

    otp = generate_otp()
    otp_storage[email] = otp

    msg = Message('Your OTP Code', recipients=[email])
    msg.body = f'Your OTP code is {otp}'
    mail.send(msg)

    return jsonify({'message': 'OTP sent'}), 200

@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    data = request.get_json()
    email = data.get('email')
    otp = data.get('otp')

    if otp_storage.get(email) == otp:
        return jsonify({'message': 'OTP verified'}), 200
    else:
        return jsonify({'error': 'Invalid OTP'}), 400

@app.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json()
    email = data.get('email')
    new_password = data.get('password')

    user = get_user(email)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    password_hash = generate_password_hash(new_password)
    sql = "UPDATE users SET password = %s WHERE email = %s"
    cursor.execute(sql, (password_hash, email))
    db.commit()

    return jsonify({'message': 'Password reset successful'}), 200

app.register_blueprint(categories_blueprint)
app.register_blueprint(meals_blueprint)
app.register_blueprint(recipe_blueprint)
app.register_blueprint(categories_detect_blueprint)
app.register_blueprint(meals_detect_blueprint)
app.register_blueprint(all_categories_detect_blueprint)
app.register_blueprint(all_meals_detect_blueprint)

if __name__ == '__main__':
    app.run(host='192.168.0.192', port=5000, debug=True)