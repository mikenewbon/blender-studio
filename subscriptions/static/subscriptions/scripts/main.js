function AddRemoveText(element) {
  const el = element;
  if (el.innerText === 'Add') {
    el.innerText = 'Remove';
  } else if (el.innerText === 'Remove') {
    el.innerText = 'Add';
  }
}

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.add-remove').forEach((element) => {
    element.parentElement.addEventListener('click', () => {
      AddRemoveText(element);
    });
  });

  // When hiding collapsed inputs, empty them.
  document.querySelectorAll('.collapse').forEach((element) => {
    element.addEventListener('hidden.bs.collapse', (e) => {
      e.target.querySelectorAll('input').forEach((input) => {
        // eslint-disable-next-line no-param-reassign
        input.value = '';
      });
    });
  });
});

document.addEventListener('DOMContentLoaded', () => {
  const selectPlan = document.querySelector('.select-plan');
  const selectPlanVariation = document.querySelector('.select-plan-variation');

  // Plan variation details that are rerendered each time selection changes:
  const priceEl = document.querySelector('.x-price');
  const priceTaxEl = document.querySelector('.x-price-tax');
  const renewalPeriodEl = document.querySelector('.x-price-period');
  const teamSeatsEl = document.querySelector('.x-team-seats');
  const priceInput = document.getElementById('id_price');
  const signInLink = document.querySelector('.x-sign-in');

  function getSelectedPlan() {
    return selectPlan.options[selectPlan.selectedIndex];
  }

  function getSelectedPlanVariation() {
    return selectPlanVariation.options[selectPlanVariation.selectedIndex];
  }

  function isInvalidOptionSelected() {
    const selectedPlanOption = getSelectedPlan();
    const selectedPlanId = selectedPlanOption.value;
    const selectedOption = getSelectedPlanVariation();
    return selectedOption.dataset.planId !== selectedPlanId;
  }

  function formatPriceAmount(amount, currencySymbol) {
    return `${currencySymbol} ${amount}`;
  }

  function formatTaxAmount(option, amount) {
    const data = option.dataset;
    if (data.taxDisplayName) {
      const formattedAmount = formatPriceAmount(amount, data.currencySymbol);
      return `Inc.\xa0${data.taxRate}%\xa0${data.taxDisplayName}\xa0(${formattedAmount})`;
    } else {
      return '';
    }
  }

  function updatePlanVariationDetails() {
    if (isInvalidOptionSelected()) {
      // console.error('Invalid option selected');
      return;
    }
    const selectedOption = getSelectedPlanVariation();
    const { currencySymbol, renewalPeriod, nextUrl, teamSeats } = selectedOption.dataset;
    const { price, priceTax } = selectedOption.dataset;

    // Display the amounts with the tax details:
    priceEl.innerText = formatPriceAmount(price, currencySymbol);

    priceTaxEl.innerText = formatTaxAmount(selectedOption, priceTax);
    renewalPeriodEl.innerText = renewalPeriod;
    teamSeatsEl.innerText = teamSeats;

    // Update SignIn button's "next" so that selection remains the same after sign in
    if (signInLink && nextUrl) {
      const url = new URL(signInLink.href);
      signInLink.href = signInLink.href.replace(url.search, '');
      signInLink.href = `${signInLink.href}?next=${nextUrl}`;
    }

    // priceInput is only available when user is logged in, it is part of payment form.
    if (priceInput) {
      priceInput.value = price;
    }
    // TODO(anna): dataset should have next automatic charge date
  }

  function showOption(element) {
    const el = element;
    el.disabled = false;
    el.hidden = false;
    el.setAttribute('aria-disabled', 'false');
    el.display = 'inline-block';
  }

  function hideOption(element) {
    const el = element;
    el.disabled = true;
    el.hidden = true;
    el.setAttribute('aria-disabled', 'true');
    el.display = 'none';
  }

  function showPlanVariationOptions() {
    const selectedPlanOption = getSelectedPlan();
    const selectedPlanId = selectedPlanOption.value;
    const { options } = selectPlanVariation;
    let firstValidOption = null;
    for (let i = 0; i < options.length; i += 1) {
      const el = options[i];
      if (el.dataset.planId === selectedPlanId) {
        showOption(el);
        if (!firstValidOption) {
          firstValidOption = el;
        }
      } else {
        hideOption(el);
      }
    }
    // Change the selection to some valid option
    selectPlanVariation.value = firstValidOption.value;
    // Trigger the change event, because selected option has changed
    selectPlanVariation.dispatchEvent(new Event('change'));
  }

  if (!selectPlan) {
    // Skip all event handlers unless the expected elements exist on the page.
    return;
  }

  // Show/hide options linked to selected collection method (plan)
  selectPlan.addEventListener('change', showPlanVariationOptions);

  // Updated detailsi when selection changes
  selectPlanVariation.addEventListener('change', updatePlanVariationDetails);
});
