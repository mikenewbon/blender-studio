/* global ajax:false */

window.asset = (function asset() {
	const baseModalId = 'file-modal';
	const zoomModalId = 'file-zoom-modal';

	document.addEventListener('DOMContentLoaded', () => {
		document.querySelectorAll(
			'.file a[data-toggle*="modal"], .grid a[data-toggle*="modal"]'
		).forEach(element => {
			element.addEventListener('click', () => getModalHtml(element, baseModalId));
		});
  });

  // Using Jquery due to BootStrap events only being avaiable here.
  // TODO(Mike): When Bootstrap 5 is added, switch to regular JS.
  $( document ).ready(function() {
    $('.modal').each(function(i){
      // Remove modal content on hide
      $(this).on('hidden.bs.modal', event => {
        $(this).empty();
        loadingSpinner(this);
      });
      // Give modal focus on open
      $(this).on('shown.bs.modal', function () {
        $(this).trigger('focus')
      })
    })
    // Left-Right keyboard events
    $('#file-modal').keydown(function( event ) {
      switch(event.key){
        case "ArrowRight":
          $('#file-modal .modal-navigation.next').trigger('click');
          break;
        case "ArrowLeft":
          $('#file-modal .modal-navigation.previous').trigger('click');
          break;
      }
    });
  });

  function loadingSpinner(element){
    const spinner = '<div class="spinner-border text-primary" role="status"><span class="sr-only">Loading...</span></div>';
    element.innerHTML = spinner;
  };

	function getModalHtml(element, modalId) {
    if (element.classList.contains('modal-navigation')){
      loadingSpinner(document.querySelector('#' + baseModalId))
    };

		fetch(element.dataset.url).then(response => {
			return response.text();
		}).then(html => {
			createModal(html, modalId);
		}).then(() =>{
      // Create a new video player for the modal
      const player = new Plyr(document.querySelector('.video-player video'));
      document.querySelector('.modal').focus();
    }).catch(err => {
			console.warn('Something went wrong.', err);
		});
	}

	function createModal(html, modalId) {
		const template = document.createElement('template');
		template.innerHTML = html.trim();
		const modal = document.getElementById(modalId);
		if (modal.childElementCount === 0) {
			modal.appendChild(template.content);
		} else {
			modal.children[0].replaceWith(template.content);
		}

		if (modalId === baseModalId) {
			addButtonClickEvent();
		}
	}

	function addButtonClickEvent() {
		document.querySelectorAll(
			'.modal button.previous, .modal button.next'
		).forEach(button => {
			button.addEventListener(
				'click', () => getModalHtml(button, baseModalId)
			);
		});
		document.querySelectorAll(
			'.modal a[data-toggle*="modal"]'
		).forEach(element => {
			element.addEventListener(
				'click', () => getModalHtml(element, zoomModalId)
			);
		});
	}
})();
