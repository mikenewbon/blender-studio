/* global ajax:false */

window.productionLogs = (function productionLogs() {
    const activityFeedSelector = '#activity-feed';
    const loadMoreWeeksButtonSelector = '#load-more-weeks';

    document.addEventListener('DOMContentLoaded', () => {
        addButtonClickEvent();
    });

    function addButtonClickEvent() {
        const loadMoreWeeksButton = document.querySelector(loadMoreWeeksButtonSelector);
        if (loadMoreWeeksButton) {
            loadMoreWeeksButton.addEventListener(
          'click', event => {
              getMoreLogs(event.target);
          });
        }
    }

    function getMoreLogs(element) {
        fetch(element.dataset.url).then(response => {
            return response.text();
        }).then(html => {
            const template = document.createElement('template');
		    template.innerHTML = html.trim();

		    const activityFeed = document.querySelector(activityFeedSelector);
		    activityFeed.children[activityFeed.children.length - 1].replaceWith(template.content);

		    addButtonClickEvent();
        }).catch(err => {
            console.warn('Something went wrong.', err);
        })
    }
})();
