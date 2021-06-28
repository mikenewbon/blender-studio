document.addEventListener('DOMContentLoaded', () => {
  const regionsPerCountryEl = document.getElementById('country-regions');
  if (!regionsPerCountryEl) {
    // Nothing to do: no country selector on the page (e.g. not logged in yet)
    return;
  }
  const regionsPerCountry = JSON.parse(regionsPerCountryEl.textContent);
  const countrySelect = document.getElementById('id_country');
  const regionSelect = document.getElementById('id_region');
  const regionSelectContainer = regionSelect.parentElement;
  const regionLabel = document.querySelector('label[for="id_region"] span');

  function templateRegionSelect(regions) {
    return `
      <option value="" selected="">Select ${regions.type}</option>
      ${regions.choices
        .map((region, index) => `<option value="${region[0]}">${region[1]}</option>`)
        .join('')}
  `;
  }

  function updateRegionSelect() {
    const selectedCountryCode = countrySelect.value;

    if (regionsPerCountry[selectedCountryCode]) {
      const regions = regionsPerCountry[selectedCountryCode];
      if (regions.used_in_address) {
        // Update region choices accordindly
        regionSelect.innerHTML = templateRegionSelect(regions);
        regionLabel.innerText = regions.type;
        // Show the updated select
        regionSelectContainer.classList.remove('d-none');
        return;
      }
    }
    // Reset and hide the region select
    regionSelect.innerHTML = '';
    regionLabel.innerText = 'Region';
    regionSelectContainer.classList.add('d-none');
  }

  if (!!countrySelect && !!regionSelect && !!regionLabel) {
    // Update region select with choices appropriated for the selected country
    countrySelect.addEventListener('change', updateRegionSelect);
  }
});
