function getYouTubeID(url) {
  const videoUrl = url;
  let videoId;
  if (videoUrl.includes('v=')) {
    // eslint-disable-next-line prefer-destructuring
    videoId = videoUrl.split('v=')[1];
    const ampersandPosition = videoId.indexOf('&');
    if (ampersandPosition !== -1) {
      videoId = videoId.substring(0, ampersandPosition);
    }
  } else {
    // eslint-disable-next-line prefer-destructuring
    videoId = videoUrl.split('.be/')[1];
  }
  return videoId;
}

function insertYouTubeEmbed(url) {
  const modal = document.querySelector('.js-youtube-embed');
  const id = getYouTubeID(url);
  const iframeMarkup = `<iframe src="https://www.youtube.com/embed/${id}" allowfullscreen></iframe>`;
  modal.innerHTML = iframeMarkup;
}

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.video-modal-link').forEach((item) => {
    item.addEventListener('click', () => {
      const url = item.dataset.video;
      insertYouTubeEmbed(url);
    });
  });

  const modalEl = document.querySelector('#videoModal');
  modalEl.addEventListener('hidden.bs.modal', (e) => {
    e.target.querySelector('.js-youtube-embed').innerHTML = '';
  });
});
