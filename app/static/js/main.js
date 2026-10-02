(function () {
  "use strict";

  // Mobile nav
  var toggle = document.getElementById("nav-toggle");
  var mobileNav = document.getElementById("mobile-nav");
  if (toggle && mobileNav) {
    toggle.addEventListener("click", function () {
      var open = toggle.getAttribute("aria-expanded") === "true";
      toggle.setAttribute("aria-expanded", open ? "false" : "true");
      if (open) {
        mobileNav.setAttribute("hidden", "");
      } else {
        mobileNav.removeAttribute("hidden");
      }
    });
    mobileNav.querySelectorAll("a").forEach(function (link) {
      link.addEventListener("click", function () {
        toggle.setAttribute("aria-expanded", "false");
        mobileNav.setAttribute("hidden", "");
      });
    });
  }

  // Header scroll shadow
  var header = document.getElementById("site-header");
  if (header) {
    window.addEventListener(
      "scroll",
      function () {
        if (window.scrollY > 20) {
          header.style.boxShadow = "0 4px 20px rgba(10,22,40,0.12)";
        } else {
          header.style.boxShadow = "none";
        }
      },
      { passive: true }
    );
  }

  // Auto-hide flashes
  setTimeout(function () {
    document.querySelectorAll(".flash").forEach(function (el) {
      el.style.opacity = "0";
      el.style.transition = "opacity 0.4s";
      setTimeout(function () {
        el.remove();
      }, 400);
    });
  }, 5000);

  // Scroll-triggered entrance animations
  var animEls = document.querySelectorAll(".animate-in");
  if (animEls.length && "IntersectionObserver" in window) {
    var io = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            io.unobserve(entry.target);
          }
        });
      },
      { rootMargin: "0px 0px -40px 0px", threshold: 0.08 }
    );
    animEls.forEach(function (el) {
      io.observe(el);
    });
  } else {
    animEls.forEach(function (el) {
      el.classList.add("is-visible");
    });
  }
})();
