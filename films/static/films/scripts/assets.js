/* global ajax:false */
// TODO(Natalia): Figure out what to assign it to (window.asset? and why?)

window.asset = (function asset() {
    document.addEventListener('DOMContentLoaded', () => {
        document.getElementsByClassName('file-body').forEach(element => {
            console.log(element.className);
            element.addEventListener('click', event => {
                event.preventDefault();
                console.log('click click');
            });
        });
    });
})();
