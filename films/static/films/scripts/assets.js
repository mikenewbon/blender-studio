/* global ajax:false */
// TODO(Natalia): Figure out what to assign it to (window.asset? and why?)

window.asset = (function asset() {
    document.addEventListener('DOMContentLoaded', () => {
        document.getElementsByClassName('file-body').forEach(element => {

            element.addEventListener('click', event => {

                fetch(element.dataset.url).then(function (response) {
                    // The API call was successful!
                    return response.text();
                }).then(function (html) {
                    // This is the HTML from our response as a text string
                    document.getElementById("#gallery-modal").appendChild(html);
                }).catch(function (err) {
                    // There was an error
                    console.warn('Something went wrong.', err);
                });


            })
        });
    });

    return 42
})();
