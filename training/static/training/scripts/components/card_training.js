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
      const card = this.element;
      const favoriteButton = this.element.querySelector('.card-training-favorite');
      const favoriteSection = document.querySelector('#savedTraining');

      ajax
        .jsonRequest('POST', card.dataset.favoriteUrl, {

          favorite: !card.dataset.checked
        })
        .then(data => {
          if (data.favorite) {
            card.dataset.checked = 'checked';
            favoriteButton.classList.add('checked', 'primary');
            favoriteButton.firstElementChild.innerText = 'check';
            favoriteButton.dataset.originalTitle = "Remove from saved training";
            //Add the current training to the favorited array.
            favoritedTrainingIDs.push(Number(card.dataset.trainingId));
            favoriteSection.insertAdjacentElement('afterbegin', card.parentElement.cloneNode(true));
          } else {
            delete card.dataset.checked;
            favoriteButton.classList.remove('checked', 'primary');
            favoriteButton.firstElementChild.innerText = 'add';
            favoriteButton.dataset.originalTitle = "Save for later";
            //Remove the current training from the favorited array.
            favoritedTrainingIDs = favoritedTrainingIDs.filter(function (ele) { return ele != Number(card.dataset.trainingId); });
            favoriteSection.querySelector('[data-training-id="'+ card.dataset.trainingId + '"').parentElement.remove();
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

  document.addEventListener('trainingResults', () => {
    document.getElementsByClassName(CardTraining.className).forEach(CardTraining.getOrWrap);
  });

  return { CardTraining };
})();
