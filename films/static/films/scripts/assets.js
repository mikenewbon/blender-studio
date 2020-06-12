/* global ajax:false */
// TODO(Natalia): Figure out what to assign it to (window.asset? and why?)

window.asset = (function asset() {
    document.addEventListener('DOMContentLoaded', () => {
        document.getElementsByClassName('file').forEach(element => {
            element.addEventListener('click', event => {
                console.log(element)
                // event.preventDefault();  // doesn't change anything...
                fetch(`../api/2/assets/4`).then(response => {
                    console.log('response:', response)
                    if (response.status >= 200 && response.status < 300) {
                        return Promise.resolve(response);
                    }
                    return Promise.reject(new Error(response.statusText));
                })
                // .then(response => response.json())
                .then(response => console.log(response));
            })
        });
    });

    return 42
})();
