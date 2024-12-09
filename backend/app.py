from flask import Flask
import mysql.connector
from dotenv import load_dotenv
from flask_cors import CORS



def get_db_connection():
    connection = mysql.connector.connect(
        host='127.0.0.1',
        port=3306,
        database='flight_game',
        user='root',
        password='salasana',
        autocommit=True,
        collation='utf8mb4_general_ci'
    )
    return connection

app = Flask(__name__)
CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

if __name__ == '__main__':
    app.run(use_reloader=True, host='127.0.0.1', port=5000)
