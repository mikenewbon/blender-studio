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

  $( document ).ready(function() {
    $('.modal').each(function(i){
      $(this).on('hidden.bs.modal', event => {
        $(this).empty();
      });
    })
    //TODO(Mike): When Bootstrap 5 is added, switch to regular JS.
    // modal.addEventListener('hidden.bs.modal', event =>{
    // 	modal.innerHTML="";
    // })
  });

	function getModalHtml(element, modalId) {
		fetch(element.dataset.url).then(response => {
			return response.text();
		}).then(html => {
			createModal(html, modalId);
		}).then(() =>{
      // Create a new video player for the modal
      const player = new Plyr(document.querySelector('.video-player video'));
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
