(function () {
  "use strict";

  var HOTEL = { lat: 26.6643, lng: 87.6335, name: "Hotel Grand" };
  var modal = document.getElementById("direction-modal");
  if (!modal) return;

  var mapEl = document.getElementById("direction-map");
  var summaryEl = document.getElementById("route-summary");
  var manualEl = document.getElementById("manual-location");
  var map = null;
  var userMarker = null;
  var hotelMarker = null;
  var routeLayer = null;
  var currentMode = "driving";
  var lastUserPos = null;

  function openModal() {
    modal.removeAttribute("hidden");
    document.body.style.overflow = "hidden";
    setTimeout(initMap, 50);
  }

  function closeModal() {
    modal.setAttribute("hidden", "");
    document.body.style.overflow = "";
  }

  document.querySelectorAll(
    "#btn-get-direction, #btn-get-direction-mobile, #btn-get-direction-hero, #btn-get-direction-cta, #btn-get-direction-page, #btn-get-direction-contact"
  ).forEach(function (btn) {
    if (btn) btn.addEventListener("click", openModal);
  });

  modal.querySelectorAll("[data-close-modal]").forEach(function (el) {
    el.addEventListener("click", closeModal);
  });

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && !modal.hasAttribute("hidden")) closeModal();
  });

  function initMap() {
    if (typeof L === "undefined") {
      summaryEl.innerHTML = '<p class="route-hint">Map library failed to load.</p>';
      return;
    }
    if (!map) {
      map = L.map(mapEl).setView([HOTEL.lat, HOTEL.lng], 13);
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "&copy; OpenStreetMap",
        maxZoom: 19,
      }).addTo(map);
      hotelMarker = L.marker([HOTEL.lat, HOTEL.lng])
        .addTo(map)
        .bindPopup(HOTEL.name);
    }
    setTimeout(function () {
      map.invalidateSize();
    }, 100);
    requestLocation();
  }

  function requestLocation() {
    if (!navigator.geolocation) {
      showFallback("Your browser does not support geolocation.");
      return;
    }
    summaryEl.innerHTML = '<p class="route-hint">Requesting your location…</p>';
    navigator.geolocation.getCurrentPosition(
      function (pos) {
        lastUserPos = { lat: pos.coords.latitude, lng: pos.coords.longitude };
        if (userMarker) map.removeLayer(userMarker);
        userMarker = L.marker([lastUserPos.lat, lastUserPos.lng])
          .addTo(map)
          .bindPopup("Your location");
        fetchRoute(lastUserPos.lat, lastUserPos.lng, currentMode);
      },
      function () {
        showFallback("We need your location to calculate the route.");
      },
      { enableHighAccuracy: true, timeout: 12000, maximumAge: 60000 }
    );
  }

  function showFallback(msg) {
    summaryEl.innerHTML = '<p class="route-hint">' + msg + "</p>";
    if (manualEl) manualEl.removeAttribute("hidden");
  }

  function fetchRoute(lat, lng, mode) {
    summaryEl.innerHTML = '<p class="route-hint">Calculating route…</p>';
    fetch("/api/route", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ lat: lat, lng: lng, mode: mode }),
    })
      .then(function (r) {
        return r.json().then(function (data) {
          if (!r.ok) throw new Error(data.error || "Route failed");
          return data;
        });
      })
      .then(function (data) {
        if (routeLayer) map.removeLayer(routeLayer);
        routeLayer = L.geoJSON(data.geometry, {
          style: { color: "#c9a227", weight: 5, opacity: 0.9 },
        }).addTo(map);
        map.fitBounds(routeLayer.getBounds(), { padding: [40, 40] });
        summaryEl.innerHTML =
          "<p><strong>Your Location</strong> → <strong>Hotel Grand</strong></p>" +
          "<p>" +
          data.distance_km +
          " km · ~" +
          data.duration_min +
          " min (" +
          (data.mode === "walking" ? "walking" : "driving") +
          ")</p>";
      })
      .catch(function (err) {
        summaryEl.innerHTML =
          '<p class="route-hint">' + (err.message || "Route calculation failed.") + "</p>";
        if (manualEl) manualEl.removeAttribute("hidden");
      });
  }

  // Mode buttons
  document.querySelectorAll(".mode-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      document.querySelectorAll(".mode-btn").forEach(function (b) {
        b.classList.remove("active");
      });
      btn.classList.add("active");
      currentMode = btn.getAttribute("data-mode") || "driving";
      if (lastUserPos) {
        fetchRoute(lastUserPos.lat, lastUserPos.lng, currentMode);
      }
    });
  });

  var enableBtn = document.getElementById("btn-enable-location");
  if (enableBtn) enableBtn.addEventListener("click", requestLocation);

  var recenterBtn = document.getElementById("btn-recenter");
  if (recenterBtn) {
    recenterBtn.addEventListener("click", function () {
      if (routeLayer) {
        map.fitBounds(routeLayer.getBounds(), { padding: [40, 40] });
      } else if (lastUserPos) {
        map.setView([lastUserPos.lat, lastUserPos.lng], 14);
      } else {
        map.setView([HOTEL.lat, HOTEL.lng], 14);
      }
    });
  }

  // Manual start via Nominatim geocode (no key)
  var searchBtn = document.getElementById("btn-search-start");
  var searchInput = document.getElementById("start-search");
  if (searchBtn && searchInput) {
    searchBtn.addEventListener("click", function () {
      var q = searchInput.value.trim();
      if (!q) return;
      summaryEl.innerHTML = '<p class="route-hint">Looking up location…</p>';
      fetch(
        "https://nominatim.openstreetmap.org/search?format=json&q=" +
          encodeURIComponent(q + ", Nepal") +
          "&limit=1",
        { headers: { Accept: "application/json" } }
      )
        .then(function (r) {
          return r.json();
        })
        .then(function (results) {
          if (!results || !results.length) {
            summaryEl.innerHTML =
              '<p class="route-hint">Place not found. Try a different name.</p>';
            return;
          }
          lastUserPos = {
            lat: parseFloat(results[0].lat),
            lng: parseFloat(results[0].lon),
          };
          if (userMarker) map.removeLayer(userMarker);
          userMarker = L.marker([lastUserPos.lat, lastUserPos.lng])
            .addTo(map)
            .bindPopup(results[0].display_name);
          fetchRoute(lastUserPos.lat, lastUserPos.lng, currentMode);
        })
        .catch(function () {
          summaryEl.innerHTML =
            '<p class="route-hint">Search failed. Please try again.</p>';
        });
    });
  }
})();
