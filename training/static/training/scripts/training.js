/* global ajax:false bootstrap */

function postFavorite(element) {
  const button = element;
  const iconElement = button.querySelector('i');
  const textElement = button.querySelector('span');

  ajax
    .jsonRequest('POST', button.dataset.favoriteUrl, {
      favorite: !button.dataset.checked,
    })
    .then((data) => {
      const tooltip = bootstrap.Tooltip.getInstance(element);
      if (data.favorite) {
        button.dataset.checked = 'checked';
        button.classList.add('btn-primary');
        button.classList.remove('btn-dark');
        iconElement.innerText = 'check';
        textElement.innerText = 'Saved';
        button.dataset.bsOriginalTitle = 'Remove from saved training';
        tooltip.update();
      } else {
        delete button.dataset.checked;
        button.classList.add('btn-dark');
        button.classList.remove('btn-primary');
        iconElement.innerText = 'add';
        textElement.innerText = 'Save';
        button.dataset.bsOriginalTitle = 'Save for later';
        tooltip.update();
      }
    });
}

document.addEventListener('DOMContentLoaded', () => {
  const saveButton = document.querySelector('.save-button');
  if (saveButton) {
    saveButton.addEventListener('click', (e) => {
      postFavorite(e.currentTarget);
    });
  }
});
