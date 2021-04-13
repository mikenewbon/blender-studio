/* global $:false */

(function navigation() {
  function navDrawerToggle() {
    document.querySelector('body').classList.toggle('nav-drawer-open');
  }

  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.navdrawertoggle').forEach((i) => {
      i.addEventListener('click', () => {
        navDrawerToggle();
      });
    });
  });

  $(() => {
    $('[data-toggle="tooltip"]').tooltip();
  });
})();

document.addEventListener('DOMContentLoaded', () => {
  // adds active class to any nav item with a href that matches the current url
  // eslint-disable-next-line no-restricted-globals
  const url = location.pathname;
  document
    .querySelectorAll(
      `a.list-group-item[href="${url}"], a.drawer-nav-section-link[href="${url}"], a.drawer-nav-dropdown[href="${url}"]`
    )
    .forEach((link) => {
      link.classList.add('active');
    });

  // adds active class to main-nav item if it matches the start of the current url
  document.querySelectorAll('.navbar-main-nav a.btn-nav').forEach((link) => {
    if (url.startsWith(link.pathname)) {
      link.classList.add('active');
    }
  });
});

// Allow side-scroll drag on desktop
function sideScrollNavigation() {
  const slider = document.querySelector('.side-scroll');
  let isDown = false;
  let startX;
  let scrollLeft;

  if (slider) {
    slider.addEventListener('mousedown', (e) => {
      isDown = true;
      slider.classList.add('active');
      startX = e.pageX - slider.offsetLeft;
      scrollLeft = slider.scrollLeft;
    });
    slider.addEventListener('mouseleave', () => {
      isDown = false;
      slider.classList.remove('active');
    });
    slider.addEventListener('mouseup', () => {
      isDown = false;
      slider.classList.remove('active');
    });
    slider.addEventListener('mousemove', (e) => {
      if (!isDown) return;
      e.preventDefault();
      const x = e.pageX - slider.offsetLeft;
      const walk = x - startX;
      slider.scrollLeft = scrollLeft - walk;
    });
  }
}

window.addEventListener('DOMContentLoaded', () => {
  sideScrollNavigation();
});

// Progress Bar
function animateProgress() {
  const globalProgress = document.querySelector('.global-progress');
  const progressBar = document.querySelector('.global-progress .progress-bar');
  let currentProgress = 0;
  let step = 0.5; // the smaller this is the slower the progress bar

  globalProgress.style.opacity = "1";

  const interval = setInterval(() => {
    currentProgress += step;
    const progress = Math.round((Math.atan(currentProgress) / (Math.PI / 2)) * 100 * 1000) / 1000;
    progressBar.style.width = `${progress}%`;
    progressBar.setAttribute('aria-valuenow', progress);

    if (progress >= 100) {
      clearInterval(interval);
    } else if (progress >= 70) {
      step = 0.1;
    }
  }, 100);
}

window.addEventListener('beforeunload', () => {
  animateProgress();
});

// Function is also used in modals and download buttons onClick.
function resetProgress() {
  const globalProgress = document.querySelector('.global-progress');
  const progressBar = document.querySelector('.global-progress .progress-bar');

  globalProgress.style.opacity = '0';
  progressBar.style.width = '0%';
  progressBar.setAttribute('aria-valuenow', 0);
  clearInterval();
}
