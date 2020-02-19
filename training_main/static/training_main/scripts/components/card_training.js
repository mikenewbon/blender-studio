class CardTraining {
    constructor(element) {
        this.element = element;
        this.favoriteUrl = element.dataset.favoriteUrl;
        this.favoriteElement = this.element.getElementsByClassName('card-training-favorite')[0];
        this._setupEventListeners();
    }

    _setupEventListeners() {
        this.favoriteElement.addEventListener('click', this._favoriteClicked.bind(this));
    }

    _favoriteClicked() {
        jsonRequest(
            'POST',
            this.favoriteUrl,
            {
                'favorite': !Boolean(this.favoriteElement.dataset.checked)
            }
        ).then((data) => {
            if (data['favorite']) {
                this.favoriteElement.dataset.checked = "checked";
            } else {
                delete this.favoriteElement.dataset.checked;
            }
        })
    }
}

document.addEventListener('DOMContentLoaded', (event) => {
    for (let card of document.getElementsByClassName('card-training')) {
        new CardTraining(card)
    }
});
