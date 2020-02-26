/* global ajax:false */

window.cardTraining = (function cardTraining() {
  class CardTraining {
    constructor(element) {
      CardTraining.instances.set(element, this);
      this.element = element;
      this._setupEventListeners();
    }

    get favoriteElement() {
      return this.element.getElementsByClassName('card-training-favorite')[0];
    }

    _setupEventListeners() {
      this.favoriteElement.addEventListener('click', this._postFavorite.bind(this));
    }

    _postFavorite() {
      const { favoriteElement } = this;
      ajax
        .jsonRequest('POST', favoriteElement.dataset.favoriteUrl, {
          favorite: !favoriteElement.dataset.checked
        })
        .then(data => {
          if (data.favorite) {
            favoriteElement.dataset.checked = 'checked';
          } else {
            delete favoriteElement.dataset.checked;
          }
        });
    }
  }

  CardTraining.className = 'card-training';
  CardTraining.instances = new WeakMap();
  CardTraining.getOrWrap = function getOrWrap(element) {
    const card = CardTraining.instances.get(element);
    if (card == null) {
      return new CardTraining(element);
    } else {
      return card;
    }
  };

  document.addEventListener('DOMContentLoaded', () => {
    document.getElementsByClassName(CardTraining.className).forEach(CardTraining.getOrWrap);
  });

  return { CardTraining };
})();
