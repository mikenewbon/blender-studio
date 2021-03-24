/* eslint-disable prefer-destructuring */
/* eslint-disable no-undef */
// eslint-disable-next-line no-unused-vars
function epochToDate(epoch) {
  let epochValue = epoch;
  if (epochValue < 10000000000) {
    epochValue *= 1000; // convert to milliseconds (Epoch is usually expressed in seconds, but Javascript uses Milliseconds)
  }
  epochValue += new Date().getTimezoneOffset() * -1; // for timeZone
  return new Date(epochValue);
}

// eslint-disable-next-line no-unused-vars
function timeDifference(datetime) {
  const now = new Date();

  const msPerMinute = 60 * 1000;
  const msPerHour = msPerMinute * 60;
  const msPerDay = msPerHour * 24;
  const msPerMonth = msPerDay * 30;
  const msPerYear = msPerDay * 365;

  const elapsed = now - datetime;

  if (elapsed < msPerMinute) {
    const value = Math.round(elapsed / 1000);
    if (value === 1) {
      return `${value}\xa0sec ago`;
    } else {
      return `${value}\xa0secs ago`;
    }
  } else if (elapsed < msPerHour) {
    const value = Math.round(elapsed / msPerMinute);
    if (value === 1) {
      return `${value}\xa0min ago`;
    } else {
      return `${value}\xa0mins ago`;
    }
  } else if (elapsed < msPerDay) {
    const value = Math.round(elapsed / msPerHour);
    if (value === 1) {
      return `${value}\xa0hour ago`;
    } else {
      return `${value}\xa0hours ago`;
    }
  } else if (elapsed < msPerMonth) {
    const value = Math.round(elapsed / msPerDay);
    if (value === 1) {
      return `${value}\xa0day ago`;
    } else {
      return `${value}\xa0days ago`;
    }
  } else if (elapsed < msPerYear) {
    const value = Math.round(elapsed / msPerMonth);
    if (value === 1) {
      return `${value}\xa0month ago`;
    } else {
      return `${value}\xa0months ago`;
    }
  } else {
    const value = Math.round(elapsed / msPerYear);
    if (value === 1) {
      return `${value}\xa0year ago`;
    } else {
      return `${value}\xa0years ago`;
    }
  }
}

// eslint-disable-next-line no-unused-vars
function titleCase(str) {
  if (str == null) {
    return null;
  } else {
    const splitStr = str.toLowerCase().split(' ');
    for (let i = 0; i < splitStr.length; i += 1) {
      // You do not need to check if i is larger than splitStr length, as your for does that for you
      // Assign it back to the array
      splitStr[i] = splitStr[i].charAt(0).toUpperCase() + splitStr[i].substring(1);
    }
    // Directly return the joined string
    return splitStr.join(' ');
  }
}

// eslint-disable-next-line no-unused-vars
function authCheck() {
  if (document.querySelector('body[data-authenticated="true"]')) {
    return true;
  } else {
    return false;
  }
}

function cardCarousel(element) {
  const totalCards = element.parentElement.childElementCount;
  let next = $(element).next();
  if (!next.length) {
    next = $(element).siblings(':first');
  }
  next.children(':first-child').clone().appendTo($(element));

  for (let i = 2; i < totalCards; i += 1) {
    next = next.next();
    if (!next.length) {
      next = $(element).siblings(':first');
    }

    next.children(':first-child').clone().appendTo($(element));
  }
}

document.addEventListener('DOMContentLoaded', () => {
  document
    .querySelectorAll('.carousel-card-3 .carousel-item, .carousel-card-4 .carousel-item')
    .forEach((item) => {
      cardCarousel(item);
    });
});

let currentUser = null;
document.addEventListener('DOMContentLoaded', () => {
  // eslint-disable-next-line no-unused-vars
  currentUser = JSON.parse(document.getElementById('current-user').textContent);
});

// Adds tooltips if text overflows.
$(() => {
  $('[data-tooltip="tooltip-overflow"]').each(function () {
    $(this).tooltip();
    $(this).tooltip('disable');
    const text = this.querySelector('.overflow-text');
    $(this).mouseenter(() => {
      if (text.scrollWidth > text.clientWidth) {
        $(this).tooltip('enable');
        $(this).tooltip('show');
      }
    });
  });
});

function spoilerSetup(element) {
  element.querySelectorAll('.spoiler-alert').forEach((i) => {
    i.addEventListener('click', () => {
      i.classList.add('revealed');
    });
  });
}

function likeButtonSetup(element) {
  element.querySelectorAll('[data-like-url]').forEach((i) => {
    i.addEventListener('click', (e) => {
      const likeButton = e.target;
      const likeUrl = likeButton.dataset.likeUrl;
      const liked = likeButton.dataset.checked;

      // eslint-disable-next-line no-undef
      ajax
        .jsonRequest('POST', likeUrl, {
          like: !liked,
        })
        .then((data) => {
          document.querySelectorAll(`[data-like-url="${likeUrl}"]`).forEach((i) => {
            const item = i;
            if (data.like) {
              item.dataset.checked = 'checked';
            } else {
              delete item.dataset.checked;
            }
            if (i.querySelector('.likes-count')) {
              // eslint-disable-next-line no-param-reassign
              i.querySelector('.likes-count').innerText = data.number_of_likes;
            } else {
              const likeCountHTML = `<span class="likes-count">${data.number_of_likes}</span>`;
              i.insertAdjacentHTML('beforeend', likeCountHTML);
            }
          });
        });
    });
  });
}

// Generic like button
document.addEventListener('DOMContentLoaded', () => {
  likeButtonSetup(document);
  spoilerSetup(document);
});

// Notification highlighting
function getAnchor() {
  const currentUrl = document.URL;
  const urlParts = currentUrl.split('#');

  return urlParts.length > 1 ? urlParts[1] : null;
}

function hightlightAnchor(element) {
  const id = getAnchor();
  const anchor = element.querySelector(`#${id}`);

  if (id != null && anchor != null) {
    anchor.classList.add('highlight');
    anchor.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
}

document.addEventListener('DOMContentLoaded', () => {
  hightlightAnchor(document);
});

// Make Masonry Grid

// eslint-disable-next-line no-unused-vars
function makeGrid() {
  const $grid = $('.grid').masonry({
    itemSelector: '.grid-item',
    columnWidth: '.grid-sizer',
    percentPosition: true,
    horizontalOrder: true,
  });

  $grid.imagesLoaded().progress(() => {
    $grid.masonry('layout');
  });
}

// eslint-disable-next-line no-unused-vars
function initVideo(container) {
  const players = Array.from(container.querySelectorAll('.video-player video')).map(
    // eslint-disable-next-line no-undef
    (p) => new Plyr(p)
  );

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

  players.forEach((element) =>
    element.elements.container.addEventListener('ready', () => {
      const dataElement = element.elements.container.parentElement;
      const startPosition = Number(dataElement.dataset.startPosition);
      const progressPostMinWait = 2000;
      const progressUrl = dataElement.dataset.progressUrl;
      let _postingProgress = 0;
      let _lastPostProgress = null;

      element.elements.controls
        .querySelector('.plyr__menu')
        .insertAdjacentHTML('afterend', loopButton);

      element.elements.controls
        .querySelector('[data-plyr="loop"]')
        .addEventListener('click', (event) => {
          event.target.classList.toggle('plyr__control--pressed');
          // eslint-disable-next-line no-param-reassign
          element.media.loop = !element.media.loop;
        });

      function postProgress() {
        _lastPostProgress = Date.now();
        _postingProgress += 1;
        // eslint-disable-next-line no-undef
        ajax
          .jsonRequest('POST', progressUrl, {
            position: element.currentTime,
          })
          .finally(() => {
            _postingProgress -= 1;
          });
      }

      if (progressUrl) {
        element.on('loadeddata', () => {
          // Setting a start position doesn't appear to work on "ready", only on "loaddata"
          // See https://github.com/sampotts/plyr/issues/208#issuecomment-400539990
          if (startPosition <= element.duration) {
            // eslint-disable-next-line no-param-reassign
            element.currentTime = startPosition;
          }
        });

        element.on('timeupdate', () => {
          if (
            _postingProgress === 0 &&
            (_lastPostProgress == null || Date.now() - _lastPostProgress >= progressPostMinWait)
          ) {
            postProgress();
          }
        });
      }
    })
  );
}

// Lightbox in blogs
document.addEventListener('DOMContentLoaded', () => {
  const imageZoomModalID = '#image-zoom-modal';
  const imageZoomModal = document.querySelector(imageZoomModalID);
  const imageWrapper = imageZoomModal.querySelector('.modal-body');

  document.querySelectorAll('.image-zoom').forEach((element) => {
    const imageURL = element.dataset.image;
    const imageHTML = `<img src="${imageURL}">`;

    element.addEventListener('click', () => {
      imageWrapper.innerHTML = imageHTML;
      // eslint-disable-next-line no-undef
      $(imageZoomModalID).modal('show');
    });
  });
});

// Readmore link
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.read-more-link').forEach((element) => {
    const id = element.hash;
    element.addEventListener('click', (event) => {
      event.preventDefault();
      document.querySelector(id + ' .read-more-elip').classList.toggle('d-none');
      document.querySelector(id + ' .read-more-text').classList.toggle('d-none');
      if (element.querySelector('.read-more-less').innerText === 'more') {
        // eslint-disable-next-line no-param-reassign
        element.querySelector('.read-more-less').innerText = 'less';
      } else {
        // eslint-disable-next-line no-param-reassign
        element.querySelector('.read-more-less').innerText = 'more';
      }
    });
  });
});
