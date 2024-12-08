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
  evt.preventDefault();
  const playerName = document.querySelector('#player-input').value;
  document.querySelector('#player-modal').classList.add('hide');
  gameSetup(`${apiUrl}newgame?player=${playerName}&loc=${startLoc}`);
});

// function to fetch data from API
async function getData(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error('Invalid server input!');
  const data = await response.json();
  return data;
}
// function to update game status
function updateStatus(status) {
     document.querySelector('#player-name').innerHTML = `Player: ${status.name}`;
     document.querySelector('#current-location').innerHTML = status.locations.find(loc => loc.active).name;
     document.querySelector('#player-distance').innerHTML = `${status.remaining_distance} km`;
     document.querySelector('#player-time').innerHTML = `${status.remaining_time} min`;
}


// function to show weather at selected airport

// function to check if any goals have been reached

// function to update goal data and goal table in UI
// function to check if game is over

// function to set up game
// this is the main function that creates the game and calls the other functions
async  function gameSetup (url) {
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

// event listener to hide goal splash



