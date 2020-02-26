/* global ajax:false */

window.section = (function section() {
  class SectionProgressReporter {
    constructor(element) {
      SectionProgressReporter.instances.set(element, this);
      this.element = element;
      const data = JSON.parse(this.element.textContent);
      this.progressUrl = data.progress_url;
      this.startedTimeout = data.started_timeout;
      this.finishedTimeout = data.finished_timeout;
      this._setupEventListeners();
    }

    _setupEventListeners() {
      if (this.startedTimeout != null) {
        setTimeout(() => {
          this._postProgress('started');
        }, this.startedTimeout * 1000);
      }

      if (this.finishedTimeout != null) {
        setTimeout(() => {
          this._postProgress('finished');
        }, this.finishedTimeout * 1000);
      }
    }

    _postProgress(status) {
      ajax.jsonRequest('POST', this.progressUrl, {
        status
      });
    }
  }

  SectionProgressReporter.dataId = 'sectionProgressReportingData';
  SectionProgressReporter.instances = new WeakMap();
  SectionProgressReporter.getOrWrap = function getOrWrap(element) {
    const instance = SectionProgressReporter.instances.get(element);
    if (instance == null) {
      return new SectionProgressReporter(element);
    } else {
      return instance;
    }
  };

  document.addEventListener('DOMContentLoaded', () => {
    const element = document.getElementById(SectionProgressReporter.dataId);
    if (element != null) {
      SectionProgressReporter.getOrWrap(element);
    }
  });

  return { SectionProgressReporter };
})();
