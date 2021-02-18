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

$('.carousel-card-3 .carousel-item').each(function () {
  cardCarousel(this, 3);
});

$('.carousel-card-4 .carousel-item').each(function () {
  cardCarousel(this, 4);
});

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
  spoilerSetup(document);
});

function spoilerSetup(element) {
  element.querySelectorAll('.spoiler-alert').forEach((i) => {
    i.addEventListener('click', (e) => {
      i.classList.add('revealed');
    })
  });
}

function likeButtonSetup(element) {
  element.querySelectorAll('[data-like-url]').forEach((i) => {
    i.addEventListener('click', (e) => {
      likeButton = e.target;
      likeUrl = likeButton.dataset.likeUrl;
      liked = likeButton.dataset.checked;

      ajax.jsonRequest('POST', likeUrl, {
        like: !liked
      }).then((data) => {
        document.querySelectorAll('[data-like-url="' + likeUrl + '"]').forEach((i) => {
          if (data.like) {
            i.dataset.checked = 'checked';
          } else {
            delete i.dataset.checked;
          }
          i.querySelector('.likes-count').innerText = data.number_of_likes;
        });
      });
    });
  });
}


//Notification highlighting
function getAnchor() {
  var currentUrl = document.URL,
    urlParts = currentUrl.split('#');

  return (urlParts.length > 1) ? urlParts[1] : null;
}

function hightlightAnchor(element) {

  id = getAnchor();
  anchor = element.querySelector('#' + id)

  if (id != null && anchor != null) {
    anchor.classList.add('highlight')
    anchor.scrollIntoView({ behavior: "smooth", block: "center" });
  }
}

document.addEventListener('DOMContentLoaded', () => {
  hightlightAnchor(document);
});



// Make Masonry Grid

function makeGrid() {
  var $grid = $('.grid').masonry({
    itemSelector: '.grid-item',
    columnWidth: '.grid-sizer',
    percentPosition: true,
    horizontalOrder: true,
  });

  $grid.imagesLoaded().progress(function () {
    $grid.masonry('layout');
  });

}

function initVideo(container) {
  const players = Array.from(container.querySelectorAll('.video-player video')).map(p => new Plyr(p));

  const loopButton = `
    <button class="plyr__controls__item plyr__control" type="button" data-plyr="loop">
      <svg class="icon--pressed" aria-hidden="true" focusable="false">
        <use xlink:href="#plyr-restart"></use>
      </svg>
      <svg class="icon--not-pressed" aria-hidden="true" focusable="false">
        <svg id="plyr-restart" viewBox="0 0 18 18"><path d="M9.7 1.2l.7 6.4 2.1-2.1c1.9 1.9 1.9 5.1 0 7-.9 1-2.2 1.5-3.5 1.5-1.3 0-2.6-.5-3.5-1.5-1.9-1.9-1.9-5.1 0-7 .6-.6 1.4-1.1 2.3-1.3l-.6-1.9C6 2.6 4.9 3.2 4 4.1 1.3 6.8 1.3 11.2 4 14c1.3 1.3 3.1 2 4.9 2 1.9 0 3.6-.7 4.9-2 2.7-2.7 2.7-7.1 0-9.9L16 1.9l-6.3-.7z" fill-opacity=".5"></path></svg>
      </svg>
      <span class="label--pressed plyr__sr-only">Disable looping</span>
      <span class="label--not-pressed plyr__sr-only">Enable looping</span>
    </button>
    `;

  players.forEach(element => element.elements.container.addEventListener('ready', () => {
    element.elements.controls.querySelector('.plyr__menu').insertAdjacentHTML('afterend', loopButton)

    element.elements.controls.querySelector('[data-plyr="loop"]').addEventListener('click', event => {
      event.target.classList.toggle("plyr__control--pressed");
      element.media.loop = !element.media.loop;
    })
  }));
}


//Lightbox in blogs
document.addEventListener('DOMContentLoaded', () => {
  const imageZoomModalID = '#image-zoom-modal';
  const imageZoomModal = document.querySelector(imageZoomModalID);
  const imageWrapper = imageZoomModal.querySelector('.modal-body');

  document.querySelectorAll('.image-zoom').forEach(element => {
    const imageURL = element.dataset.image;
    console.log(element)
    const imageHTML = `<img src="${imageURL}">`
    element.addEventListener('click', (event) => {
      imageWrapper.innerHTML = imageHTML;
      $(imageZoomModalID).modal('show');
    })
  })
});
