function getYouTubeID(url) {
  const videoUrl = url;
  let videoId;
  if (videoUrl.includes('v=')) {
    videoId = videoUrl.split('v=')[1];
    const ampersandPosition = videoId.indexOf('&');
    if (ampersandPosition !== -1) {
      videoId = videoId.substring(0, ampersandPosition);
    }
  } else {
    videoId = videoUrl.split('.be/')[1];
  }
  return videoId;
}

function insertYouTubeEmbed(url) {
  const modal = document.querySelector('.js-youtube-embed');
  const id = getYouTubeID(url);
  const iframeMarkup = `<iframe class="embed-responsive-item" src="https://www.youtube.com/embed/${id}" allowfullscreen></iframe>`;
  modal.innerHTML = iframeMarkup;
}

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.video-modal-link').forEach((item) => {
    item.addEventListener('click', () => {
      const url = item.dataset.video;
      insertYouTubeEmbed(url);
    });
  });

  // This must be written in jQuery as the modal events can only be accessed this way.
  // TODO(Mike): When Bootstrap 5 is released, change to vanilla js.
  $('#videoModal').on('hidden.bs.modal', (e) => {
    // When you close the modal, it's content should be removed to prevent the modal being un-hidden with the incorrect content.
    e.target.querySelector('.js-youtube-embed').innerHTML = '';
  });
});
