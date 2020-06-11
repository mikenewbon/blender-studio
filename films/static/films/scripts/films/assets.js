
// TODO(Natalia): Figure out what to assign it to (window.asset??) And how to execute this?

window.asset = (function asset() {
    class Asset {
        constructor(element) {
            this.id = element.dataset.assetId;
            this.element = element;
            this._setUpEventListeners();
        }

        get collection() {
            return this.element.querySelector('drawer-nav-section-link')
        }

        _setUpEventListeners() {
            this.collection.addEventListener('click', event => {
                console.log('whoops');
            });
        }
    }
})();

// console.log('asdf')
