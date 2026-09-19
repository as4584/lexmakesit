/* ============================================================
   LEXMAKESIT — CONTACT FORM
   Posts to the existing /api/contact endpoint.

   The endpoint is rate limited to 5/hour per client, so the most
   likely failure a real visitor sees is a 429 rather than a
   validation error. Both are reported in plain language instead of
   a status code, and the form never silently swallows a failure —
   if the message did not send, it says so and keeps what was typed.
   ============================================================ */
(function () {
  'use strict';

  var form = document.getElementById('contact-form');
  if (!form) return;

  /* ----------------------------------------------------------
     Browser-side throttle.

     This is the first of three layers, and the weakest by design:
     anyone can bypass it with curl. Its job is not security, it is
     to stop an ordinary visitor double-submitting or hammering the
     button and burning the server's 5/hour allowance on duplicates.
     The real enforcement is the per-client limit on the server, and
     a Cloudflare rule at the edge.

     The timestamp lives in localStorage so a page refresh does not
     reset it, and every access is guarded because storage throws in
     private windows.
     ---------------------------------------------------------- */
  var COOLDOWN_MS = 45000;
  var STORE_KEY = 'lex:contact:last';

  function lastSentAt() {
    try {
      var raw = window.localStorage.getItem(STORE_KEY);
      return raw ? parseInt(raw, 10) || 0 : 0;
    } catch (err) { return 0; }
  }

  function markSent() {
    try { window.localStorage.setItem(STORE_KEY, String(Date.now())); }
    catch (err) { /* private mode: fall back to the in-page guard */ }
  }

  var inFlight = false;

  var statusEl = document.getElementById('cf-status');
  var submit = document.getElementById('cf-submit');
  var label = submit ? submit.querySelector('.btn__label') : null;
  var original = label ? label.textContent : 'Send message';

  function setStatus(message, state) {
    statusEl.textContent = message;
    statusEl.dataset.state = state;
    statusEl.hidden = false;
  }

  function clearErrors() {
    form.querySelectorAll('.field__error').forEach(function (el) { el.textContent = ''; });
    form.querySelectorAll('[aria-invalid]').forEach(function (el) {
      el.removeAttribute('aria-invalid');
    });
  }

  function showError(id, message) {
    var target = form.querySelector('.field__error[data-for="' + id + '"]');
    if (target) target.textContent = message;
    var input = document.getElementById(id);
    if (input) input.setAttribute('aria-invalid', 'true');
    return input;
  }

  // Validate here so the visitor is not spending one of five hourly
  // attempts on a typo.
  function validate(data) {
    var problems = [];
    if (!data.name || data.name.trim().length < 2) {
      problems.push(['cf-name', 'Please give a name of at least 2 characters.']);
    }
    if (!data.email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(data.email)) {
      problems.push(['cf-email', 'Please enter an email address I can reply to.']);
    }
    if (!data.message || data.message.trim().length < 10) {
      problems.push(['cf-message', 'A sentence or two about what you need, please.']);
    }
    return problems;
  }

  form.addEventListener('submit', function (event) {
    event.preventDefault();
    clearErrors();

    if (inFlight) return;

    var waited = Date.now() - lastSentAt();
    if (waited < COOLDOWN_MS) {
      var seconds = Math.ceil((COOLDOWN_MS - waited) / 1000);
      setStatus(
        'Just sent one. Give it ' + seconds + ' second' + (seconds === 1 ? '' : 's') +
        ' before sending another — or email as42519256@gmail.com if it is urgent.',
        'error'
      );
      return;
    }

    var data = {
      name: form.elements.name.value,
      email: form.elements.email.value,
      subject: form.elements.subject.value || undefined,
      message: form.elements.message.value
    };

    var problems = validate(data);
    if (problems.length) {
      var first = null;
      problems.forEach(function (p) {
        var el = showError(p[0], p[1]);
        if (!first) first = el;
      });
      setStatus('Please fix the fields marked above.', 'error');
      if (first) first.focus();
      return;
    }

    if (!data.subject) delete data.subject;

    inFlight = true;
    submit.disabled = true;
    if (label) label.textContent = 'Sending…';
    setStatus('Sending…', 'busy');

    fetch('/api/contact', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    }).then(function (response) {
      if (response.ok) {
        markSent();
        form.reset();
        setStatus('Message sent. I read everything that comes through here and will reply to the address you gave.', 'ok');
        return;
      }
      if (response.status === 429) {
        setStatus('That is a lot of messages in a short time. Please try again later, or email me directly at as42519256@gmail.com.', 'error');
        return;
      }
      if (response.status === 503) {
        // The server accepted the request but could not deliver it. It
        // says so rather than pretending, so pass that on truthfully.
        setStatus('The message could not be delivered right now. Please email as42519256@gmail.com directly so it is not lost — your text is still here to copy.', 'error');
        return;
      }
      if (response.status === 422) {
        setStatus('One of the fields was rejected. Check the email address and try again.', 'error');
        return;
      }
      setStatus('The message did not send (error ' + response.status + '). Your text is still here — please try again, or email as42519256@gmail.com.', 'error');
    }).catch(function () {
      setStatus('Could not reach the server. Check your connection, or email as42519256@gmail.com directly.', 'error');
    }).then(function () {
      inFlight = false;
      submit.disabled = false;
      if (label) label.textContent = original;
    });
  });
})();
