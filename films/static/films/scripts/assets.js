/* global ajax:false */

window.asset = (function asset() {
	document.addEventListener('DOMContentLoaded', () => {
		document.querySelectorAll(
			'.file a[data-toggle*="modal"], .grid a[data-toggle*="modal"]'
		).forEach(element => {
			element.addEventListener('click', () => { getModalHtml(element); });
		});
	});

	function getModalHtml(element) {
		fetch(element.dataset.url).then(response => {
			return response.text();
		}).then(html => {
			createModal(html);
			addButtonClickEvent();
		}).catch(err => {
			console.warn('Something went wrong.', err);
		});
	}

	function createModal(html) {
		const template = document.createElement('template');
		template.innerHTML = html.trim();

		const modal = document.getElementById('file-modal');
		if (modal.childElementCount === 0) {
			modal.appendChild(template.content);
		} else {
			modal.children[0].replaceWith(template.content);
		}
		$(modal).on('hidden.bs.modal', event => {
			modal.innerHTML = "";
		});
		//TODO(Mike): When Bootstrap 5 is added, switch to regular JS.
		// modal.addEventListener('hidden.bs.modal', event =>{
		// 	modal.innerHTML="";
		// })
	}

	function addButtonClickEvent() {
		document.querySelectorAll(
			'.modal button.previous, .modal button.next'
		).forEach(button => {
			button.addEventListener('click', () => { getModalHtml(button); });
		});
	}
})();
