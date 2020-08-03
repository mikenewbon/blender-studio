/* global $:false */

(function navigation() {
  function navDrawerToggle() {
    document.querySelector('body').classList.toggle('nav-drawer-open');
  }

  document.addEventListener('DOMContentLoaded', () => {

    document.querySelectorAll('.navdrawertoggle').forEach(i => {
      i.addEventListener('click', () => {
        navDrawerToggle();
      });
    });

    // Progress bar replaces this.
    // document.querySelectorAll('a.drawer-nav-dropdown:not([data-toggle]), .drawer-nav-section a').forEach(i => {
    //   i.addEventListener('click', () => {
    //     document.querySelector('.gallery-load-overlay').classList.add('show');
    //   })
    // });
  });

  // TODO(sem): Why do we wrap this function in `$`? What does that do?
  $(function () {
    $('[data-toggle="tooltip"]').tooltip()
  });
})();

document.addEventListener("DOMContentLoaded", function () {

  // adds active class to any nav item with a href that matches the current url
  document.querySelectorAll('a.list-group-item[href="' + location.pathname + '"], a.drawer-nav-section-link[href="' + location.pathname + '"], a.drawer-nav-dropdown[href="' + location.pathname + '"]').forEach((link) => {
    link.classList.add('active');
  })

  // adds active class to main-nav item if it matches the start of the current url
  document.querySelectorAll('.navbar-main-nav a.list-group-item').forEach((link) => {
    if (location.pathname.startsWith(link.pathname)) {
      link.classList.add('active');
    }
  });
});

// Allow side-scroll drag on desktop
const slider = document.querySelector(".side-scroll");
let isDown = false;
let startX;
let scrollLeft;

if (slider) {
  slider.addEventListener("mousedown", e => {
    isDown = true;
    slider.classList.add("active");
    startX = e.pageX - slider.offsetLeft;
    scrollLeft = slider.scrollLeft;
  });
  slider.addEventListener("mouseleave", () => {
    isDown = false;
    slider.classList.remove("active");
  });
  slider.addEventListener("mouseup", () => {
    isDown = false;
    slider.classList.remove("active");
  });
  slider.addEventListener("mousemove", e => {
    if (!isDown) return;
    e.preventDefault();
    const x = e.pageX - slider.offsetLeft;
    const walk = x - startX;
    slider.scrollLeft = scrollLeft - walk;
  });
}


//Progress Bar

window.addEventListener("beforeunload", function (event) {
  animateProgress();
});

function animateProgress() {
  const globalProgress = document.querySelector('.global-progress');
  const progressBar = document.querySelector('.global-progress .progress-bar');
  let current_progress = 0;
  let step = 0.5; // the smaller this is the slower the progress bar

  globalProgress.style.opacity = "1";

  interval = setInterval(function () {
    current_progress += step;
    progress = Math.round(Math.atan(current_progress) / (Math.PI / 2) * 100 * 1000) / 1000;
    progressBar.style.width = progress + "%";
    progressBar.setAttribute('aria-valuenow', progress);

    if (progress >= 100) {
      clearInterval(interval);
    } else if (progress >= 70) {
      step = 0.1
    }
  }, 100);
}

function resetProgress() {
  const globalProgress = document.querySelector('.global-progress');
  const progressBar = document.querySelector('.global-progress .progress-bar');

  globalProgress.style.opacity = "0";
  progressBar.style.width = "0%";
  progressBar.setAttribute('aria-valuenow', 0);
  clearInterval(interval);
}
