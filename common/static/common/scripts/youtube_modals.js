function getYouTubeID(url) {
  let video_url = url;
  let video_id = video_url.split('v=')[1];
  let ampersandPosition = video_id.indexOf('&');
  if (ampersandPosition != -1) {
    video_id = video_id.substring(0, ampersandPosition);
  }
  return video_id;
}

function insertYouTubeEmbed(url) {
  let modal = document.querySelector('.js-youtube-embed');
  let id = getYouTubeID(url);
  let iframeMarkup = '<iframe class="embed-responsive-item" src="https://www.youtube.com/embed/' + id +
    '" allowfullscreen></iframe>';
  modal.innerHTML = iframeMarkup;
}

document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll('.video-modal-link').forEach(item =>{
    item.addEventListener('click', () =>{
      url = item.dataset.video;
      id = getYouTubeID(url);
      insertYouTubeEmbed(url);
    })
  });


  //This must be written in jQuery as the modal events can only be accessed this way.
  // TODO(Mike): When Bootstrap 5 is released, change to vanilla js.
  $('#videoModal').on('hidden.bs.modal', (e) =>{
    // When you close the modal, it's content should be removed to prevent the modal being un-hidden with the incorrect content.
    e.target.querySelector('.js-youtube-embed').innerHTML = "";
  });
});
