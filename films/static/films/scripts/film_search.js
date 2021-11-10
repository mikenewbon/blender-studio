/* eslint-disable no-undef, no-unused-vars, no-nested-ternary */
const searchClientConfig = JSON.parse(document.getElementById('search-client-config').textContent);
const filmTitle = JSON.parse(document.getElementById('film-title').textContent);

const search = instantsearch({
  indexName: 'studio_date_desc',
  searchClient: instantMeiliSearch(searchClientConfig.hostUrl, searchClientConfig.apiKey),
  routing: false,
});

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
                    ${item.is_free ? `
                      <i class="material-icons icon-inline small text-success mr-1" data-toggle="tooltip" data-placement="top" title="Free">lock_open</i>
                    ` : ''}

                  <span data-tooltip="tooltip-overflow" data-placement="top" title="${item.name}" class="overflow-text">
                    <p class="overflow-text h4">${instantsearch.highlight({ attribute: 'name', hit: item })}</p>
                  </span>
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
  customHits({
    container: document.querySelector('#hits'),
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
