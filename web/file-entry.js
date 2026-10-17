// The studio needs its local server for voices, settings and audio processing.
if (window.location.protocol === 'file:') {
  window.location.replace('http://127.0.0.1:7865/');
}
