function epochToDate(epoch) {
  if (epoch < 10000000000)
    epoch *= 1000; // convert to milliseconds (Epoch is usually expressed in seconds, but Javascript uses Milliseconds)
  var epoch = epoch + (new Date().getTimezoneOffset() * -1); //for timeZone
  return new Date(epoch);
}

function timeDifference(datetime) {

  let now = new Date();

  const msPerMinute = 60 * 1000;
  const msPerHour = msPerMinute * 60;
  const msPerDay = msPerHour * 24;
  const msPerMonth = msPerDay * 30;
  const msPerYear = msPerDay * 365;

  let elapsed = now - datetime;

  if (elapsed < msPerMinute) {
    let value = Math.round(elapsed / 1000);
    if (value == 1) {
      return value + ' sec ago'
    } else {
      return value + ' secs ago';
    }
  }

  else if (elapsed < msPerHour) {
    let value = Math.round(elapsed / msPerMinute);
    if (value == 1) {
      return value + ' min ago'
    } else {
      return value + ' mins ago';
    }
  }

  else if (elapsed < msPerDay) {

    let value = Math.round(elapsed / msPerHour);
    if (value == 1) {
      return value + ' hour ago'
    } else {
      return value + ' hours ago';
    }
  }

  else if (elapsed < msPerMonth) {
    let value = Math.round(elapsed / msPerDay);
    if (value == 1) {
      return value + ' day ago'
    } else {
      return value + ' days ago';
    }
  }

  else if (elapsed < msPerYear) {
    let value = Math.round(elapsed / msPerMonth);
    if (value == 1) {
      return value + ' month ago'
    } else {
      return value + ' months ago';
    }
  }

  else {
    let value = Math.round(elapsed / msPerYear);
    if (value == 1) {
      return value + ' year ago'
    } else {
      return value + ' years ago';
    }
  }
}

function titleCase(str) {
  if (str == null) {
    return null;
  } else {


    var splitStr = str.toLowerCase().split(' ');
    for (var i = 0; i < splitStr.length; i++) {
      // You do not need to check if i is larger than splitStr length, as your for does that for you
      // Assign it back to the array
      splitStr[i] = splitStr[i].charAt(0).toUpperCase() + splitStr[i].substring(1);
    }
    // Directly return the joined string
    return splitStr.join(' ');
  }
}

function authCheck() {
  if (document.querySelector('body[data-authenticated="true"]')) {
    return true;
  } else {
    return false;
  }
}

function cardCarousel(element, slides) {
  var totalCards = element.parentElement.childElementCount;
  var next = $(element).next();
  if (!next.length) {
    next = $(element).siblings(':first');
  }
  next.children(':first-child').clone().appendTo($(element));

  for (var i = 2; i < totalCards; i++) {
    next = next.next();
    if (!next.length) {
      next = $(element).siblings(':first');
    }

    next.children(':first-child').clone().appendTo($(element));
  }
}

let currentUser = '';
document.addEventListener('DOMContentLoaded', () => {
  currentUser = JSON.parse(
    document.getElementById('current-user').textContent
  );
});

// Adds tooltips if text overflows.
$(function () {
  $('[data-tooltip="tooltip-overflow"]').each(function () {
    $(this).tooltip()
    $(this).tooltip('disable')
    const text = this.querySelector('.overflow-text');
    $(this).mouseenter(function () {
      if (text.scrollWidth > text.clientWidth) {
        $(this).tooltip('enable');
        $(this).tooltip('show');
      }
    })
  });
});

// Generic like button
document.addEventListener('DOMContentLoaded', () => {
  likeButtonSetup(document);
});

function likeButtonSetup(element) {
  element.querySelectorAll('[data-like-url]').forEach((i) => {
    i.addEventListener('click', (e) => {
      likeButton = e.target;
      likeCount = e.target.querySelector('.likes-count');
      likeUrl = likeButton.dataset.likeUrl;
      liked = likeButton.dataset.checked;

      ajax.jsonRequest('POST', likeUrl, {
        like: !liked
      }).then((data) => {
        if (data.like) {
          likeButton.dataset.checked = 'checked';
        } else {
          delete likeButton.dataset.checked;
        }
        likeCount.innerText = data.number_of_likes;
      });
    });
  });
}
