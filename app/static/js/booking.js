(function () {
  "use strict";

  var form = document.getElementById("booking-form");
  if (!form) return;

  var roomSelect = document.getElementById("room_type_id");
  var roomIdSelect = document.getElementById("room_id");
  var checkIn = document.getElementById("check_in");
  var checkOut = document.getElementById("check_out");
  var quoteEl = document.getElementById("quote-content");
  var hint = document.getElementById("room-pick-hint");

  var today = new Date();
  var todayStr = today.toISOString().slice(0, 10);
  if (checkIn) {
    checkIn.min = todayStr;
    checkIn.addEventListener("change", function () {
      if (checkOut) {
        var d = new Date(checkIn.value);
        d.setDate(d.getDate() + 1);
        checkOut.min = d.toISOString().slice(0, 10);
        if (checkOut.value && checkOut.value <= checkIn.value) {
          checkOut.value = checkOut.min;
        }
      }
      updateQuote();
      loadRooms();
    });
  }
  if (checkOut) {
    checkOut.addEventListener("change", function () {
      updateQuote();
      loadRooms();
    });
  }
  if (roomSelect) {
    roomSelect.addEventListener("change", function () {
      updateQuote();
      loadRooms();
    });
  }

  function loadRooms() {
    if (!roomIdSelect) return;
    if (!roomSelect.value || !checkIn.value || !checkOut.value) {
      roomIdSelect.innerHTML = '<option value="">Select class and dates first</option>';
      if (hint) hint.textContent = "Choose class and dates to load available rooms.";
      return;
    }
    if (checkOut.value <= checkIn.value) {
      roomIdSelect.innerHTML = '<option value="">Invalid dates</option>';
      return;
    }
    roomIdSelect.innerHTML = '<option value="">Loading…</option>';
    fetch("/booking/available-rooms", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        room_type_id: parseInt(roomSelect.value, 10),
        check_in: checkIn.value,
        check_out: checkOut.value,
      }),
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        var rooms = data.rooms || [];
        if (!rooms.length) {
          roomIdSelect.innerHTML = '<option value="">No rooms available</option>';
          if (hint) hint.textContent = "Try different dates or another class.";
          return;
        }
        roomIdSelect.innerHTML = '<option value="">Select room number</option>';
        rooms.forEach(function (rm) {
          var opt = document.createElement("option");
          opt.value = rm.id;
          opt.textContent =
            "Room " + rm.room_number + (rm.floor ? " (Floor " + rm.floor + ")" : "");
          roomIdSelect.appendChild(opt);
        });
        if (hint) hint.textContent = rooms.length + " room(s) available.";
      })
      .catch(function () {
        roomIdSelect.innerHTML = '<option value="">Could not load rooms</option>';
      });
  }

  function updateQuote() {
    if (!quoteEl) return;
    if (!roomSelect.value || !checkIn.value || !checkOut.value) {
      quoteEl.innerHTML = '<p class="muted">Select room class and dates to see the total.</p>';
      return;
    }
    if (checkOut.value <= checkIn.value) {
      quoteEl.innerHTML = '<p class="muted">Check-out must be after check-in.</p>';
      return;
    }
    quoteEl.innerHTML = '<p class="muted">Calculating…</p>';
    fetch("/booking/quote", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        room_type_id: parseInt(roomSelect.value, 10),
        check_in: checkIn.value,
        check_out: checkOut.value,
      }),
    })
      .then(function (r) {
        return r.json().then(function (data) {
          if (!r.ok) throw new Error(data.error || "Failed");
          return data;
        });
      })
      .then(function (data) {
        var html = "";
        data.nights.forEach(function (n) {
          html +=
            '<div class="night-row"><span>' +
            n.date +
            " · " +
            n.label +
            '</span><span>Rs. ' +
            Math.round(n.rate).toLocaleString() +
            "</span></div>";
        });
        html +=
          '<div class="total-row"><span>Total (' +
          data.total_nights +
          " nights)</span><span>Rs. " +
          Math.round(data.total_amount).toLocaleString() +
          "</span></div>";
        quoteEl.innerHTML = html;
      })
      .catch(function (err) {
        quoteEl.innerHTML =
          '<p class="muted">' + (err.message || "Unable to calculate price") + "</p>";
      });
  }
})();
