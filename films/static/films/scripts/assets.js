/* global ajax:false */
// TODO(Natalia): Figure out what to assign it to (window.asset? and why?)

window.asset = (function asset() {
    document.addEventListener('DOMContentLoaded', () => {
        document.getElementsByClassName('file-body').forEach(element => {
            element.addEventListener('click', event => {
                fetch(element.dataset.url).then(response => {
                    if (response.status >= 200 && response.status < 300) {
                        return Promise.resolve(response);
                    }
                    return Promise.reject(new Error(response.statusText));
                }).then(response => {
                    const html = response.text()
                    const template = document.createElement('template');
                    template.innerHTML = html.trim();

                    const modal = document.getElementById("gallery-modal")
                    if (modal.childElementCount !== 0) {
                        modal.children[0].replaceWith(template.content);
                    } else {
                        modal.appendChild(template.content);
                    }
                })
            })
        });
    });
})();
