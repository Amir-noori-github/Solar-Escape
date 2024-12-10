from flask import Flask, Blueprint, render_template, request, session, jsonify
from geopy.distance import geodesic as calculate_distance
import random
import mysql.connector
from flask_cors import CORS

# Flask uygulamasını başlatan fonksiyon
def create_app():
    app = Flask(__name__)
    CORS(app)  # Allow Cross-Origin Resource Sharing
    app.secret_key = 'salasana'  # Secret key for session management
    app.register_blueprint(routes, url_prefix='/')  # Register routes
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

@routes.route('/airports', methods=['GET'])
def get_all_airports():
    """Fetch all medium and large airports in Finland."""
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
    """Initialize a new game session."""
    player_name = request.args.get('player')  # Player's name
    start_location = request.args.get('loc')  # Starting airport

    # Validate inputs
    if not player_name or not start_location:
        return jsonify({"error": "Missing player or location parameters."}), 400

    # Fetch all eligible airports from the database to select random protected areas
    connection = get_db_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT ident 
            FROM airport 
            WHERE iso_country = 'FI' AND type IN ('medium_airport', 'large_airport')
        """)
        all_airports = [airport['ident'] for airport in cursor.fetchall()]
        session['goal_airports'] = random.sample(all_airports, 5)  # Randomly select 5 airports as protected areas
    finally:
        connection.close()

    # Initialize game session variables
    session.update({
        'player_name': player_name,
        'current_airport': start_location,
        'visited_airports': [start_location],
        'remaining_time': 600,  # 600 minutes to complete the game
        'remaining_distance': 5000  # 5000 km to complete the game
    })

    # Return the initial game state
    return jsonify({
        "name": player_name,
        "remaining_time": session['remaining_time'],
        "remaining_distance": session['remaining_distance'],
        "current_location": session['current_airport'],
        "locations": get_airports_with_distances(start_location)
    }), 200

@routes.route('/flyto', methods=['GET'])
def fly_to():
    """Handle flight to a new airport and update the game state."""
    destination_id = request.args.get('dest')  # Target destination ID

    if not destination_id:
        return jsonify({"error": "Destination airport not provided."}), 400

    connection = get_db_connection()
    try:
        # Fetch details of the destination airport
        destination = get_airport_by_id(connection, destination_id)
        if not destination:
            return jsonify({"error": "Destination not found."}), 404

        # Calculate distance and flight time
        distance = calculate_distance_from_start(session['current_airport'], destination)
        flight_time = calculate_flight_time(distance)

        # Check if the player has enough time and distance left
        if session['remaining_distance'] < distance or session['remaining_time'] < flight_time:
            session['remaining_time'] = 420
            session['remaining_distance'] = 3000
            session['visited_airports'] = []
            return jsonify({
                "message": "Time or distance is insufficient. Restarting game.",
                "status": "restart",
                "remaining_time": session['remaining_time'],
                "remaining_distance": session['remaining_distance'],
                "current_location": session['current_airport'],
                "locations": get_airports_with_distances(session['current_airport'])
            }), 200

        # Update game session
        session['remaining_distance'] -= distance
        session['remaining_time'] -= flight_time
        session['current_airport'] = destination_id
        session['visited_airports'].append(destination_id)

        # Check if the player reached a protected area
        if destination_id in session['goal_airports']:
            session['goal_airports'].remove(destination_id)
            if len(session['goal_airports']) == 0:  # All protected airports found
                return jsonify({
                    "message": "You found all protected areas! Game Over. Congratulations!",
                    "status": "victory",
                    "remaining_time": session['remaining_time'],
                    "remaining_distance": session['remaining_distance'],
                    "current_location": session['current_airport'],
                    "locations": get_airports_with_distances(destination_id)
                }), 200
            else:
                return jsonify({
                    "message": f"You found a protected area: {destination_id}. Keep going!",
                    "status": "goal",
                    "remaining_time": session['remaining_time'],
                    "remaining_distance": session['remaining_distance'],
                    "current_location": session['current_airport'],
                    "locations": get_airports_with_distances(destination_id)
                }), 200

        # Return the updated game state
        return jsonify({
            "remaining_time": session['remaining_time'],
            "remaining_distance": session['remaining_distance'],
            "current_location": session['current_airport'],
            "locations": get_airports_with_distances(destination_id)
        }), 200
    finally:
        connection.close()

# Helper function to get airport details by ID
def get_airport_by_id(connection, airport_id):
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT ident, latitude_deg, longitude_deg FROM airport WHERE ident = %s", (airport_id,))
    result = cursor.fetchone()
    cursor.close()
    return result

# Helper function to retrieve airports with distances from a given location
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

        # Add distance to each airport
        return [{
            "id": airport['ident'],
            "name": airport['name'],
            "latitude": airport['latitude_deg'],
            "longitude": airport['longitude_deg'],
            "distance": calculate_distance(start_coords, (airport['latitude_deg'], airport['longitude_deg'])).km
        } for airport in airports]
    finally:
        connection.close()

# Helper function to get coordinates of an airport by ID
def get_airport_coordinates(airport_id):
    connection = get_db_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT latitude_deg, longitude_deg FROM airport WHERE ident = %s", (airport_id,))
        result = cursor.fetchone()
        return (result['latitude_deg'], result['longitude_deg']) if result else (0, 0)
    finally:
        connection.close()

# Helper function to calculate distance between two locations
def calculate_distance_from_start(start_airport, destination_airport):
    start_coords = get_airport_coordinates(start_airport)
    return calculate_distance(start_coords, (destination_airport['latitude_deg'], destination_airport['longitude_deg'])).km

# Helper function to calculate flight time based on distance
def calculate_flight_time(distance_km):
    return (distance_km / 100) * 15  # 15 minutes per 100 km


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='127.0.0.1', port=3000)

