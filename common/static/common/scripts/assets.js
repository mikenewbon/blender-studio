/* global ajax:false */

window.asset = (function asset() {

  let baseModal = null;
  const baseModalId = '#file-modal';
  let zoomModal = null;
  const zoomModalId = '#file-zoom-modal';
  const assetParamName = 'asset';

  document.addEventListener('DOMContentLoaded', () => {
    baseModal = document.querySelector(baseModalId);
    zoomModal = document.querySelector(zoomModalId);
    addFileClickEvent();
    initalizeAssetURL();
  });

  window.addEventListener('popstate', (event) => {

    const fileElementSelector = document.querySelector('[data-asset-id="' + event.state + '"]');

    $(zoomModalId).modal('hide');

    if (event.state == "") {
      //The empty state occurs when the modal is closed, so it hides the modal.
      $(baseModalId).modal('hide');
    } else if (event.state) {
      loadingSpinner(baseModal);
      getModalHtml(fileElementSelector, baseModal, event);
      $(baseModalId).modal('show');
    }
  });

  // Using Jquery due to BootStrap events only being available here.
  // TODO(Mike): When Bootstrap 5 is added, switch to regular JS.
  $(document).ready(function () {
    $(baseModalId).each(function (i) {
      // Remove modal content on hide
      $(this).on('hidden.bs.modal', event => {
        $(this).modal('handleUpdate');
        $(this).empty();
        if (this.classList.contains('modal-asset')) {
          // Add loading spinner pre-emtively
          loadingSpinner(this);
        }
      });

      // Give modal focus on open
      $(this).on('shown.bs.modal', function () {
        $(this).trigger('focus')
      })

    })

    $(zoomModalId).on('hidden.bs.modal', event => {
      $(this).modal('handleUpdate');
    });

    // Left-Right keyboard events
    $(baseModalId).keydown(function (event) {
      const rightArrow = baseModalId + ' .modal-navigation.next';
      const leftArrow = baseModalId + ' .modal-navigation.previous';

      switch (event.key) {
        case "ArrowRight":
          $(rightArrow).trigger('click');
          break;
        case "ArrowLeft":
          $(leftArrow).trigger('click');
          break;
        case "Escape":
          $(baseModalId).modal('hide');
          removeURLParam(assetParamName);
          break;
      }
    });
  });

  // This fixes the issue of broken scrolling after opening the zoom modal by readding the modal-open class to the body, which gets removed on modal close.
  $(document).on('hidden.bs.modal', '.modal', function () {
    $('.modal:visible').length && $(document.body).addClass('modal-open');
  });


  function initalizeAssetURL() {
    const urlParams = new URLSearchParams(window.location.search);
    const assetParam = urlParams.get(assetParamName);
    const assetElem = document.querySelector('[data-asset-id="' + assetParam + '"]')

    if (assetParam != null && assetElem != null) {
      assetElem.click();
    }
  }

  function addURLParam(param, value) {
    let url = new URL(window.location);
    const title = document.title;
    const state = value;
    const newparam = '?' + param + '=' + value;
    //When going back, it checks the state against the url before pushing it - otherwise the pop-stack gets over-ridden and you cant go forward in time.
    if (url.search != newparam) {
      url.searchParams.set(param, value);
      window.history.pushState(state, title, url);
    }
  }

  function removeURLParam(param) {
    let url = new URL(window.location);
    const title = document.title;
    const state = '';

    url.searchParams.delete(param);
    window.history.pushState(state, title, url);
  }

  function addFileClickEvent() {
    document.querySelectorAll('.file-modal-link, .grid a[data-toggle*="modal"]').forEach(element => {
      element.addEventListener('click', (event) => {
        event.preventDefault();
        getModalHtml(element, baseModal, event)
      });
    });
  }

  function loadingSpinner(element) {
    const spinner = '<div class="spinner-border text-primary" role="status"><span class="sr-only">Loading...</span></div>';
    const close = '<button class="modal-navigation modal-close btn btn-lg btn-icon d-none d-md-block" data-dismiss="modal"><i class="material-icons btn-material-icons">close</i></button>'
    element.innerHTML = spinner + close;
  }

  function getModalHtml(element, modal, event) {
    animateProgress();
    if (element.classList.contains('modal-navigation')) {
      loadingSpinner(modal)
    }

    fetch(element.dataset.url).then(response => {
      return response.text();
    }).then(html => {
      createModal(html, modal, element.dataset.assetId, event);
    }).then(() => {
      // Create a new video player for the modal
      $(baseModalId).modal('show');

      const videoPlayer = new Plyr(document.querySelector('.video-player video'));

      const loopButton = `
      <button class="plyr__controls__item plyr__control" type="button" data-plyr="loop">
        <svg class="icon--pressed" aria-hidden="true" focusable="false">
          <use xlink:href="#plyr-restart"></use>
        </svg>
        <svg class="icon--not-pressed" aria-hidden="true" focusable="false">
          <svg id="plyr-restart" viewBox="0 0 18 18"><path d="M9.7 1.2l.7 6.4 2.1-2.1c1.9 1.9 1.9 5.1 0 7-.9 1-2.2 1.5-3.5 1.5-1.3 0-2.6-.5-3.5-1.5-1.9-1.9-1.9-5.1 0-7 .6-.6 1.4-1.1 2.3-1.3l-.6-1.9C6 2.6 4.9 3.2 4 4.1 1.3 6.8 1.3 11.2 4 14c1.3 1.3 3.1 2 4.9 2 1.9 0 3.6-.7 4.9-2 2.7-2.7 2.7-7.1 0-9.9L16 1.9l-6.3-.7z" fill-opacity=".5"></path></svg>
        </svg>
        <span class="label--pressed plyr__sr-only">Disable looping</span>
        <span class="label--not-pressed plyr__sr-only">Enable looping</span>
      </button>
      `;

      videoPlayer.elements.container.addEventListener('ready', () => {
        videoPlayer.elements.controls.querySelector('.plyr__menu').insertAdjacentHTML('afterend', loopButton)

        videoPlayer.elements.controls.querySelector('[data-plyr="loop"]').addEventListener('click', event => {
          event.target.classList.toggle("plyr__control--pressed");
          videoPlayer.media.loop = !videoPlayer.media.loop;
        })
      });

      modal.focus();

      // Trigger activation of comment event listeners
      activateComments();
      $('[data-toggle="tooltip"]').tooltip();
      resetProgress();
    });
  }

  function createModal(html, modal, assetId, event) {

    const template = document.createElement('template');

    template.innerHTML = html.trim();

    if (modal.childElementCount === 0) {
      modal.appendChild(template.content);
    } else {
      modal.children[0].replaceWith(template.content);
    }

    if (modal === baseModal) {
      addButtonClickEvent();
      if (event.type != "popstate") {
        addURLParam(assetParamName, assetId);
      }
    }
  }

  function addButtonClickEvent() {

    document.querySelectorAll('.modal button.previous, .modal button.next').forEach(button => {
      button.addEventListener(
        'click', (event) => getModalHtml(button, baseModal, event)
      );
    });

    document.querySelectorAll('.modal a[data-toggle*="modal"]').forEach(element => {
      element.addEventListener(
        'click', (event) => getModalHtml(element, zoomModal, event)
      );
    });

    document.querySelectorAll(baseModalId + ' .modal-close').forEach(element => {
      element.addEventListener('click', () => {
        removeURLParam(assetParamName);
      });
    });

    baseModal.addEventListener('click', (event) => {
      if (event.target == baseModal) {
        removeURLParam(assetParamName);
      }
    })

  }

  function activateComments() {
    const event = new CustomEvent('activateComments', { bubbles: true });
    baseModal.dispatchEvent(event);
  }
})();
