/* eslint-disable no-undef */
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
      if (this.favoriteElement) {
        this.favoriteElement.addEventListener('click', this._postFavorite.bind(this));
        // eslint-disable-next-line no-unused-vars
        const tooltip = new bootstrap.Tooltip(this.favoriteElement);
      }
    }

    _postFavorite() {
      const card = this.element;
      const favoriteButton = this.element.querySelector('.card-training-favorite');
      const favoriteSection = document.querySelector('#savedTraining');

      ajax
        .jsonRequest('POST', card.dataset.favoriteUrl, {
          favorite: !card.dataset.checked,
        })
        .then((data) => {
          if (data.favorite) {
            card.dataset.checked = 'checked';
            favoriteButton.classList.add('checked', 'primary');
            favoriteButton.firstElementChild.innerText = 'check';
            favoriteButton.dataset.originalTitle = 'Remove from saved training';
            // Add the current training to the favorited array.
            // eslint-disable-next-line no-undef
            favoritedTrainingIDs.push(Number(card.dataset.trainingId));

            // This adds the event listener to the new card
            document.dispatchEvent(new Event('trainingResults'));
          } else {
            delete card.dataset.checked;
            favoriteButton.classList.remove('checked', 'primary');
            favoriteButton.firstElementChild.innerText = 'add';
            favoriteButton.dataset.originalTitle = 'Save for later';
            // Remove the current training from the favorited array.
            favoritedTrainingIDs = favoritedTrainingIDs.filter(
              (ele) => ele !== Number(card.dataset.trainingId)
            );

            favoriteSection
              .querySelectorAll(`[data-training-id="${card.dataset.trainingId}"]`)
              .forEach((e) => {
                if (e.parentElement === e.parentElement.parentElement.firstElementChild) {
                  if (e.parentElement.parentElement.classList.contains('active')) {
                    e.parentElement.parentElement.remove();
                    if (favoriteSection.firstElementChild.firstElementChild) {
                      favoriteSection.firstElementChild.firstElementChild.classList.add('active');
                    } else {
                      favoriteSection.firstElementChild.innerHTML = `<div class="col text-center empty-saved-training">
                          <div class="bg-secondary py-4 rounded">
                            <h3 class="mb-0">No saved training</h3>
                            <p class="mb-0">You can favorite a few below!</p>
                          </div>
                        </div>`;
                      favoriteSection
                        .closest('section')
                        .querySelectorAll('.carousel-card-toolbar .btn')
                        .forEach((e) => {
                          e.classList.add('disabled');
                        });
                    }
                  } else {
                    e.parentElement.parentElement.remove();
                  }
                } else {
                  e.parentElement.remove();
                }

                if (favoriteSection.classList.contains('carousel-card-3')) {
                  if (favoriteSection.firstElementChild.childElementCount <= 1) {
                    favoriteSection
                      .closest('section')
                      .querySelectorAll('.carousel-card-toolbar .btn')
                      .forEach((e) => {
                        e.classList.add('onlyOne');
                      });
                  } else if (favoriteSection.firstElementChild.childElementCount <= 3) {
                    favoriteSection
                      .closest('section')
                      .querySelectorAll('.carousel-card-toolbar .btn')
                      .forEach((e) => {
                        e.classList.add('lessThanThree');
                      });
                  }
                } else if (favoriteSection.classList.contains('carousel-card-4')) {
                  if (favoriteSection.firstElementChild.childElementCount <= 1) {
                    favoriteSection
                      .closest('section')
                      .querySelectorAll('.carousel-card-toolbar .btn')
                      .forEach((e) => {
                        e.classList.add('onlyOne');
                      });
                  } else if (favoriteSection.firstElementChild.childElementCount <= 4) {
                    favoriteSection
                      .closest('section')
                      .querySelectorAll('.carousel-card-toolbar .btn')
                      .forEach((e) => {
                        e.classList.add('lessThanFour');
                      });
                  }
                }
              });

            if (favoriteSection.childElementCount === 0) {
              favoriteSection.innerHTML = `<div class="col text-center empty-saved-training">
                <div class="bg-secondary py-4 rounded">
                  <h3 class="mb-0">No saved training</h3>
                  <p class="mb-0">You can favorite a few below!</p>
                </div>
              </div>`;
            }

            // Remove tick and 'checked' data attribute from all duplicate cards.
            const similarCards = document.querySelectorAll(
              `[data-training-id="${card.dataset.trainingId}"]`
            );
            similarCards.forEach((element) => {
              const similarCardsFavorite = element.querySelector('.card-training-favorite');
              similarCardsFavorite.classList.remove('checked', 'primary');
              similarCardsFavorite.firstElementChild.innerText = 'add';
              similarCardsFavorite.dataset.originalTitle = 'Save for later';
              element.removeAttribute('data-checked');
            });
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
