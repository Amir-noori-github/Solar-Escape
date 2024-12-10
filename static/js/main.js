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

    // Pyöristetään jäljellä oleva etäisyys ja aika 0 desimaaliin
    const pyoristettuEtaisyys = tila.remaining_distance ? parseFloat(tila.remaining_distance).toFixed(0) : '0';
    const pyoristettuAika = tila.remaining_time ? (tila.remaining_time / 60).toFixed(2) : '0';

    // Päivitetään käyttöliittymän arvot
    document.querySelector('#player-distance').textContent = `${pyoristettuEtaisyys} km`; // Jäljellä oleva etäisyys
    document.querySelector('#player-time').textContent = `${pyoristettuAika} h`; // Jäljellä oleva aika tunneissa

    // Tarkista, onko aika tai etäisyys loppunut
    if (tila.remaining_time <= 0 || tila.remaining_distance <= 0) {
        alert('Aika tai etäisyys on loppunut! Peli käynnistyy uudelleen.');
        avaaModal(); // Näytä modal uudelleen pelin aloitusta varten
    }
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
    airportMarkers.clearLayers(); // Tyhjennetään vanhat markkerit
    paivitaPelitilanne(pelidata); // Päivitetään pelaajan tilanne UI:hin

    // Lisätään lentokentät kartalle
    pelidata.locations.forEach(lentokentta => {
        const marker = L.marker([lentokentta.latitude, lentokentta.longitude]); // Luodaan markkeri
        marker.addTo(airportMarkers); // Lisätään markkeri ryhmään

        // Popup-ikkuna ja "Fly here" -painike
        marker.bindPopup(`
            <b>${lentokentta.name}</b><br>
            Etäisyys: ${lentokentta.distance.toFixed(2)} km<br>
            <button onclick="lennäLentokentälle('${lentokentta.id}')">Lennä tänne</button>
        `);
    });

    if (airportMarkers.getBounds().isValid()) {
        map.fitBounds(airportMarkers.getBounds()); // Sovitetaan kartta markkereiden ympärille
    }
}

// Lentotoiminnon API-kutsu
async function lennäLentokentälle(kohdeId) {
    try {
        const vastaus = await fetch(`${apiUrl}flyto?dest=${kohdeId}`);
        const pelidata = await vastaus.json();

        if (pelidata.status === 'goal') {
            alert('Saavutit suojatun alueen! Jatka etsimistä.');
        } else if (pelidata.status === 'victory') {
            alert('Onnittelut! Löysit kaikki suojatut alueet.');
            avaaModal(); // Peli alkaa alusta
        } else if (pelidata.status === 'restart') {
            alert(pelidata.message); // Kullanıcıya mesaj göster
            avaaModal(); // Modal yeniden açılır
        }

        asetaKartta(pelidata); // Kartta ve UI päivitetään
    } catch (virhe) {
        console.error('Virhe lentämisessä:', virhe);
        alert('Lentotoiminto epäonnistui. Yritä uudelleen.');
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
            alert('Saavutit suojatun alueen! Jatka etsimistä.');
        } else if (pelidata.status === 'victory') {
            alert('Onnittelut! Löysit kaikki suojatut alueet.');
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
