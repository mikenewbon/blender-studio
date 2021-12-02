/* eslint-disable prefer-destructuring */
/* global bootstrap:false initVideo likeButtonSetup hightlightAnchor resetProgress spoilerSetup animateProgress */

window.asset = (function asset() {
  const baseModalId = '#file-modal';
  const baseModalEl = document.querySelector(baseModalId);
  const baseModal = bootstrap.Modal.getOrCreateInstance(baseModalEl);
  const zoomModalId = '#file-zoom-modal';
  const zoomModalEl = document.querySelector(zoomModalId);
  const zoomModal = bootstrap.Modal.getOrCreateInstance(zoomModalEl);
  const assetParamName = 'asset';

  function initalizeAssetURL() {
    const urlParams = new URLSearchParams(window.location.search);
    const assetParam = urlParams.get(assetParamName);
    const assetElem = document.querySelector(`[data-asset-id="${assetParam}"]`);

    if (assetParam != null && assetElem != null) {
      assetElem.click();
    }
  }

  function activateComments() {
    const event = new CustomEvent('activateComments', { bubbles: true });
    baseModalEl.dispatchEvent(event);
  }

  function addURLParam(param, value) {
    const url = new URL(window.location);
    const title = document.title;
    const state = value;
    const newparam = `?${param}=${value}`;
    // hen going back, it checks the state against the url before pushing it - otherwise the pop-stack gets over-ridden and you cant go forward in time.
    if (url.search !== newparam) {
      url.searchParams.set(param, value);
      window.history.pushState(state, title, url);
    }
  }

  function removeURLParam(param) {
    const url = new URL(window.location);
    const title = document.title;
    const state = '';

    url.searchParams.delete(param);
    window.history.pushState(state, title, url);
  }

  function loadingSpinner(element) {
    const spinner =
      '<div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div>';
    const close =
      '<button class="modal-navigation modal-close btn btn-lg btn-icon d-none d-md-block" data-bs-dismiss="modal"><i class="material-icons btn-material-icons">close</i></button>';
    // eslint-disable-next-line no-param-reassign
    element.innerHTML = spinner + close;
  }

  function createModal(html, modal, assetId, event) {
    const template = document.createElement('template');

    template.innerHTML = html.trim();

    // eslint-disable-next-line no-param-reassign
    modal.innerHTML = '';

    modal.appendChild(template.content);

    if (modal === baseModalEl) {
      // eslint-disable-next-line no-use-before-define
      addButtonClickEvent();
      if (event.type !== 'popstate') {
        addURLParam(assetParamName, assetId);
      }
    }
  }

  function getModalHtml(element, modal, event) {
    animateProgress();
    if (element.classList.contains('modal-navigation')) {
      loadingSpinner(modal);
    }

    fetch(element.dataset.url)
      .then((response) => response.text())
      .then((html) => {
        createModal(html, modal, element.dataset.assetId, event);
      })
      .then(() => {
        // Otherwise the Modal object is `_dialog: null` and wont open the modal.
        const dialog = modal.querySelector('.modal-dialog');
        const modalObj = bootstrap.Modal.getOrCreateInstance(modal);
        modalObj._dialog = dialog;
        modalObj.show();

        // Create a new video player for the modal
        initVideo(modal);
        modal.focus();

        // Trigger activation of comment event listeners
        activateComments();
        likeButtonSetup(modal);
        hightlightAnchor(modal);
        resetProgress();
        spoilerSetup(modal);
      });
  }

  function addButtonClickEvent() {
    document.querySelectorAll('.modal button.previous, .modal button.next').forEach((button) => {
      button.addEventListener('click', (event) => getModalHtml(button, baseModalEl, event));
    });

    document.querySelectorAll('.zoom-modal-link').forEach((element) => {
      element.addEventListener('click', (event) => getModalHtml(element, zoomModalEl, event));
    });

    document.querySelectorAll(`${baseModalId} .modal-close`).forEach((element) => {
      element.addEventListener('click', () => {
        removeURLParam(assetParamName);
      });
    });

    baseModalEl.addEventListener('click', (event) => {
      if (event.target === baseModalEl) {
        removeURLParam(assetParamName);
      }
    });
  }

  function addFileClickEvent() {
    document
      .querySelectorAll('.file-modal-link, .grid a[data-toggle*="modal"]')
      .forEach((element) => {
        element.addEventListener('click', (event) => {
          event.preventDefault();
          getModalHtml(element, baseModalEl, event);
        });
      });
  }

  window.addEventListener('popstate', (event) => {
    const fileElementSelector = document.querySelector(`[data-asset-id="${event.state}"]`);

    zoomModal.hide();

    if (event.state === '') {
      // The empty state occurs when the modal is closed, so it hides the modal.
      baseModal.hide();
    } else if (event.state) {
      loadingSpinner(baseModalEl);
      getModalHtml(fileElementSelector, baseModalEl, event);
      baseModal.show();
    }
  });

  document.addEventListener('DOMContentLoaded', () => {
    addFileClickEvent();
    initalizeAssetURL();

    baseModalEl.addEventListener('hidden.bs.modal', () => {
      baseModal.handleUpdate();
      if (baseModalEl.classList.contains('modal-asset')) {
        loadingSpinner(baseModal);
      }
    });

    baseModalEl.addEventListener('shown.bs.modal', () => {
      baseModalEl.focus();
    });

    zoomModalEl.addEventListener('hidden.bs.modal', () => {
      zoomModal.handleUpdate();
    });

    baseModalEl.addEventListener('keydown', (e) => {
      const rightArrow = baseModalEl.querySelector('.modal-navigation.next');
      const leftArrow = baseModalEl.querySelector('.modal-navigation.previous');

      switch (e.key) {
        case 'ArrowRight':
          rightArrow?.click();
          break;
        case 'ArrowLeft':
          leftArrow?.click();
          break;
        case 'Escape':
          baseModal.hide();
          removeURLParam(assetParamName);
          break;
        default:
          break;
      }
    });
  });

  // This fixes the issue of broken scrolling after opening the zoom modal by readding the modal-open class to the body, which gets removed on modal close.
  document.addEventListener('hidden.bs.modal', () => {
    if (baseModal._isShown === true) {
      document.body.classList.add('modal-open');
    }
  });
})();
