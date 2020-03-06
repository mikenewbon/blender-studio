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
  });

  // TODO(sem): Why do we wrap this function in `$`? What does that do?
  $(() => {
    $('[data-toggle="tooltip"]').tooltip();
  });
})();
