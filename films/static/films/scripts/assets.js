/* global ajax:false */
// TODO(Natalia): Figure out what to assign it to (window.asset? and why?)

window.asset = (function asset() {
    document.addEventListener('DOMContentLoaded', () => {
        document.getElementsByClassName('file-body').forEach(element => {
            element.addEventListener('click', event => {
                fetch(element.dataset.url).then(response => {
                    return response.text();
                }).then(html => {
                    const template = document.createElement('template');
                    template.innerHTML = html.trim();

                    const modal = document.getElementById('gallery-modal')
                    if (modal.childElementCount === 0) {
                        modal.appendChild(template.content);
                    } else {
                        modal.children[0].replaceWith(template.content);
                    }
                }).catch(err => {
                    console.warn('Something went wrong.', err);
                });
            });
        });
    });
})();
