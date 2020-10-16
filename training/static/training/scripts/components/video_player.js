/* global ajax:false, Plyr:false */

window.videoPlayer = (function videoPlayer() {
  class VideoPlayer {
    constructor(element) {
      VideoPlayer.instances.set(element, this);
      this.element = element;
      this.startPosition = Number(this.element.dataset.startPosition);
      this.progressPostMinWait = 2000;
      this.progressUrl = this.element.dataset.progressUrl;
      this._postingProgress = 0;
      this._lastPostProgress = null;
      this.plyr = new Plyr(this.videoElement);
      this._setupEventListeners();
    }

    get videoElement() {
      return this.element.querySelector('video');
    }

    _setupEventListeners() {
      this.plyr.on('loadeddata', () => {
        // Setting a start position doesn't appear to work on "ready", only on "loaddata"
        // See https://github.com/sampotts/plyr/issues/208#issuecomment-400539990
        if (this.startPosition <= this.plyr.duration) {
          this.plyr.currentTime = this.startPosition;
        }
      });

      this.plyr.on('timeupdate', () => {
        if (
          this._postingProgress === 0 &&
          (this._lastPostProgress == null ||
            Date.now() - this._lastPostProgress >= this.progressPostMinWait)
        ) {
          this._postProgress();
        }
      });
    }

    _postProgress() {
      const { plyr } = this;
      this._lastPostProgress = Date.now();
      this._postingProgress += 1;
      ajax
        .jsonRequest('POST', this.progressUrl, {
          position: plyr.currentTime
        })
        .finally(() => {
          this._postingProgress -= 1;
        });
    }
  }

  VideoPlayer.className = 'video-player';
  VideoPlayer.instances = new WeakMap();
  VideoPlayer.getOrWrap = function getOrWrap(element) {
    const instance = VideoPlayer.instances.get(element);
    if (instance == null) {
      return new VideoPlayer(element);
    } else {
      return instance;
    }
  };

  document.addEventListener('DOMContentLoaded', () => {
    document.getElementsByClassName(VideoPlayer.className).forEach(VideoPlayer.getOrWrap);
  });

  return { VideoPlayer };
})();
