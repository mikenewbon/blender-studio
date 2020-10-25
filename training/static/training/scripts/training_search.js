
const searchClientConfig = JSON.parse(
  document.getElementById('training-search-client-config').textContent
);
var favoritedTrainingIDs = JSON.parse(
  document.getElementById('training-favorited-ids').textContent
);
const search = instantsearch({
  indexName: "training_date_desc",
  searchClient: instantMeiliSearch(searchClientConfig.hostUrl, searchClientConfig.apiKey)
});


// -------- INPUT -------- //

// Create a render function
const renderSearchBox = (renderOptions, isFirstRender) => {
  const {
    query,
    refine,
    clear,
    isSearchStalled,
    widgetParams
  } = renderOptions;

  if (isFirstRender) {
    const input = document.createElement('input');
    input.setAttribute('class', 'form-control');
    input.setAttribute('type', 'text')
    input.setAttribute('placeholder', 'Search tags and keywords')

    const append = document.createElement('div');
    append.setAttribute('class', 'input-group-append');
    const button = document.createElement('button');
    button.setAttribute('class', 'btn btn-icon btn-input');
    append.appendChild(button);
    const buttonIcon = document.createElement('i');
    buttonIcon.setAttribute('class', 'material-icons');
    buttonIcon.textContent = 'close';
    button.appendChild(buttonIcon);

    input.addEventListener('input', event => {
      refine(event.target.value);
    });

    button.addEventListener('click', () => {
      clear();
    });

    widgetParams.container.querySelector('.input-group-prepend').insertAdjacentElement('afterend', input);
    input.insertAdjacentElement('afterend', append);
  }

  widgetParams.container.querySelector('input').value = query;
  //widgetParams.container.querySelector('span').hidden = !isSearchStalled;
};

// create custom widget
const customSearchBox = instantsearch.connectors.connectSearchBox(
  renderSearchBox
);

// -------- SORTING -------- //

// Create the render function
const renderSortBy = (renderOptions, isFirstRender) => {
  const {
    options,
    currentRefinement,
    hasNoResults,
    refine,
    widgetParams,
  } = renderOptions;

  if (isFirstRender) {
    const select = document.createElement('select');
    select.setAttribute('class', 'custom-select');

    select.addEventListener('change', event => {
      refine(event.target.value);
    });

    widgetParams.container.querySelector('.input-group-prepend').insertAdjacentElement('afterend', select);
  }

  const select = widgetParams.container.querySelector('select');

  select.disabled = hasNoResults;

  select.innerHTML = `
    ${options
      .map(
        option => `
          <option
            value="${option.value}"
            ${option.value === currentRefinement ? 'selected' : ''}
          >
            ${option.label}
          </option>
        `
      )
      .join('')}
  `;
};

// Create the custom widget
const customSortBy = instantsearch.connectors.connectSortBy(renderSortBy);

// -------- HITS -------- //

let lastRenderArgs;

// Create the render function
const renderHits = (renderOptions, isFirstRender) => {
  const { hits, showMore, widgetParams } = renderOptions;

  widgetParams.container.innerHTML = `
      ${hits
      .map(
        item =>
        `
          <div class="col-12 col-sm-6 col-lg-4 card-grid-item">

            <div class="card card-dark card-training card-media card-hover" data-training-id="${ item.id }" data-favorite-url="${ item.favorite_url }" ${ favoritedTrainingIDs.filter(i => i == item.id).length > 0 == true ? 'data-checked="checked"' : ''}>
              <div class="card-header" style='background-image: url("${ item.thumbnail_url }")'>
                <a href="${ item.url }" class="card-header-link"></a>
                ${ authCheck() == true ?
                `<button class="btn btn-xs btn-icon btn-float checkbox-favorite btn-save-media card-training-favorite ${ favoritedTrainingIDs.filter(i => i == item.id).length > 0 == true ? 'checked primary' : ''}" data-toggle="tooltip" data-placement="left" title="Save for later">
                  <i class="material-icons checkbox-favorite-icon-unchecked">${ favoritedTrainingIDs.filter(i => i == item.id).length > 0 == true ? 'check' : 'add'}</i>
                </button>` : ''
                }
              </div>

              <a class="card-body" href="${ item.url }">
                <div class="card-subtitle-group">
                  <p class="card-subtitle">${ titleCase(item.type) }</p>
                  <p class="card-subtitle">
                  ${ !!(item.difficulty) ? `
                    <i class="material-icons icon-inline small">school</i>
                    ${ titleCase(item.difficulty) }` : ''}
                  </p>
                </div>
                <h3 class="card-title">${instantsearch.highlight({ attribute: 'name', hit: item })}</h3>
                <p class="card-text">${instantsearch.highlight({ attribute: 'description', hit: item })}</p>
              </a>

              ${ item.tags != '' ? `<div class="card-footer">
                <div class="pills">
                  ${item.tags.map( tag => `
                  <p class="badge badge-pill">${titleCase(tag)}</p>
                  `).join('')}
                </div>
              </div>` : ''}

            </div>
          </div>
        `
      )
      .join('')}
  `;

  lastRenderArgs = renderOptions;

  if (isFirstRender) {
    const sentinel = document.createElement('div');
    widgetParams.container.insertAdjacentElement('afterend', sentinel);

    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting && !lastRenderArgs.isLastPage) {
          showMore();
        }
      });
    });

    observer.observe(sentinel);

    return;
  }

  // On search is dispatches this event to setup the training cards (event listeners etc)
  document.dispatchEvent(new Event('trainingResults'));
};


const customHits = instantsearch.connectors.connectInfiniteHits(renderHits);


// -------- FILTERS -------- //

// 1. Create a render function
const renderMenuSelect = (renderOptions, isFirstRender) => {
  const { items, canRefine, refine, widgetParams } = renderOptions;

  if (isFirstRender) {
    const select = document.createElement('select');

    select.setAttribute('class', 'custom-select');
    select.addEventListener('change', event => {
      refine(event.target.value);
    });

    widgetParams.container.insertAdjacentElement('beforeend', select);
    // widgetParams.container.appendChild(select);
  }

  const select = widgetParams.container.querySelector('select');

  select.disabled = !canRefine;

  select.innerHTML = `
    <option value="">${widgetParams.placeholder}</option>
    ${items
      .map(
        item =>
          `<option
            value="${item.value}"
            ${item.isRefined ? 'selected' : ''}
          >
            ${titleCase(item.label)}
          </option>`
      )
      .join('')}
  `;
};

// 2. Create the custom widget
const customMenuSelect = instantsearch.connectors.connectMenu(renderMenuSelect);


// -------- CONFIGURE -------- //

const renderConfigure = (renderOptions, isFirstRender) => {};

const customConfigure = instantsearch.connectors.connectConfigure(
  renderConfigure,
  () => {}
);


// -------- RENDER -------- //

search.addWidgets([
  customSearchBox({
    container: document.querySelector('#search_input'),
  }),
  customHits({
    container: document.querySelector('#hits'),
  }),
  customMenuSelect({
    container: document.querySelector('#search_type'),
    attribute: 'type',
    placeholder: 'All Types',
  }),
  customMenuSelect({
    container: document.querySelector('#search_difficulty'),
    attribute: 'difficulty',
    placeholder: 'All Difficulties',
  }),
  customSortBy({
    container: document.querySelector('#sorting'),
    items: [
      // { label: 'Relevance', value: 'training' },
      { label: 'Date (new first)', value: 'training_date_desc' },
      { label: 'Date (old first)', value: 'training_date_asc' },
    ],
  }),

]);

search.start();

