/* global ajax:false */

window.productionLogs = (function productionLogs() {
    const activityFeedId = 'activity-feed';

    document.addEventListener('DOMContentLoaded', () => {
        addButtonClickEvent();
    });

    function addButtonClickEvent() {
        document.querySelectorAll(
            'a.btn.btn-sm.btn-secondary.collapsed.show-more-less'
        ).forEach(element => {
            element.addEventListener('click', () => {
                getMoreLogs(element);
            })
        })
    }

    function getMoreLogs(element) {
        fetch(element.dataset.url).then(response => {
            return response.text();
        }).then(html => {
            const template = document.createElement('template');
		    template.innerHTML = html.trim();

		    const activityFeed = document.getElementById(activityFeedId);
		    activityFeed.children[activityFeed.children.length - 1].replaceWith(template.content);

		    addButtonClickEvent();
        }).catch(err => {
            console.warn('Something went wrong.', err);
        })
    }
})();
