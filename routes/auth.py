
# route to create account
from datetime import datetime
from flask import Blueprint, jsonify, request
import jwt
import pytz

from database.get_barber_name_by_id.get_barber_name_by_id import get_barber_name_by_id
from database.userAccount.userAccounts import create_user, verify_user
from srvices.jwt.jwt_models import generate_token
finland_tz = pytz.timezone('Europe/Helsinki')
SECRET_KEY = "ndwdkw-defdef-fefefe"

signup_bp = Blueprint('signup', __name__)

@signup_bp.route('/signup', methods=['POST'])
def signup():
    barber_id = request.json.get('barber_id')
    username = request.json.get('username')
    password = request.json.get('password')

    if not barber_id or not username or not password:
        return jsonify({'error': 'Barber ID, username, and password are required!'}), 400

    result = create_user(barber_id, username, password)

    if result == "success":
        return jsonify({'message': 'User created successfully!'}), 201
    elif result == "barber_exists":
        return jsonify({'error': 'Barber ID already exists!'}), 409
    elif result == "username_exists":
        return jsonify({'error': 'Username already exists!'}), 409


login_bp = Blueprint('login_bp', __name__)

# route to login
@login_bp.route('/login', methods=['POST'])
def login():
    username = request.json.get('username')
    password = request.json.get('password')

    if not username or not password:
        return jsonify({'error': 'Username and password are required!'}), 400

    result, barber_id = verify_user(username, password)  # Ensure verify_user returns barber_id

    if result == "login_success":
        token = generate_token(barber_id)  # Generate a token with barber_id
        return jsonify({'message': 'Login successful!', 'token': token}), 200
    elif result == "user_not_found":
        return jsonify({'error': 'Username does not exist!'}), 404
    elif result == "invalid_password":
        return jsonify({'error': 'Incorrect password!'}), 401
    


protected_bp = Blueprint('protected_bp', __name__)

@protected_bp.route('/protected', methods=['GET'])
def protected_route():
    # Get the token from the Authorization header
    token = request.headers.get('Authorization')
    
    if not token:
        return jsonify({'message': 'Token is missing!'}), 401
    
    try:
        # Split the token from "Bearer <token>"
        token = token.split(" ")[1]
        data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])

        # Get the expiration timestamp from the token
        exp_timestamp = data['exp']

        # Convert the UTC expiration time to Finland time
        utc_expiration = datetime.utcfromtimestamp(exp_timestamp)
        finland_expiration = utc_expiration.replace(tzinfo=pytz.utc).astimezone(finland_tz)

        # Format the expiration time for Finland
        exp = finland_expiration.strftime('%Y-%m-%d %H:%M:%S')

        # Extract barber_id from the decoded JWT data
        barber_id = data.get('barber_id')

        if not barber_id:
            return jsonify({'message': 'Barber ID not found in token!'}), 400

        # Fetch the barber's name using the barber_id
        barber_name = get_barber_name_by_id(barber_id)

        if not barber_name:
            return jsonify({'message': 'Barber not found!'}), 404

        return jsonify({
            'barber_id': barber_id,
            'barber_name': barber_name,
            'expiration_date': exp  # Include the expiration date in Finland time
        })

    except jwt.ExpiredSignatureError:
        return jsonify({'message': 'Token has expired!'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'message': 'Token is invalid!'}), 401

