'use strict';
/* 1. show map using Leaflet library. (L comes from the Leaflet library) */

const map = L.map('map', {tap: false});
L.tileLayer('https://{s}.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', {
  maxZoom: 20,
  subdomains: ['mt0', 'mt1', 'mt2', 'mt3'],
}).addTo(map);
map.setView([60, 24], 7);

// global variables
const apiUrl = 'http://127.0.0.1:5000/';
const startLoc = 'EFHK';
const globalGoals = [];
const airportMarkers = L.featureGroup().addTo(map);

// icons
const blueIcon = L.divIcon({ className: 'blue-icon' });
const greenIcon = L.divIcon({ className: 'green-icon' });

// form for player name
document.querySelector('#player-form').addEventListener('submit', function (evt) {
    evt.preventDefault(); // Estää lomakkeen oletustoiminnan (uudelleenlatauksen)

    const playerName = document.querySelector('#player-input').value; // Hakee syötetyn nimen

    if (playerName.trim() !== '') { // Tarkistaa, että nimi ei ole tyhjä
        // Piilota modal ja tausta
        document.querySelector('#player-modal').classList.remove('show');
        document.querySelector('.modal-backdrop').classList.remove('show');

        // Aloita peli tai suorita haluttu toiminto
        console.log(`Player name: ${playerName}`);
        gameSetup(`${apiUrl}newgame?player=${playerName}&loc=${startLoc}`);
    } else {
        alert('Please enter a valid name.'); // Näytä virheilmoitus, jos nimi on tyhjä
    }
});

// function to fetch data from API
async function getData(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error('Invalid server input!');
  const data = await response.json();
  return data;
}

// function to update location, kilometres, time



// function to check if any goals have been reached



// function to check if game is over



// function to set up game
// this is the main function that creates the game and calls the other functions
async  function gameSetup () {
    try {
        const gameData = await getData('testdata/newgame.json');
        console.log(gameData);
        for (let airport of gameData.location) {
            const marker = L.marker([airport.latitude, airport.longitude]).addTo(map);
            if (airport.active) {
                marker.bindPopup(`You are here: <b>${airport.name}</b>`);
                marker.openPopup();
                marker.setIcon(greenIcon);
            } else {
                marker.setIcon(blueIcon);
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
                marker.bindPopup(popupContent);
            }
        }
    } catch (error) {
        console.log();
    }
}
gameSetup();




