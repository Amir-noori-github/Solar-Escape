from flask import Flask, Blueprint, render_template, request, redirect, url_for, session, jsonify
from geopy.distance import geodesic as calculate_distance
import random
import mysql.connector
from flask_cors import CORS

# Initialize the Flask application and Blueprint
def create_app():
    app = Flask(__name__)
    CORS(app)
    app.config['CORS_HEADERS'] = 'Content-Type'
    app.secret_key = 'salasana'  # Replace with a strong secret key

    # Register routes blueprint
    app.register_blueprint(routes, url_prefix='/')
    return app

# Database connection function
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

# Initialize Blueprint
routes = Blueprint('routes', __name__)

# Route to serve the index page
@routes.route('/')
def index():
    return render_template('index.html')

# Start a new game
@routes.route('/newgame', methods=['GET'])
def new_game():
    player_name = request.args.get('player')
    start_location = request.args.get('loc')

    if not player_name or not start_location:
        return jsonify({"error": "Missing player or location parameters."}), 400

    session['player_name'] = player_name
    session['current_airport'] = start_location
    session['visited_airports'] = [start_location]
    session['remaining_time'] = 420  # 420 minutes
    session['player_distance'] = 3000  # 3000 km
    session['remaining_distance'] = session['player_distance']  # Lisää tämä
    session['goal_airport'] = random.choice(['EFIV', 'EFOU', 'EFKS', 'EFKT', 'EFKE'])

    game_data = {
        "name": player_name,
        "remaining_time": session['remaining_time'],
        "remaining_distance": session['remaining_distance'],  # Päivitä myös tähän
        "locations": get_initial_locations(start_location),
        "goal_airport": session['goal_airport'],
    }

    return jsonify(game_data), 200

# Fly to a new airport
@routes.route('/flyto', methods=['GET'])
def fly_to():
    print(session)  # Debug: Tulosta session sisältö
    player = request.args.get('player')
    destination_id = request.args.get('dest')

    if not player or not destination_id:
        return jsonify({"error": "Missing player or destination parameters."}), 400

    connection = get_db_connection()
    try:
        # Get destination airport details
        destination = get_airport_by_id(connection, destination_id)
        if not destination:
            return jsonify({"error": "Destination airport not found."}), 404

        current_airport = session.get('current_airport')
        print(current_airport)  # Debug: Tulosta nykyinen lentokenttä
        distance_to_airport = calculate_distance_from_start(current_airport, destination)

        # Tarkista, onko pelaajalla riittävästi matkaa jäljellä
        if session.get('remaining_distance', 0) < distance_to_airport:
            return jsonify({"error": "Not enough remaining distance to travel."}), 400

        # Tarkista, onko pelaajalla riittävästi aikaa jäljellä
        flight_time = calculate_flight_time(distance_to_airport)
        if session.get('remaining_time', 0) < flight_time:
            return jsonify({"error": "Not enough remaining time to travel."}), 400

        # Päivitä session muuttujat
        session['remaining_distance'] -= distance_to_airport
        session['remaining_time'] -= flight_time
        session['current_airport'] = destination_id
        session['visited_airports'].append(destination_id)

        # Tarkista, onko pelaaja saavuttanut tavoitekentän
        if session['current_airport'] == session['goal_airport']:
            return jsonify({"message": "Congratulations! You reached your goal airport.", "status": "victory"}), 200

        # Valmistele pelin tilatiedot vastaukseen
        game_data = {
            "name": session['player_name'],
            "remaining_time": session['remaining_time'],
            "remaining_distance": session['remaining_distance'],
            "current_location": session['current_airport'],
            "locations": get_initial_locations(session['current_airport']),
            "goal_airport": session['goal_airport'],
        }

        return jsonify(game_data), 200
    finally:
        connection.close()

# Game over route
@routes.route('/game_over')
def game_over():
    reason = request.args.get('reason')
    return render_template('game_over.html', reason=reason)

# Victory route
@routes.route('/victory')
def victory():
    return render_template('victory.html')

# Helper functions
def get_airport_info(connection):
    cursor = connection.cursor(dictionary=True)
    cursor.execute("""
        SELECT ident, name, latitude_deg, longitude_deg 
        FROM airport 
        WHERE iso_country = 'FI' AND type IN ('medium_airport', 'large_airport')
    """)
    result = cursor.fetchall()
    cursor.close()
    return result

def get_airport_by_id(connection, airport_id):
    cursor = connection.cursor(dictionary=True)
    cursor.execute("""
        SELECT ident, name, latitude_deg, longitude_deg 
        FROM airport 
        WHERE ident = %s
    """, (airport_id,))
    result = cursor.fetchone()
    cursor.close()
    return result

def get_initial_locations(start_location):
    connection = get_db_connection()
    try:
        airports = get_airport_info(connection)
        start_coords = get_airport_coordinates(start_location)

        locations = []
        for airport in airports:
            airport_coords = (airport['latitude_deg'], airport['longitude_deg'])
            distance_to_airport = calculate_distance(start_coords, airport_coords).km
            locations.append({
                "id": airport['ident'],
                "name": airport['name'],
                "latitude": airport['latitude_deg'],
                "longitude": airport['longitude_deg'],
                "distance": distance_to_airport,
                "active": airport['ident'] == start_location,
            })

        return locations
    finally:
        connection.close()

def get_airport_coordinates(airport_id):
    connection = get_db_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT latitude_deg, longitude_deg 
            FROM airport 
            WHERE ident = %s
        """, (airport_id,))
        result = cursor.fetchone()
        return (result['latitude_deg'], result['longitude_deg']) if result else (0, 0)
    finally:
        connection.close()

def calculate_distance_from_start(start_location, airport):
    start_coords = get_airport_coordinates(start_location)
    airport_coords = (airport['latitude_deg'], airport['longitude_deg'])
    return calculate_distance(start_coords, airport_coords).km

def calculate_flight_time(distance_km):
    avg_speed_per_100km = 15  # Minutes per 100 km
    return (distance_km / 100) * avg_speed_per_100km

# Run the Flask app
if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='127.0.0.1', port=3000)

