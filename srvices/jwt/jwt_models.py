from datetime import datetime, timedelta
import jwt

SECRET_KEY = "ndwdkw-defdef-fefefe"

def generate_token(barber_id):
    token = jwt.encode({
        'barber_id': barber_id,
        
        'exp': datetime.utcnow() + timedelta(hours=9)  # Token expires in 1 hour
    }, SECRET_KEY, algorithm='HS256')
    return token
