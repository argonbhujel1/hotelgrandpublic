
/* Get Direction — Google Maps (no Leaflet) */
(function () {
  var HOTEL = { lat: 26.6643, lng: 87.6335, name: "Hotel Grand, Urlabari" };

  function openGoogleDir(originLat, originLng) {
    var dest = HOTEL.lat + "," + HOTEL.lng;
    var url;
    if (originLat != null && originLng != null) {
      url = "https://www.google.com/maps/dir/?api=1&origin=" + originLat + "," + originLng +
            "&destination=" + dest + "&travelmode=driving";
    } else {
      url = "https://www.google.com/maps/dir/?api=1&destination=" + dest + "&travelmode=driving";
    }
    window.open(url, "_blank", "noopener");
  }

  function openStreetView() {
    window.open(
      "https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=" + HOTEL.lat + "," + HOTEL.lng,
      "_blank",
      "noopener"
    );
  }

  function bind() {
    document.querySelectorAll("#btn-get-direction-cta, #btn-get-direction-page, [data-get-direction]").forEach(function (btn) {
      btn.addEventListener("click", function (e) {
        e.preventDefault();
        if (!navigator.geolocation) {
          openGoogleDir(null, null);
          return;
        }
        navigator.geolocation.getCurrentPosition(
          function (pos) {
            openGoogleDir(pos.coords.latitude, pos.coords.longitude);
          },
          function () {
            openGoogleDir(null, null);
          },
          { enableHighAccuracy: true, timeout: 10000 }
        );
      });
    });
    document.querySelectorAll("[data-street-view]").forEach(function (btn) {
      btn.addEventListener("click", function (e) {
        e.preventDefault();
        openStreetView();
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }
})();
