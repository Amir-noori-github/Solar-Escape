import mysql.connector


def get_db_connection():
    # Veritabanına bağlanmak için fonksiyon
    return mysql.connector.connect(
        host='127.0.0.1',  # Sunucu adresi
        port=3306,  # Port numarası
        database='solardata',  # Veritabanı adı
        user='root',  # Kullanıcı adı
        password='1234',  # Parola
        autocommit=True,
        collation='utf8mb4_general_ci'
    )


def test_query():
    connection = get_db_connection()
    try:
        cursor = connection.cursor(dictionary=True)

        # Veritabanından havalimanlarını alacak sorgu
        cursor.execute("""
            SELECT ident, name, latitude_deg, longitude_deg 
            FROM airport 
            WHERE iso_country = 'FI' AND type IN ('medium_airport', 'large_airport')
        """)

        # Sorgu sonuçlarını alıyoruz
        airports = cursor.fetchall()

        # Sonuçları ekrana yazdırıyoruz
        if airports:
            for airport in airports:
                print(
                    f"Ident: {airport['ident']}, Name: {airport['name']}, Latitude: {airport['latitude_deg']}, Longitude: {airport['longitude_deg']}")
        else:
            print("Hiç havalimanı bulunamadı.")
    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        connection.close()


# Test sorgusunu çalıştır
test_query()
from flask import Flask, Blueprint, render_template, request, session, jsonify
from geopy.distance import geodesic as calculate_distance
import random
import mysql.connector
from flask_cors import CORS

# Function to initialize the Flask application
def create_app():
    app = Flask(__name__)  # Create a Flask application instance
    CORS(app)  # Enable Cross-Origin Resource Sharing (CORS)
    app.secret_key = 'salasana'  # Secret key for session management
    app.register_blueprint(routes, url_prefix='/')  # Register Blueprint for routing
    return app

# Function to establish a database connection
def get_db_connection():
    return mysql.connector.connect(
        host='127.0.0.1',
        port=3306,
        database='solardata',
        user='root',
        password='1234',
        autocommit=True ,
        collation = 'utf8mb4_general_ci'
    )

# Define a Blueprint for routes
routes = Blueprint('routes', __name__)

# Route to render the home page
@routes.route('/')
def index():
    return render_template('index.html')  # Returns the main HTML page

# Route to fetch all airports in Finland
@routes.route('/airports', methods=['GET'])
def get_all_airports():
    """Fetch all Finland airports of type medium and large."""
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

# Route to start a new game
@routes.route('/newgame', methods=['GET'])
def new_game():
    player_name = request.args.get('player')  # Get player name from URL parameters
    start_location = request.args.get('loc')  # Get starting location from URL parameters
    print (player_name, start_location)
    # Validate required parameters
    if not player_name or not start_location:
        return jsonify({"error": "Missing player or location parameters."}), 400

    # Initialize game session variables
    session.update({
        'player_name': player_name,
        'current_airport': start_location,
        'visited_airports': [start_location],
        'remaining_time': 420,  # Player starts with 420 minutes
        'remaining_distance': 3000,  # 3000 km total distance
        'goal_airport': random.choice(['EFIV', 'EFOU', 'EFKS', 'EFKT', 'EFKE'])  # Random target airport
    })

    # Return initial game state as JSON
    game_data = {
        "name": player_name,
        "remaining_time": session['remaining_time'],
        "remaining_distance": session['remaining_distance'],
        "locations": get_initial_locations(start_location)  # List of airports
    }
    return jsonify(game_data), 200

# Route to handle flying to a new airport
@routes.route('/flyto', methods=['GET'])
def fly_to():
    destination_id = request.args.get('dest')  # Get the target destination

    # Validate destination
    if not destination_id:
        return jsonify({"error": "Destination airport not provided."}), 400

    connection = get_db_connection()
    try:
        # Fetch destination details
        destination = get_airport_by_id(connection, destination_id)
        if not destination:
            return jsonify({"error": "Destination not found."}), 404

        # Calculate distance and flight time
        distance = calculate_distance_from_start(session['current_airport'], destination)
        flight_time = calculate_flight_time(distance)

        # Check if the player has enough time and distance left
        if session['remaining_distance'] < distance or session['remaining_time'] < flight_time:
            return jsonify({"error": "Not enough distance or time."}), 400

        # Update session variables
        session['remaining_distance'] -= distance
        session['remaining_time'] -= flight_time
        session['current_airport'] = destination_id
        session['visited_airports'].append(destination_id)

        # Check if the player has reached the goal airport
        if destination_id == session['goal_airport']:
            return jsonify({"message": "You reached the goal!", "status": "victory"}), 200

        # Return updated game state
        game_data = {
            "name": session['player_name'],
            "remaining_time": session['remaining_time'],
            "remaining_distance": session['remaining_distance'],
            "current_location": session['current_airport'],
            "locations": get_initial_locations(destination_id)
        }
        return jsonify(game_data), 200
    finally:
        connection.close()

# Helper function to get airport details by ID
def get_airport_by_id(connection, airport_id):
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT ident, latitude_deg, longitude_deg FROM airport WHERE ident = %s", (airport_id,))
    result = cursor.fetchone()
    cursor.close()
    return result

# Helper function to retrieve a list of initial airports
def get_initial_locations(start_location):
    connection = get_db_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT ident, name, latitude_deg, longitude_deg 
            FROM airport 
            WHERE iso_country = 'FI' AND type IN ('medium_airport', 'large_airport')
            ORDER BY RAND() LIMIT 5
        """)
        airports = cursor.fetchall()
        cursor.close()

        # Get coordinates for the start location
        start_coords = get_airport_coordinates(start_location)

        # Calculate distance for each airport and return a list
        return [{
            "id": airport['ident'],
            "name": airport['name'],
            "latitude": airport['latitude_deg'],
            "longitude": airport['longitude_deg'],
            "distance": calculate_distance(start_coords, (airport['latitude_deg'], airport['longitude_deg'])).km
        } for airport in airports]
    finally:
        connection.close()

# Helper function to get airport coordinates by ID
def get_airport_coordinates(airport_id):
    connection = get_db_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT latitude_deg, longitude_deg FROM airport WHERE ident = %s", (airport_id,))
        result = cursor.fetchone()
        return (result['latitude_deg'], result['longitude_deg']) if result else (0, 0)
    finally:
        connection.close()

# Helper function to calculate distance between two airports
def calculate_distance_from_start(start_airport, destination_airport):
    start_coords = get_airport_coordinates(start_airport)
    destination_coords = (destination_airport['latitude_deg'], destination_airport['longitude_deg'])
    return calculate_distance(start_coords, destination_coords).km

# Helper function to calculate flight time based on distance
def calculate_flight_time(distance_km):
    return (distance_km / 100) * 15  # 15 minutes per 100 km

# Run the Flask application
if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='127.0.0.1', port=3000)