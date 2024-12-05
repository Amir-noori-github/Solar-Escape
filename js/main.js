'use strict';
/* 1. Näytetään kartta Leaflet-kirjaston avulla */
const map = L.map('map', { tap: false });
L.tileLayer('https://{s}.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', {
  maxZoom: 20,
  subdomains: ['mt0', 'mt1', 'mt2', 'mt3'],
}).addTo(map);
map.setView([60, 24], 7);

// Globaalit muuttujat
const apiUrl = 'http://127.0.0.1:5000/';
const startLoc = 'EFHK';
const globalGoals = [];
const airportMarkers = L.featureGroup().addTo(map);

// Ikonit
const blueIcon = L.divIcon({ className: 'blue-icon' });
const greenIcon = L.divIcon({ className: 'green-icon' });

// Pelaajan nimen lomake
document.querySelector('#player-form').addEventListener('submit', function (evt) {
  evt.preventDefault();
  const playerName = document.querySelector('#player-input').value.trim();
  if (playerName) {
    document.querySelector('#player-modal').classList.add('hide');
    gameSetup(`${apiUrl}newgame?player=${playerName}&loc=${startLoc}`);
  } else {
    alert('Please enter a player name!');
  }
});

// Datahaun funktio
async function getData(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error('Invalid server response!');
  }
  return await response.json();
}

// Tavoitteiden päivittäminen
function updateGoals(goals) {
  document.querySelector('#goals').innerHTML = '';
  for (const goal of goals) {
    const li = document.createElement('li');
    const figure = document.createElement('figure');
    const img = document.createElement('img');
    const figcaption = document.createElement('figcaption');
    img.src = goal.icon;
    img.alt = `goal name: ${goal.name}`;
    figcaption.innerHTML = goal.description;
    figure.append(img, figcaption);
    li.append(figure);
    if (goal.reached) {
      li.classList.add('done');
      if (!globalGoals.includes(goal.goalid)) {
        globalGoals.push(goal.goalid);
      }
    }
    document.querySelector('#goals').append(li);
  }
}

// Pelin alustus
async function gameSetup(url) {
  try {
    document.querySelector('.goal').classList.add('hide');
    airportMarkers.clearLayers();

    const gameData = await getData(url);
    console.log(gameData);

    // Päivitä pelaajan nimi
    document.querySelector('#player-name').textContent = `Player: ${gameData.status.name}`;

    // Käsitellään lentokentät
    for (const airport of gameData.location) {
      const marker = L.marker([airport.latitude, airport.longitude]).addTo(map);
      airportMarkers.addLayer(marker);

      if (airport.active) {
        // Pelaajan nykyinen sijainti
        map.flyTo([airport.latitude, airport.longitude], 10);
        marker.bindPopup(`You are here: <b>${airport.name}</b>`);
        marker.openPopup();
        marker.setIcon(greenIcon);
      } else {
        // Muu lentokenttä
        marker.setIcon(blueIcon);

        // Luo popup-sisältö
        const popupContent = document.createElement('div');
        const h4 = document.createElement('h4');
        h4.textContent = airport.name;
        popupContent.append(h4);

        const goButton = document.createElement('button');
        goButton.classList.add('button');
        goButton.textContent = 'Fly here';
        popupContent.append(goButton);

        const p = document.createElement('p');
        p.textContent = `Distance: ${airport.distance} km`;
        popupContent.append(p);

        marker.bindPopup(popupContent);

        // "Fly here" -napin toiminnallisuus
        goButton.addEventListener('click', function () {
          gameSetup(`${apiUrl}flyto?game=${gameData.status.id}&dest=${airport.ident}`);
        });
      }
    }

    // Päivitä tavoitteet
    updateGoals(gameData.goals);
  } catch (error) {
    console.error('Error during game setup:', error);
  }
}

// Käynnistä peli oletusasetuksilla
gameSetup(`${apiUrl}newgame?player=default&loc=${startLoc}`);
