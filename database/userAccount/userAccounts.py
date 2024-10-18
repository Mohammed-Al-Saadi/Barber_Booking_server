
import hashlib
import os

import psycopg2

from database.database_conn import get_connection


def hash_password(password):
    salt = os.urandom(16)  # Generate a new salt
    # Hash the password using the salt
    password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
    return salt, password_hash

def barber_exists(barber_id):
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute('SELECT * FROM barber_login WHERE barber_id = %s', (barber_id,))
        count = cur.fetchone()[0]
        return count > 0  # Returns True if exists, False otherwise
    finally:
        cur.close()
        conn.close()


def create_user(barber_id, username, password):
    if barber_exists(barber_id):
        return "barber_exists"  # Barber ID already exists

    conn = get_connection()
    cur = conn.cursor()

    try:
        salt, password_hash = hash_password(password)
        cur.execute('INSERT INTO barber_login (barber_id, username, password_hash, salt) VALUES (%s, %s, %s, %s)',
                    (barber_id, username, password_hash, salt))
        conn.commit()
        return "success"  # User created successfully
    except psycopg2.IntegrityError:
        conn.rollback()
        return "username_exists"  # Username already exists
    finally:
        cur.close()
        conn.close()



def verify_user(username, password):
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute('SELECT password_hash, salt, barber_id FROM barber_login WHERE username = %s', (username,))
        result = cur.fetchone()

        if result is None:
            return "user_not_found", None  # Username does not exist

        password_hash, salt, barber_id = result

        if isinstance(password_hash, memoryview):
            password_hash = bytes(password_hash)
        if isinstance(salt, memoryview):
            salt = bytes(salt)

        provided_password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)

        if provided_password_hash == password_hash:
            return "login_success", barber_id  # Return barber_id on success
        else:
            return "invalid_password", None  # Incorrect password
    finally:
        cur.close()
        conn.close()

