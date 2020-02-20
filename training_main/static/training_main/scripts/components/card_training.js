'use strict';
/* global ajax:false */

window.cardTraining = (function cardTraining() {
    class CardTraining {
        constructor(element) {
            this.element = element;
            this.favoriteUrl = element.dataset.favoriteUrl;
            [this.favoriteElement] = this.element.getElementsByClassName('card-training-favorite');
            this._setupEventListeners();
        }

        _setupEventListeners() {
            this.favoriteElement.addEventListener('click', this._favoriteClicked.bind(this));
        }

        _favoriteClicked() {
            ajax.jsonRequest(
                'POST',
                this.favoriteUrl,
                {
                    favorite: !this.favoriteElement.dataset.checked,
                },
            ).then((data) => {
                if (data.favorite) {
                    this.favoriteElement.dataset.checked = 'checked';
                } else {
                    delete this.favoriteElement.dataset.checked;
                }
            });
        }
    }

    document.addEventListener('DOMContentLoaded', () => {
        document.getElementsByClassName('card-training').forEach((card) => {
            // TODO(sem): How to store references to these JS Objects?
            new CardTraining(card); // eslint-disable-line no-new
        });
    });

    return {};
}());
