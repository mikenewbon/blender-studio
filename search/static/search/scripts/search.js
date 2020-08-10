const search = instantsearch({
  indexName: "studio",
  searchClient: instantMeiliSearch(
    "http://0.0.0.0:7700",
    //  TODO(Nat): api key goes here
  )
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

    //const loadingIndicator = document.createElement('span');
    //loadingIndicator.textContent = 'Loading...';

    const button = document.createElement('button');
    button.setAttribute('class', 'btn btn-icon btn-input');
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

    widgetParams.container.querySelector('.input-group-append').insertAdjacentElement('beforebegin', input);
    //widgetParams.container.appendChild(loadingIndicator);
    widgetParams.container.querySelector('.input-group-append').appendChild(button);
  }

  widgetParams.container.querySelector('input').value = query;
  //widgetParams.container.querySelector('span').hidden = !isSearchStalled;
};

// create custom widget
const customSearchBox = instantsearch.connectors.connectSearchBox(
  renderSearchBox
);


// -------- HITS -------- //

// Create the render function
const renderHits = (renderOptions, isFirstRender) => {
  const { hits, widgetParams } = renderOptions;
  widgetParams.container.innerHTML = `

      ${hits
      .map(
        item =>
          `
          <div class="col-12 col-sm-6 col-lg-4 card-grid-item">
            <div class="card card-dark card-hover card-media">
              <div class="card-header">
                <a class="card-header-link" href="">
                  <img src="${ item.thumbnail_url }" class="card-image">
                </a>
              </div>
              <a href="" class="card-body">
                <div class="card-subtitle-group">
                  <p class="card-subtitle content-type">
                  ${instantsearch.highlight({ attribute: 'model', hit: item })}
                  </p>

                  <p class="card-subtitle">
                    <i class="material-icons icon-inline x-small">schedule</i>
                    ${instantsearch.highlight({ attribute: 'date_created', hit: item })}
                  </p>

                </div>
                <h3 class="card-title">
                  ${instantsearch.highlight({ attribute: 'name', hit: item })}
                </h3>
                <p class="card-text">
                  ${instantsearch.highlight({ attribute: 'description', hit: item })}
                </p>
              </a>
            </div>
          </div>
            `
      )
      .join('')}

  `;
};


const customHits = instantsearch.connectors.connectHits(renderHits);


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

    widgetParams.container.querySelector('.input-group-prepend').insertAdjacentElement('afterend', select);
    // widgetParams.container.appendChild(select);
  }

  const select = widgetParams.container.querySelector('select');

  select.disabled = !canRefine;

  select.innerHTML = `
    <option value="">See all</option>
    ${items
      .map(
        item =>
          `<option
            value="${item.value}"
            ${item.isRefined ? 'selected' : ''}
          >
            ${item.label}
          </option>`
      )
      .join('')}
  `;
};

// 2. Create the custom widget
const customMenuSelect = instantsearch.connectors.connectMenu(renderMenuSelect);


// -------- RENDER -------- //

search.addWidgets([
  customSearchBox({
    container: document.querySelector('#search-container'),
  }),
  customHits({
    container: document.querySelector('#hits'),
  }),
  // customMenu({
  //   container: document.querySelector('#filters'),
  //   attribute: 'categories',
  //   showMoreLimit: 20,
  // }),
  customMenuSelect({
    container: document.querySelector('#searchType'),
    attribute: 'model',
  })
]);

search.start();
