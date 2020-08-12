function EpochToDate(epoch) {
  if (epoch < 10000000000)
      epoch *= 1000; // convert to milliseconds (Epoch is usually expressed in seconds, but Javascript uses Milliseconds)
  var epoch = epoch + (new Date().getTimezoneOffset() * -1); //for timeZone
  return new Date(epoch);
}

function timeDifference(datetime) {

  //Timestamps are provided in the search as EPOCH timestamps - so need to be converted.
  datetime = EpochToDate(datetime);

  let now = new Date();

  const msPerMinute = 60 * 1000;
  const msPerHour = msPerMinute * 60;
  const msPerDay = msPerHour * 24;
  const msPerMonth = msPerDay * 30;
  const msPerYear = msPerDay * 365;

  let elapsed = now - datetime;

  if (elapsed < msPerMinute) {
       return Math.round(elapsed/1000) + ' seconds ago';
  }

  else if (elapsed < msPerHour) {
       return Math.round(elapsed/msPerMinute) + ' minutes ago';
  }

  else if (elapsed < msPerDay ) {
       return Math.round(elapsed/msPerHour ) + ' hours ago';
  }

  else if (elapsed < msPerMonth) {
      return  Math.round(elapsed/msPerDay) + ' days ago';
  }

  else if (elapsed < msPerYear) {
      return  Math.round(elapsed/msPerMonth) + ' months ago';
  }

  else {
      return Math.round(elapsed/msPerYear ) + ' years ago';
  }
}
