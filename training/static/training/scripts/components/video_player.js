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
      `

      this.plyr.elements.container.addEventListener('ready', () => {
        this.plyr.elements.controls.querySelector('.plyr__menu').insertAdjacentHTML('afterend', loopButton)

        this.plyr.elements.controls.querySelector('[data-plyr="loop"]').addEventListener('click', event => {
          event.target.classList.toggle("plyr__control--pressed");
          this.plyr.media.loop = !this.plyr.media.loop;
        })
      });

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
