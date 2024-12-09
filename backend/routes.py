from flask import Blueprint, render_template, request, redirect, url_for, session
from geopy import distance
import random
from app import get_db_connection

routes = Blueprint('routes', __name__)

@routes.route('/')
def index():
    return render_template('index.html')

@routes.route('/start_game', methods=['POST'])
def start_game():
    session['difficulty'] = request.form.get('difficulty')
    session['current_airport'] = "EFHK"
    session['visited_airports'] = ["EFHK"]
    session['remaining_time'] = 300 if session['difficulty'] == "hard" else 420 if session['difficulty'] == "normal" else 480
    session['player_distance'] = 2000 if session['difficulty'] == "hard" else 3000 if session['difficulty'] == "normal" else 4000
    session['goal_airport'] = random.choice(['EFIV', 'EFOU', 'EFKS', 'EFKT', 'EFKE'])
    return redirect(url_for('routes.game'))

@routes.route('/game')
def game():
    connection = get_db_connection()  # Hakee tietokantayhteyden
    lentokentat = get_airport_info(connection)
    current_airport = session['current_airport']
    visited_airports = session['visited_airports']
    remaining_time = session['remaining_time']
    player_distance = session['player_distance']

    nearby_airports = get_nearby_airports(lentokentat, current_airport, visited_airports, remaining_time, player_distance)
    connection.close()  # Sulkee yhteyden, kun sitä ei enää tarvita

    if not nearby_airports:
        return redirect(url_for('routes.game_over', reason='no_airports'))

    return render_template('index.html', airports=nearby_airports, time=remaining_time, distance=player_distance)

@routes.route('/travel', methods=['POST'])
def travel():
    lentokentta_id = request.form.get('airport_id')
    lentokentta_etaisyys = float(request.form.get('distance'))
    lentoaika = int(request.form.get('travel_time'))

    session['remaining_time'] -= lentoaika
    session['player_distance'] -= lentokentta_etaisyys
    session['current_airport'] = lentokentta_id
    session['visited_airports'].append(lentokentta_id)

    if session['remaining_time'] <= 0:
        return redirect(url_for('routes.game_over', reason='time'))
    if session['player_distance'] <= 0:
        return redirect(url_for('routes.game_over', reason='fuel'))
    if session['current_airport'] == session['goal_airport']:
        return redirect(url_for('routes.victory'))

    return redirect(url_for('routes.game'))

@routes.route('/game_over')
def game_over():
    reason = request.args.get('reason')
    connection = get_db_connection()
    update_losses(connection, session.get('player_name', 'unknown'))
    connection.close()
    return render_template('index.html', reason=reason)

@routes.route('/victory')
def victory():
    connection = get_db_connection()
    time_used = (7 * 60 if session['difficulty'] == 'easy' else 5 * 60) - session['remaining_time']
    distance_traveled = (3000 if session['difficulty'] == 'easy' else 2000) - session['player_distance']
    update_wins(connection, session.get('player_name', 'unknown'), time_used)
    update_distance_traveled(connection, session.get('player_name', 'unknown'), distance_traveled)
    connection.close()
    return render_template('index.html')

# Apufunktiot
def get_airport_info(connection):
    cursor = connection.cursor(dictionary=True)
    sql = "SELECT ident, name, latitude_deg, longitude_deg FROM airport WHERE iso_country = 'FI' AND type IN ('medium_airport', 'large_airport')"
    cursor.execute(sql)
    result = cursor.fetchall()
    cursor.close()
    return result

def get_nearby_airports(lentokentat, current, visited, remaining_time, kilsat_pelaaja):
    current_lat, current_lng = None, None
    for airport in lentokentat:
        if airport["ident"] == current:
            current_lat = airport["latitude_deg"]
            current_lng = airport["longitude_deg"]
            break

    if current_lat is None or current_lng is None:
        raise ValueError("Nykyistä lentokenttää ei löytynyt.")

    etaisyydet = []
    for details in lentokentat:
        ident = details["ident"]
        if ident == current or ident in visited:
            continue
        etaisyys = etaisyyden_lasku((current_lat, current_lng), (details['latitude_deg'], details['longitude_deg']))
        tunnit, minuutit = lentoaika(etaisyys)
        matka_aika = tunnit * 60 + minuutit
        if matka_aika <= remaining_time and etaisyys <= kilsat_pelaaja:
            etaisyydet.append({"id": ident, "name": details["name"], "distance": etaisyys, "travel_time": matka_aika})

    return sorted(etaisyydet, key=lambda x: x["distance"])[:5]

def etaisyyden_lasku(start_coords, end_coords):
    return distance.distance(start_coords, end_coords).km

def lentoaika(etaisyys_km):
    vakioaika_100_km = 15
    lentoaika_minuutit = (etaisyys_km / 100) * vakioaika_100_km
    tunnit = int(lentoaika_minuutit // 60)
    minuutit = int(lentoaika_minuutit % 60)
    return tunnit, minuutit

def update_wins(connection, player_name, time_used):
    cursor = connection.cursor()
    time_str = f"{time_used // 60}:{time_used % 60:02d}"
    update_sql = "UPDATE player_stats SET wins = wins + 1, time_used = %s WHERE player_name = %s"
    cursor.execute(update_sql, (time_str, player_name))
    connection.commit()
    cursor.close()

def update_losses(connection, player_name):
    cursor = connection.cursor()
    update_sql = "UPDATE player_stats SET losses = losses + 1 WHERE player_name = %s"
    cursor.execute(update_sql, (player_name,))
    connection.commit()
    cursor.close()

def update_distance_traveled(connection, player_name, distance_traveled):
    cursor = connection.cursor()
    sql_query = "UPDATE player_stats SET distance_traveled = %s WHERE player_name = %s"
    cursor.execute(sql_query, (distance_traveled, player_name))
    connection.commit()
    cursor.close()

def init_app(app):
    app.register_blueprint(routes)

