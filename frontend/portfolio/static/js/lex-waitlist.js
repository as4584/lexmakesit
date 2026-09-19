/* ============================================================
   LEXMAKESIT — WAITLIST
   Posts to /api/waitlist.

   An address already on the list is reported as success, because
   from the visitor's side it is: they are on the list. Telling them
   "duplicate" reads as an error and invites a second attempt.

   If the server cannot store the signup it says so rather than
   accepting an address that goes nowhere — the same rule the
   contact form follows.
   ============================================================ */
(function () {
  'use strict';

  var form = document.getElementById('waitlist-form');
  if (!form) return;

  var statusEl = document.getElementById('wl-status');
  var submit = document.getElementById('wl-submit');
  var input = document.getElementById('wl-email');
  var label = submit ? submit.querySelector('.btn__label') : null;
  var original = label ? label.textContent : 'Join the waitlist';
  var product = form.dataset.product || 'reseller';
  var inFlight = false;

  // Remember locally so a returning visitor is not asked twice.
  var STORE_KEY = 'lex:waitlist:' + product;

  function setStatus(message, state) {
    statusEl.textContent = message;
    statusEl.dataset.state = state;
    statusEl.hidden = false;
  }

  function alreadyJoined() {
    try { return window.localStorage.getItem(STORE_KEY) === '1'; }
    catch (err) { return false; }
  }

  function remember() {
    try { window.localStorage.setItem(STORE_KEY, '1'); }
    catch (err) { /* private mode: harmless, the server still dedupes */ }
  }

  if (alreadyJoined()) {
    setStatus("You're on the list already.", 'ok');
  }

  form.addEventListener('submit', function (event) {
    event.preventDefault();
    if (inFlight) return;

    var email = (input.value || '').trim();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setStatus('That does not look like an email address.', 'error');
      input.setAttribute('aria-invalid', 'true');
      input.focus();
      return;
    }
    input.removeAttribute('aria-invalid');

    inFlight = true;
    submit.disabled = true;
    if (label) label.textContent = 'Adding…';

    fetch('/api/waitlist', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: email, product: product })
    }).then(function (response) {
      return response.json().then(function (body) {
        return { ok: response.ok, status: response.status, body: body };
      });
    }).then(function (result) {
      if (result.ok) {
        remember();
        form.reset();
        setStatus(result.body.message || "You're on the list.", 'ok');
        return;
      }
      if (result.status === 429) {
        setStatus('Too many attempts just now. Try again in a little while.', 'error');
        return;
      }
      if (result.status === 503) {
        setStatus(result.body.message ||
          'The waitlist is not accepting signups right now. Email as42519256@gmail.com instead.', 'error');
        return;
      }
      setStatus('That did not go through. Please try again, or email as42519256@gmail.com.', 'error');
    }).catch(function () {
      setStatus('Could not reach the server. Check your connection and try again.', 'error');
    }).then(function () {
      inFlight = false;
      submit.disabled = false;
      if (label) label.textContent = original;
    });
  });
})();
