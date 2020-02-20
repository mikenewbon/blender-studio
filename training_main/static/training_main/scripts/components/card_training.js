/* global ajax:false */

window.cardTraining = (function cardTraining() {
  class CardTraining {
    constructor(element) {
      CardTraining.instances.set(element, this);
      this.element = element;
      this.favoriteUrl = element.dataset.favoriteUrl;
      const [favoriteElement] = this.element.getElementsByClassName('card-training-favorite');
      this.favoriteElement = favoriteElement;
      this._setupEventListeners();
    }

    _setupEventListeners() {
      this.favoriteElement.addEventListener('click', this._postFavorite.bind(this));
    }

    _postFavorite() {
      ajax
        .jsonRequest('POST', this.favoriteUrl, {
          favorite: !this.favoriteElement.dataset.checked
        })
        .then(data => {
          if (data.favorite) {
            this.favoriteElement.dataset.checked = 'checked';
          } else {
            delete this.favoriteElement.dataset.checked;
          }
        });
    }
  }

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
    document.getElementsByClassName('card-training').forEach(CardTraining.getOrWrap);
  });

  return { CardTraining };
})();
