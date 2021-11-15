/* eslint-disable no-undef, no-unused-vars, no-nested-ternary */
const searchClientConfig = JSON.parse(document.getElementById('search-client-config').textContent);
const filmTitle = JSON.parse(document.getElementById('film-title').textContent);

const indexName = 'studio_date_desc';
const search = instantsearch({
  indexName,
  searchClient: instantMeiliSearch(searchClientConfig.hostUrl, searchClientConfig.apiKey),
  routing: {
    stateMapping: {
      stateToRoute(uiState) {
        const indexUiState = uiState[indexName];
        return {
          query: indexUiState.query,
          sortBy: indexUiState && indexUiState.sortBy,
        };
      },
      routeToState(routeState) {
        return {
          [indexName]: {
            query: routeState.query,
            sortBy: routeState.sortBy,
          },
        };
      },
    },
  },
});

// -------- INPUT -------- //

// Create a render function
const renderSearchBox = (renderOptions, isFirstRender) => {
  const { query, refine, clear, isSearchStalled, widgetParams } = renderOptions;

  if (isFirstRender) {
    const input = document.createElement('input');
    input.setAttribute('class', 'form-control');
    input.setAttribute('type', 'text');
    input.setAttribute('id', 'searchInput');
    input.setAttribute('placeholder', 'Search tags and keywords');

    const append = document.createElement('div');
    append.setAttribute('class', 'input-group-append');
    const button = document.createElement('button');
    button.setAttribute('class', 'btn btn-icon btn-input');
    append.appendChild(button);
    const buttonIcon = document.createElement('i');
    buttonIcon.setAttribute('class', 'material-icons');
    buttonIcon.textContent = 'close';
    button.appendChild(buttonIcon);

    input.addEventListener('input', (event) => {
      refine(event.target.value);
    });

    button.addEventListener('click', () => {
      clear();
    });

    widgetParams.container
      .querySelector('.input-group-prepend')
      .insertAdjacentElement('afterend', input);
    input.insertAdjacentElement('afterend', append);
  }

  widgetParams.container.querySelector('input').value = query;
  // widgetParams.container.querySelector('span').hidden = !isSearchStalled;
};

// create custom widget
const customSearchBox = instantsearch.connectors.connectSearchBox(renderSearchBox);

// -------- SORTING -------- //

// Create the render function
const renderSortBy = (renderOptions, isFirstRender) => {
  const { options, currentRefinement, hasNoResults, refine, widgetParams } = renderOptions;

  if (isFirstRender) {
    const select = document.createElement('select');
    select.setAttribute('class', 'custom-select');

    select.addEventListener('change', (event) => {
      refine(event.target.value);
    });

    widgetParams.container
      .querySelector('.input-group-prepend')
      .insertAdjacentElement('afterend', select);
  }

  const select = widgetParams.container.querySelector('select');

  select.disabled = hasNoResults;

  select.innerHTML = `
    ${options
      .map(
        (option) => `
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
          (item) =>
            `
              <div class="col-12 col-sm-6 col-lg-4 file grid-item">

                  <div class="file-header">
                    <a class="file-header-link" href="${item.url}" aria-label="${item.name}">
                      <img src="${item.thumbnail_url || fileIconURL}" class="${
              item.thumbnail_url ? 'card-img' : 'file-icon'
            }" loading=lazy aria-label="${item.name}">
                    </a>
                  </div>
                  <a href="${item.url}" class="file-body">


                  <span data-tooltip="tooltip-overflow" data-placement="top" title="${
                    item.name
                  }" class="overflow-text">
                    <p class="overflow-text h4">${instantsearch.highlight({
                      attribute: 'name',
                      hit: item,
                    })}</p>
                  </span>
                  </a>
                  <a href="${item.url}" class="file-footer">
                    <div class="card-subtitle-group">
                      <p class="card-subtitle x-small">
                        <i class="material-icons icon-inline x-small">schedule</i>&nbsp;
                        ${timeDifference(epochToDate(item.timestamp))}
                      </p>
                      ${
                        item.is_free
                          ? `
                        <p class="d-inline mr-2 text-success x-small"><i class="material-icons icon-inline x-small" >lock_open</i>&nbsp;Free</p>
                      `
                          : ''
                      }
                    </div>
                  </a>
                </div>

            `
        )
        .join('')}
  `;

  lastRenderArgs = renderOptions;

  if (isFirstRender) {
    const sentinel = document.createElement('div');
    widgetParams.container.insertAdjacentElement('afterend', sentinel);

    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting && !lastRenderArgs.isLastPage) {
          showMore();
        }
      });
    });

    observer.observe(sentinel);

    return;
  }

  $(() => {
    $('[data-toggle="tooltip"]').tooltip();
  });
};

const customHits = instantsearch.connectors.connectInfiniteHits(renderHits);

// -------- CONFIGURE -------- //

const renderConfigure = (renderOptions, isFirstRender) => {};

const customConfigure = instantsearch.connectors.connectConfigure(renderConfigure, () => {});

// -------- RENDER -------- //

search.addWidgets([
  customSearchBox({
    container: document.querySelector('#search-container'),
  }),
  customHits({
    container: document.querySelector('#hits'),
  }),
  customSortBy({
    container: document.querySelector('#sorting'),
    items: [
      { label: 'Relevance', value: 'studio' },
      { label: 'Date (new first)', value: 'studio_date_desc' },
      { label: 'Date (old first)', value: 'studio_date_asc' },
    ],
  }),
  customConfigure({
    container: document.querySelector('#hits'),
    searchParameters: {
      film_title: filmTitle,
      hitsPerPage: 12,
      disjunctiveFacetsRefinements: {
        film_title: [filmTitle.film],
        model: ['asset'],
      },
    },
  }),
]);

search.start();

document.addEventListener('DOMContentLoaded', () => {
  document.querySelector('#searchInput').focus();
});
