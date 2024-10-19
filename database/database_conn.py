import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Database connection details from environment variables
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

# Initialize connection_pool globally
connection_pool = None

def initialize_connection_pool(minconn=1, maxconn=10):
    """Initialize the connection pool."""
    global connection_pool
    try:
        if connection_pool is None:
            connection_pool = psycopg2.pool.SimpleConnectionPool(
                minconn, maxconn,  
                user=DB_USER,
                password=DB_PASSWORD,
                host=DB_HOST,
                port=DB_PORT,
                database=DB_NAME
            )
            if connection_pool:
                print("Connection pool created successfully")
    except Exception as e:
        print(f"Error occurred during pool initialization: {e}")

def get_connection():
    """Get a connection from the pool."""
    try:
        if connection_pool is None:
            initialize_connection_pool()  # Initialize if not already done
        return connection_pool.getconn()
    except Exception as e:
        print(f"Error occurred while getting connection: {e}")
        return None

def release_connection(conn):
    """Release a connection back to the pool."""
    try:
        if connection_pool and conn:
            connection_pool.putconn(conn)
    except Exception as e:
        print(f"Error occurred while releasing connection: {e}")

def close_connection_pool():
    """Close the connection pool."""
    try:
        if connection_pool:
            connection_pool.closeall()
            print("Connection pool closed")
    except Exception as e:
        print(f"Error occurred while closing connection pool: {e}")
