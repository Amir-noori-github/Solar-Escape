from flask import Flask, Blueprint, render_template, request, session, jsonify
from geopy.distance import geodesic as calculate_distance
import random
import mysql.connector
from flask_cors import CORS
from dotenv import load_dotenv
import os

load_dotenv()

def create_app():
    app = Flask(__name__)
    CORS(app)
    app.secret_key = 'salasana'
    app.register_blueprint(routes, url_prefix='/')
    return app

def get_db_connection():
    return mysql.connector.connect(
        host='127.0.0.1',
        port=3306,
        database='flight_game',
        user='root',
        password='salasana',
        autocommit=True,
        collation='utf8mb4_general_ci'
    )

# Blueprint for route definitions
routes = Blueprint('routes', __name__)

@routes.route('/')
def index():
    return render_template('index.html')

@routes.route('/about')
def about():
    print(session)  # Lisää tämä jokaisen reitin alkuun debuggausta varten
    player_name = session.get('player_name')  # Fetch the player's name from session
    if not player_name:
        # Redirect user or return a message if session is empty
        return render_template('about.html', player_stats=None)

    connection = get_db_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT player_name, wins, losses, airports_visited, num_airports_visited, distance_traveled
            FROM player_stats
            WHERE player_name = %s
        """, (player_name,))
        player_stats = cursor.fetchone()
        return render_template('about.html', player_stats=player_stats)
    finally:
        connection.close()


@routes.route('/airports', methods=['GET'])
def get_all_airports():
    connection = get_db_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT ident, name, latitude_deg, longitude_deg 
            FROM airport 
            WHERE iso_country = 'FI' AND type IN ('medium_airport', 'large_airport')
        """)
        airports = cursor.fetchall()
        return jsonify(airports), 200
    finally:
        connection.close()

@routes.route('/newgame', methods=['GET'])
def new_game():
    """Initialize a new game session and update player stats in the database."""
    player_name = request.args.get('player')
    start_location = request.args.get('loc')

    if not player_name or not start_location:
        return jsonify({"error": "Missing player or location parameters."}), 400

    connection = get_db_connection()
    try:
        cursor = connection.cursor(dictionary=True)

        # Hae aloituspaikan tiedot
        cursor.execute("""
            SELECT name, latitude_deg, longitude_deg 
            FROM airport 
            WHERE ident = %s
        """, (start_location,))
        start_airport = cursor.fetchone()

        if not start_airport:
            return jsonify({"error": "Starting location not found."}), 404

        # Alusta pelaajan tilastot tauluun
        cursor.execute("""
            INSERT INTO player_stats (player_name, wins, losses, airports_visited, num_airports_visited, time_used, distance_traveled)
            VALUES (%s, 0, 0, '', 0, 0, 0)
            ON DUPLICATE KEY UPDATE player_name = %s
        """, (player_name, player_name))

        # Määritä pelin tila sessioon
        predefined_airports = ['EFIV', 'EFOU', 'EFKS', 'EFKT', 'EFKE']
        session['goal_airports'] = [random.choice(predefined_airports)]

        session.update({
            'player_name': player_name,
            'current_airport': start_location,
            'visited_airports': [start_location],
            'remaining_time': 150,
            'remaining_distance': 1000
        })

        return jsonify({
            "name": player_name,
            "remaining_time": session['remaining_time'],
            "remaining_distance": session['remaining_distance'],
            "current_location": start_airport['name'],
            "locations": get_airports_with_distances(start_location),
            "goal_airports": session['goal_airports']
        }), 200
    finally:
        connection.close()

@routes.route('/flyto', methods=['GET'])
def fly_to():
    """Handle flight to a new airport and update the game state."""
    destination_id = request.args.get('dest')
    if not destination_id:
        return jsonify({"error": "Destination airport not provided."}), 400

    connection = get_db_connection()
    try:
        # Hae kohdelentokentän tiedot
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT name, latitude_deg, longitude_deg 
            FROM airport 
            WHERE ident = %s
        """, (destination_id,))
        destination = cursor.fetchone()

        if not destination:
            return jsonify({"error": "Destination not found."}), 404

        # Lasketaan matka ja aika
        distance = calculate_distance_from_start(session['current_airport'], destination)
        flight_time = calculate_flight_time(distance)

        # Tarkistetaan, riittävätkö aika ja matka
        if session['remaining_distance'] < distance or session['remaining_time'] < flight_time:
            cursor.execute("""
                UPDATE player_stats
                SET losses = losses + 1
                WHERE player_name = %s
            """, (session['player_name'],))

            session['remaining_time'] = 150
            session['remaining_distance'] = 1500
            session['visited_airports'] = []

            return jsonify({
                "message": "Time or distance is insufficient. You lost. Restarting game.",
                "status": "restart",
                "remaining_time": session['remaining_time'],
                "remaining_distance": session['remaining_distance'],
                "current_location": session['current_airport'],
                "locations": get_airports_with_distances(session['current_airport']),
                "goal_airports": session['goal_airports']
            }), 200

        # Päivitä pelitilanne
        session['remaining_distance'] -= distance
        session['remaining_time'] -= flight_time
        session['current_airport'] = destination_id
        session['visited_airports'].append(destination_id)

        # Päivitä pelaajan statistiikat tietokantaan
        cursor.execute("""
            UPDATE player_stats
            SET 
                airports_visited = %s,
                num_airports_visited = %s,
                time_used = time_used + %s,
                distance_traveled = distance_traveled + %s
            WHERE player_name = %s
        """, (
            ','.join(session['visited_airports']),
            len(session['visited_airports']),
            flight_time,
            distance,
            session['player_name']
        ))

        # Tarkistetaan, onko nykyinen lentokenttä suojapaikka
        if destination_id == session['goal_airports'][0]:
            cursor.execute("""
                UPDATE player_stats
                SET wins = wins + 1
                WHERE player_name = %s
            """, (session['player_name'],))

            return jsonify({
                "message": "You found the protected area! Game Over. Congratulations!",
                "status": "victory",
                "remaining_time": session['remaining_time'],
                "remaining_distance": session['remaining_distance'],
                "current_location": destination['name'],
                "locations": get_airports_with_distances(destination_id)
            }), 200

        return jsonify({
            "remaining_time": session['remaining_time'],
            "remaining_distance": session['remaining_distance'],
            "current_location": destination['name'],
            "locations": get_airports_with_distances(destination_id),
            "goal_airports": session['goal_airports']
        }), 200
    finally:
        connection.close()

def get_airports_with_distances(start_location):
    connection = get_db_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT ident, name, latitude_deg, longitude_deg 
            FROM airport 
            WHERE iso_country = 'FI' AND type IN ('medium_airport', 'large_airport')
        """)
        airports = cursor.fetchall()
        start_coords = get_airport_coordinates(start_location)

        airports_with_distances = [{
            "id": airport['ident'],
            "name": airport['name'],
            "latitude": airport['latitude_deg'],
            "longitude": airport['longitude_deg'],
            "distance": calculate_distance(start_coords, (airport['latitude_deg'], airport['longitude_deg'])).km
        } for airport in airports]

        return sorted(airports_with_distances, key=lambda x: x['distance'])[:6]
    finally:
        connection.close()

def get_airport_coordinates(airport_id):
    connection = get_db_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT latitude_deg, longitude_deg FROM airport WHERE ident = %s", (airport_id,))
        result = cursor.fetchone()
        return (result['latitude_deg'], result['longitude_deg']) if result else (0, 0)
    finally:
        connection.close()

def calculate_distance_from_start(start_airport, destination_airport):
    start_coords = get_airport_coordinates(start_airport)
    return calculate_distance(start_coords, (destination_airport['latitude_deg'], destination_airport['longitude_deg'])).km

def calculate_flight_time(distance_km):
    return (distance_km / 100) * 15

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='127.0.0.1', port=3000)
