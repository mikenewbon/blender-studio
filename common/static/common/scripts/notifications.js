/* global ajax:false bootstrap:false */
function markAsRead(event) {
  event.preventDefault();
  const element = event.currentTarget;
  const url = element.dataset.markReadUrl;
  if (element.dataset.isRead === 'true') return;

  ajax.jsonRequest('POST', url).then(() => {
    if (element.href) {
      window.location.href = element.href;
    } else {
      element
        .closest('.activity-list-item-wrapper')
        .querySelectorAll('.unread')
        .forEach((i) => {
          i.classList.remove('unread');
        });

      const tooltip = bootstrap.Tooltip.getInstance(event.target);
      tooltip.dispose();
      element.remove();
    }
  });
}

function markAllAsRead(event) {
  event.preventDefault();
  const element = event.currentTarget;
  const url = element.dataset.markAllReadUrl;

  ajax.jsonRequest('POST', url).then(() => {
    document.querySelectorAll('.unread').forEach((i) => {
      i.classList.remove('unread');

      if (
        i.closest('.activity-list-item-wrapper') &&
        i.closest('.activity-list-item-wrapper').querySelector('.markasread')
      ) {
        i.closest('.activity-list-item-wrapper').querySelector('.markasread').remove();
      }

      if (document.querySelector('.notifications-counter')) {
        document.querySelector('.notifications-counter').remove();
      }
    });
  });
}

document.querySelectorAll('[data-mark-read-url][data-is-read="false"]').forEach((item) => {
  item.addEventListener('click', (e) => markAsRead(e));
});

document.querySelectorAll('[data-mark-all-read-url]').forEach((item) => {
  item.addEventListener('click', (e) => markAllAsRead(e));
});
