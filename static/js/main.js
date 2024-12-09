'use strict';

/* 1. Show map using Leaflet library. (L comes from the Leaflet library) */
const map = L.map('map', { tap: false });
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '',
}).addTo(map);

map.setView([60, 24], 7); // Start map centered on Finland

// Global variables
const apiUrl = 'http://127.0.0.1:5000/'; // Flask server endpoint
const startLoc = 'EFHK'; // Default starting airport (Helsinki-Vantaa)
const airportMarkers = L.featureGroup().addTo(map); // Group to hold all airport markers

// Icons for markers
const blueIcon = L.divIcon({ className: 'blue-icon' });
const greenIcon = L.divIcon({ className: 'green-icon' });

// Form for player name
document.querySelector('#player-form').addEventListener('submit', function (evt) {
    evt.preventDefault(); // Prevent default form submission (page reload)

    const playerName = document.querySelector('#player-input').value; // Get the entered name

    if (playerName.trim() !== '') { // Check if name is not empty
        // Hide the modal and backdrop
        document.querySelector('#player-modal').classList.remove('show');
        document.querySelector('.modal-backdrop')?.classList.remove('show');

        // Start the game or perform the desired action
        console.log(`Player name: ${playerName}`);
        gameSetup(`${apiUrl}newgame?player=${playerName}&loc=${startLoc}`);
    } else {
        alert('Please enter a valid name.'); // Show error if the name is empty
    }
});

// Function to fetch data from API
async function getData(url) {
    const response = await fetch(url);
    if (!response.ok) throw new Error('Invalid server input!');
    const data = await response.json();
    return data;
}

// Function to update the player's status
function updateGameStatus(status) {
    const activeLocation = status.locations.find(loc => loc.active);
    document.querySelector('#current-location').innerHTML = activeLocation ? activeLocation.name : 'Unknown';
    document.querySelector('#player-distance').innerHTML = `${status.remaining_distance} km`;
    document.querySelector('#player-time').innerHTML = `${status.remaining_time} min`;
}

// Function to set up the game
async function gameSetup(playerUrl) {
    try {
        // Clear existing markers on the map
        airportMarkers.clearLayers();

        // Fetch game data from the server (using the passed playerUrl)
        const gameData = await getData(playerUrl);
        console.log('Game data received:', gameData);

        // Update game status UI
        updateGameStatus(gameData);

        // Loop through the locations (airports) provided by the gameData
        for (let airport of gameData.locations) {
            const marker = L.marker([airport.latitude, airport.longitude]).addTo(airportMarkers);

            // Check if the airport is the player's starting point
            if (airport.active) {
                marker.setIcon(greenIcon); // Set the green icon for active airport
                marker.bindPopup(`You are here: <b>${airport.name}</b>`);
                marker.openPopup();
            } else {
                marker.setIcon(blueIcon); // Set the blue icon for other airports
                const popupContent = document.createElement('div');
                const h4 = document.createElement('h4');
                h4.innerHTML = airport.name;
                popupContent.append(h4);
                const goButton = document.createElement('button');
                goButton.classList.add('button');
                goButton.innerHTML = 'Fly here';
                popupContent.append(goButton);
                const p = document.createElement('p');
                p.innerHTML = `Distance ${airport.distance}km`;
                popupContent.append(p);

                // Add event listener for the "Fly here" button
                goButton.addEventListener('click', function () {
                    const flyUrl = `${apiUrl}flyto?player=${gameData.player}&dest=${airport.icao}`;
                    flyToAirport(flyUrl);
                });

                marker.bindPopup(popupContent);
            }
        }

        // Fit map bounds to markers
        if (airportMarkers.getBounds().isValid()) {
            map.fitBounds(airportMarkers.getBounds(), { padding: [20, 20] });
        }
    } catch (error) {
        console.error('Error setting up the game:', error);
    }
}

// Function to handle flying to a selected airport
async function flyToAirport(flyUrl) {
    try {
        const gameData = await getData(flyUrl);
        console.log('Updated game data:', gameData);

        // Update game status UI
        updateGameStatus(gameData);

        // Refresh game setup with new data
        gameSetup(`${apiUrl}game?player=${gameData.player}`);
    } catch (error) {
        console.error('Error flying to airport:', error);
    }
}

// Start the game setup when the page loads (with default player and location)
gameSetup(`${apiUrl}newgame?player=Player1&loc=${startLoc}`);
