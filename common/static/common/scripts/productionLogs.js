/* global ajax:false */

window.productionLogs = (function productionLogs() {
    const activityFeedId = 'activity-feed';

    document.addEventListener('DOMContentLoaded', () => {
        document.querySelectorAll(
            'a.btn.btn-sm.btn-secondary.collapsed.show-more-less'
        ).forEach(element => {
            element.addEventListener('click', () => {
                getMoreLogs(element);
            })
        })
    });

    function getMoreLogs(element) {
        console.log(element.dataset.url);
        fetch(element.dataset.url).then(response => {
            return response.text();
        }).then(html => {
            console.log('response arrived');
            // TODO: insert the response in the right place in the DOM
        }).catch(err => {
            console.warn('Something went wrong.', err);
        })
    }

})();
