'use strict';

// Alustetaan kartta käyttämällä Leaflet-kirjastoa
const map = L.map('map', { tap: false });
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '',
}).addTo(map);
map.setView([60, 24], 7); // Keskitetään Suomeen

// Globaalit muuttujat
const apiUrl = 'http://127.0.0.1:5000/';
const startLoc = 'EFHK'; // Oletuskenttä Helsinki-Vantaa
const airportMarkers = L.featureGroup().addTo(map); // Markkerien ryhmä

// Ikonit
const blueIcon = L.divIcon({ className: 'blue-icon' });
const greenIcon = L.divIcon({ className: 'green-icon' });

// Pelaajan nimen syöttölomakkeen toiminnallisuus
document.querySelector('#player-form').addEventListener('submit', function (evt) {
    evt.preventDefault();

    const playerName = document.querySelector('#player-input').value.trim();

    if (playerName) {
        // Suljetaan modaalinen ikkuna
        closeModal();

        // Aloitetaan peli
        const playerUrl = `${apiUrl}newgame?player=${encodeURIComponent(playerName)}&loc=${startLoc}`;
        gameSetup(playerUrl);
    } else {
        alert('Please enter a valid name.');
    }
});

// Sulkee modaalisen ikkunan
function closeModal() {
    const modal = document.querySelector('#player-modal');
    modal.classList.remove('show');
    modal.style.display = 'none';
    document.querySelector('.modal-backdrop')?.remove();
    document.body.classList.remove('modal-open');
}

// API-tiedon hakemiseen käytettävä funktio
async function getData(url) {
    try {
        const response = await fetch(url);
        if (!response.ok) throw new Error(`Error fetching data: ${response.status}`);
        return await response.json();
    } catch (error) {
        console.error('Error in getData:', error);
        alert('Failed to fetch data from server. Please try again.');
        throw error;
    }
}

// Päivittää pelaajan tilatiedot UI:ssa
function updateGameStatus(status) {
    const activeLocation = status.locations.find(loc => loc.active);
    document.querySelector('#current-location').textContent = activeLocation ? activeLocation.name : 'Unknown';
    document.querySelector('#player-distance').textContent = `${status.remaining_distance} km`;
    document.querySelector('#player-time').textContent = `${status.remaining_time} min`;
}

// Pelin alustus ja kartan asetukset
async function gameSetup(playerUrl) {
    try {
        airportMarkers.clearLayers(); // Tyhjennetään markkerit

        const gameData = await getData(playerUrl);
        console.log('Game data received:', gameData);

        updateGameStatus(gameData);

        for (let airport of gameData.locations) {
            const marker = L.marker([airport.latitude, airport.longitude]).addTo(airportMarkers);

            if (airport.active) {
                marker.setIcon(greenIcon);
                marker.bindPopup(`You are here: <b>${airport.name}</b>`).openPopup();
            } else {
                marker.setIcon(blueIcon);
                const popupContent = createAirportPopup(airport, gameData.player);
                marker.bindPopup(popupContent);
            }
        }

        // Sovitetaan kartta kaikkien markkerien ympärille
        if (airportMarkers.getBounds().isValid()) {
            map.fitBounds(airportMarkers.getBounds(), { padding: [20, 20] });
        }
    } catch (error) {
        console.error('Error setting up the game:', error);
    }
}

// Luo lentokentän popup-sisällön
function createAirportPopup(airport, playerName) {
    const popupContent = document.createElement('div');
    popupContent.classList.add('popup-content');

    const h4 = document.createElement('h4');
    h4.textContent = airport.name;
    popupContent.appendChild(h4);

    const p = document.createElement('p');
    p.textContent = `Distance: ${airport.distance} km`;
    popupContent.appendChild(p);

    const goButton = document.createElement('button');
    goButton.classList.add('fly-button');
    goButton.textContent = 'Fly here';
    goButton.addEventListener('click', function () {
        const flyUrl = `${apiUrl}flyto?player=${encodeURIComponent(playerName)}&dest=${encodeURIComponent(airport.icao)}`;
        flyToAirport(flyUrl);
    });
    popupContent.appendChild(goButton);

    return popupContent;
}

// Lentää valittuun lentokenttään
async function flyToAirport(flyUrl) {
    try {
        showLoading(true); // Näytetään latausanimaatio
        const gameData = await getData(flyUrl);
        console.log('Updated game data:', gameData);

        updateGameStatus(gameData);

        const gameUrl = `${apiUrl}game?player=${encodeURIComponent(gameData.player)}`;
        gameSetup(gameUrl);
    } catch (error) {
        console.error('Error flying to airport:', error);
        alert('Flight failed. Please try again.');
    } finally {
        showLoading(false); // Piilotetaan latausanimaatio
    }
}

// Näyttää tai piilottaa latausviestin
function showLoading(isLoading) {
    const loadingMessage = document.querySelector('#loading-message');
    loadingMessage.style.display = isLoading ? 'block' : 'none';
}

// Aloittaa pelin oletuksilla, kun sivu ladataan
gameSetup(`${apiUrl}newgame?player=Player1&loc=${startLoc}`);
