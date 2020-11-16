
//Mark as read notifications
$(function () {
  $('[data-mark-read-url][data-is-read="false"]').on('click', function (e) {
    $el = $(this);
    if ($el.data('is-read')) {
      // Already marked as read, just continue
      return true;
    }
    e.preventDefault();
    url = $el.data('mark-read-url');
    ajax.jsonRequest('POST', url).then(function () {
      if (e.currentTarget.href) {
        window.location.href = e.currentTarget.href;
      } else {
        e.currentTarget.closest('.activity-list-item-wrapper').querySelectorAll('.unread').forEach((i) => {
          i.classList.remove('unread');
        })
        $(e.currentTarget).tooltip('dispose');
        e.currentTarget.remove();
      }
    }).catch((error) => {
      if (e.currentTarget.href != null) {
        window.location.href = e.currentTarget.href
      }
    });
  });

  $('[data-mark-all-read-url]').on('click', function (e) {
    $el = $(this);
    e.preventDefault();
    url = $el.data('mark-all-read-url');
    ajax.jsonRequest('POST', url).then(function () {
      document.querySelectorAll('.unread').forEach((i) => {
        i.classList.remove('unread');

        if (i.closest('.activity-list-item-wrapper') && i.closest('.activity-list-item-wrapper').querySelector('.markasread')) {
          i.closest('.activity-list-item-wrapper').querySelector('.markasread').remove();
        }

        if (document.querySelector('.notifications-counter')) {
          document.querySelector('.notifications-counter').remove();
        }

      });
    });
  });
});
