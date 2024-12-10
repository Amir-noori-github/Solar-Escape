'use strict';

let playerName; // Pelaajan nimi
const apiUrl = 'http://127.0.0.1:3000/'; // Backendin API-osoite

// Kartan alustus
let map; // Kartta muuttuja
const airportMarkers = L.featureGroup(); // Lentokenttien markkerien ryhmä

// Kartan alustaminen vasta DOM:n latauksen jälkeen
document.addEventListener('DOMContentLoaded', function () {
    map = L.map('map').setView([60, 24], 7); // Keskitetään Suomi
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
    }).addTo(map);
    airportMarkers.addTo(map); // Lisätään markkerit kartalle

    setupModalHandler(); // Modalin käsittely
});

// Modalin käsittely ja pelaajan nimen syöttö
function setupModalHandler() {
    const form = document.querySelector('#player-form');
    const modal = document.querySelector('#player-modal');
    const backdrop = document.querySelector('.modal-backdrop');

    if (form) {
        form.addEventListener('submit', function (evt) {
            evt.preventDefault(); // Estetään lomakkeen oletustoiminto
            const input = document.querySelector('#player-input').value;

            if (input.trim() !== '') {
                playerName = input; // Asetetaan pelaajan nimi
                document.querySelector('#player-name').textContent = playerName; // Päivitetään UI

                // Suljetaan modal
                if (modal) {
                    modal.style.display = 'none';
                    modal.classList.remove('show');
                }
                if (backdrop) {
                    backdrop.style.display = 'none';
                    backdrop.classList.remove('show');
                }

                aloitaPeli(); // Aloitetaan peli
            } else {
                alert('Anna kelvollinen nimi ennen pelin aloitusta.');
            }
        });
    }
}

// Päivittää pelaajan tiedot käyttöliittymässä
function paivitaPelitilanne(tila) {
    document.querySelector('#current-location').textContent = tila.current_location || 'Tuntematon'; // Nykyinen sijainti
    document.querySelector('#bunkers_found').textContent = `${totalBunkers - tila.goal_airports.length}/${totalBunkers}`; // Päivitä suojapaikkalaskuri

    // Pyöristetään jäljellä oleva etäisyys ja aika 0 desimaaliin
    const pyoristettuEtaisyys = tila.remaining_distance ? parseFloat(tila.remaining_distance).toFixed(0) : '0';
    const pyoristettuAika = tila.remaining_time ? (tila.remaining_time / 60).toFixed(2) : '0';

    // Päivitetään käyttöliittymän arvot
    document.querySelector('#player-distance').textContent = `${pyoristettuEtaisyys} km`; // Jäljellä oleva etäisyys
    document.querySelector('#player-time').textContent = `${pyoristettuAika} h`; // Jäljellä oleva aika tunneissa
}

// Pelin alustus ja API-kutsu
async function aloitaPeli() {
    try {
        const vastaus = await fetch(`${apiUrl}newgame?player=${playerName}&loc=EFHK`); // Haetaan uusi peli
        const pelidata = await vastaus.json(); // Muutetaan vastaus JSON-muotoon
        asetaKartta(pelidata);
    } catch (virhe) {
        console.error('Virhe pelin alustuksessa:', virhe);
        alert('Pelin aloitus epäonnistui. Yritä uudelleen.');
    }
}

// Lentokenttien markkerien luonti ja pelin UI:n asettaminen
async function asetaKartta(pelidata) {
    console.log("Pelidata saapui karttaan:", pelidata); // Debug: Tulostetaan pelidata

    // Tyhjennetään vanhat markkerit
    airportMarkers.clearLayers();
    paivitaPelitilanne(pelidata); // Päivitetään pelaajan tilanne käyttöliittymään

    if (!pelidata.locations || pelidata.locations.length === 0) {
        console.error("Ei lentokenttiä näytettäväksi!");
        return; // Ei jatketa, jos ei ole lentokenttiä
    }

    // Lisätään markkerit kartalle
    pelidata.locations.forEach(lentokentta => {
        if (lentokentta.latitude && lentokentta.longitude) {
            // Tarkistetaan, onko tämä pelaajan nykyinen sijainti
            const isCurrentLocation = lentokentta.name === pelidata.current_location;

            const marker = L.circleMarker([lentokentta.latitude, lentokentta.longitude], {
                color: isCurrentLocation ? 'green' : 'blue', // Vihreä nykyiselle sijainnille, sininen muille
                radius: isCurrentLocation ? 10 : 6, // Suurempi koko nykyiselle sijainnille
                fillOpacity: 0.8
            });

            marker.addTo(airportMarkers); // Lisätään markkeri ryhmään

            // Popup-ikkuna ja "Fly here" -painike
            marker.bindPopup(`
                <b>${lentokentta.name}</b><br>
                Distance: ${lentokentta.distance ? lentokentta.distance.toFixed(2) : "N/A"} km<br>
                ${!isCurrentLocation ? `<button onclick="lennäLentokentälle('${lentokentta.id}')">Fly here</button>` : ""}
            `);
        } else {
            console.warn("Lentokentältä puuttuu koordinaatit:", lentokentta);
        }
    });

    // Sovitetaan kartta markkereiden ympärille, jos niitä on
    if (airportMarkers.getBounds().isValid()) {
        map.fitBounds(airportMarkers.getBounds());
    } else {
        console.error("Markkereita ei lisätty kartalle!");
    }
}

// Modalin avaamisen apufunktio
function avaaModal() {
    const modal = document.querySelector('#player-modal');
    const backdrop = document.querySelector('.modal-backdrop');
    if (modal) {
        modal.style.display = 'block';
        modal.classList.add('show');
    }
    if (backdrop) {
        backdrop.style.display = 'block';
        backdrop.classList.add('show');
    }
}
// Suojapaikkalaskurin muuttujat
let totalBunkers = 5; // Kokonaismäärä suojapaikkoja
let foundBunkers = 0; // Aluksi löydettyjä suojapaikkoja

// Päivittää suojapaikkalaskurin käyttöliittymässä
function paivitaSuojapaikkaLaskuri() {
    const bunkersElement = document.querySelector('#bunkers_found');
    if (bunkersElement) {
        bunkersElement.textContent = `${foundBunkers}/${totalBunkers}`;
    }
}

// Lentotoiminnon API-kutsu (päivitetty laskurilla)
async function lennäLentokentälle(kohdeId) {
    try {
        const vastaus = await fetch(`${apiUrl}flyto?dest=${kohdeId}`);
        const pelidata = await vastaus.json();

        if (pelidata.status === 'goal') {
            foundBunkers++; // Lisätään löydetty suojapaikka
            paivitaSuojapaikkaLaskuri(); // Päivitetään laskuri käyttöliittymässä
            alert('You found a protected area! Keep going!');
        } else if (pelidata.status === 'victory') {
            alert('You found all protected areas! Game Over. Congratulations!');
            avaaModal(); // Peli alkaa alusta
        } else if (pelidata.status === 'restart') {
            alert(pelidata.message); // Näytetään käyttäjälle viesti
            avaaModal(); // Näytetään modal uudelleen
        }

        asetaKartta(pelidata); // Kartta ja UI päivitetään
    } catch (virhe) {
        console.error('Virhe lentämisessä:', virhe);
        alert('Lentotoiminto epäonnistui. Yritä uudelleen.');
    }
}

// Pelin alustus (päivitetty laskurin nollaus)
async function aloitaPeli() {
    try {
        foundBunkers = 0; // Nollataan löydetyt suojapaikat pelin alkaessa
        paivitaSuojapaikkaLaskuri(); // Päivitetään käyttöliittymä
        const vastaus = await fetch(`${apiUrl}newgame?player=${playerName}&loc=EFHK`); // Haetaan uusi peli
        const pelidata = await vastaus.json(); // Muutetaan vastaus JSON-muotoon
        asetaKartta(pelidata);
    } catch (virhe) {
        console.error('Virhe pelin alustuksessa:', virhe);
        alert('Pelin aloitus epäonnistui. Yritä uudelleen.');
    }
}
