window.ajax = (function ajax() {
  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i += 1) {
        const cookie = cookies[i].trim();
        // Does this cookie string begin with the name we want?
        if (cookie.substring(0, name.length + 1) === `${name}=`) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  const csrfToken = getCookie('csrftoken');

  function jsonRequest(method, url, data = null) {
    return fetch(url, {
      method: 'POST',
      mode: 'same-origin',
      cache: 'no-cache',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      },
      body: data == null ? null : JSON.stringify(data)
    })
      .then(response => {
        if (response.status >= 200 && response.status < 300) {
          return Promise.resolve(response);
        }
        return Promise.reject(new Error(response.statusText));
      })
      .then(response => response.json());
  }

  return { jsonRequest };
})();
