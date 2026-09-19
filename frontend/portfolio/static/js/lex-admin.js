/* Blog editor. One operator, one password, session in an httpOnly cookie.

   Everything rendered from stored data goes through esc(). The editor is
   the one place a post's own text is handled, so it must never build HTML
   out of it. */
(function () {
  'use strict';

  var mount = document.getElementById('admin-app');
  if (!mount) return;

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function say(message, state) {
    var el = document.getElementById('admin-status');
    if (!el) return;
    el.textContent = message;
    el.dataset.state = state || 'error';
    el.hidden = false;
  }

  function loginView() {
    mount.innerHTML =
      '<form class="contact-form" id="login-form" style="max-width:32rem;transform:none">' +
        '<h2 class="case-h2" style="color:var(--paper-ink);font-size:clamp(18px,1.7vw,24px)">Sign in</h2>' +
        '<div class="field">' +
          '<label for="admin-pw">Password</label>' +
          '<input id="admin-pw" type="password" autocomplete="current-password" required />' +
        '</div>' +
        '<button class="btn btn--acid" type="submit" style="width:100%">' +
          '<span class="btn__label">Sign in</span></button>' +
        '<p class="form-status" id="admin-status" role="status" aria-live="polite" hidden></p>' +
      '</form>';

    document.getElementById('login-form').addEventListener('submit', function (e) {
      e.preventDefault();
      var pw = document.getElementById('admin-pw').value;
      fetch('/api/admin/login', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password: pw })
      }).then(function (r) {
        if (r.ok) { editorView(); return; }
        if (r.status === 429) { say('Too many attempts. Wait a while before trying again.'); return; }
        say('Incorrect password.');
      }).catch(function () { say('Could not reach the server.'); });
    });
  }

  function editorView() {
    mount.innerHTML =
      '<div style="display:flex;gap:12px;flex-wrap:wrap;align-items:center;margin-bottom:clamp(14px,1.8vw,24px)">' +
        '<button class="btn btn--outline" id="new-post"><span class="btn__label">New post</span></button>' +
        '<button class="btn btn--outline" id="sign-out"><span class="btn__label">Sign out</span></button>' +
      '</div>' +
      '<div id="post-index" style="margin-bottom:clamp(16px,2vw,28px)"></div>' +
      '<form class="contact-form" id="post-form" style="transform:none">' +
        '<div class="field"><label for="p-title">Title</label>' +
          '<input id="p-title" required maxlength="140" /></div>' +
        '<div class="field"><label for="p-slug">Slug (the URL)</label>' +
          '<input id="p-slug" required maxlength="80" placeholder="what-broke-this-week" /></div>' +
        '<div class="field"><label for="p-summary">Summary (optional)</label>' +
          '<input id="p-summary" maxlength="240" /></div>' +
        '<div class="field"><label for="p-body">Post</label>' +
          '<textarea id="p-body" required style="min-height:18em"></textarea></div>' +
        '<label style="display:flex;gap:.5em;align-items:center;font-family:var(--font-body);color:var(--paper-ink);margin-bottom:1em">' +
          '<input type="checkbox" id="p-published" style="width:auto" /> Published' +
        '</label>' +
        '<div style="display:flex;gap:10px;flex-wrap:wrap">' +
          '<button class="btn btn--acid" type="submit"><span class="btn__label">Save</span></button>' +
          '<button class="btn btn--outline" type="button" id="p-delete"><span class="btn__label">Delete</span></button>' +
        '</div>' +
        '<p class="form-status" id="admin-status" role="status" aria-live="polite" hidden></p>' +
      '</form>';

    document.getElementById('sign-out').addEventListener('click', function () {
      fetch('/api/admin/logout', { method: 'POST', credentials: 'same-origin' }).then(loginView);
    });

    document.getElementById('new-post').addEventListener('click', function () {
      ['p-title', 'p-slug', 'p-summary', 'p-body'].forEach(function (id) {
        document.getElementById(id).value = '';
      });
      document.getElementById('p-published').checked = false;
      say('New post.', 'ok');
    });

    // The slug follows the title until it is edited by hand.
    var slugTouched = false;
    document.getElementById('p-slug').addEventListener('input', function () { slugTouched = true; });
    document.getElementById('p-title').addEventListener('input', function (e) {
      if (slugTouched) return;
      document.getElementById('p-slug').value = e.target.value
        .toLowerCase().replace(/[^a-z0-9\s-]/g, '').trim()
        .replace(/\s+/g, '-').slice(0, 80);
    });

    document.getElementById('post-form').addEventListener('submit', function (e) {
      e.preventDefault();
      var payload = {
        slug: document.getElementById('p-slug').value,
        title: document.getElementById('p-title').value,
        summary: document.getElementById('p-summary').value || null,
        body: document.getElementById('p-body').value,
        published: document.getElementById('p-published').checked
      };
      fetch('/api/posts', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      }).then(function (r) {
        if (r.ok) { say('Saved.', 'ok'); loadIndex(); return; }
        if (r.status === 401) { say('Session expired — sign in again.'); return; }
        if (r.status === 422) { say('Check the slug: lowercase letters, numbers and hyphens only.'); return; }
        say('Could not save (error ' + r.status + ').');
      }).catch(function () { say('Could not reach the server.'); });
    });

    document.getElementById('p-delete').addEventListener('click', function () {
      var slug = document.getElementById('p-slug').value;
      if (!slug) { say('Nothing selected to delete.'); return; }
      if (!window.confirm('Delete "' + slug + '"? This cannot be undone.')) return;
      fetch('/api/posts/' + encodeURIComponent(slug), {
        method: 'DELETE',
        credentials: 'same-origin'
      }).then(function (r) {
        if (r.ok) { say('Deleted.', 'ok'); loadIndex(); return; }
        say('Could not delete (error ' + r.status + ').');
      });
    });

    loadIndex();
  }

  function loadIndex() {
    var box = document.getElementById('post-index');
    if (!box) return;
    fetch('/api/posts', { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var posts = data.posts || [];
        if (!posts.length) { box.innerHTML = '<p class="case-p">No posts yet.</p>'; return; }
        box.innerHTML = '<ul class="post-list" role="list">' + posts.map(function (p) {
          return '<li><button class="post-card" type="button" data-slug="' + esc(p.slug) + '" ' +
            'style="width:100%;text-align:start;border:0;cursor:pointer">' +
            (p.published ? '' : '<span class="post-card__draft">Draft</span>') +
            '<h2 class="post-card__title">' + esc(p.title) + '</h2>' +
            '<p class="post-card__date">' + esc(p.slug) + '</p></button></li>';
        }).join('') + '</ul>';
        Array.prototype.forEach.call(box.querySelectorAll('[data-slug]'), function (btn) {
          btn.addEventListener('click', function () { loadPost(btn.dataset.slug); });
        });
      });
  }

  function loadPost(slug) {
    fetch('/api/posts/' + encodeURIComponent(slug), { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(function (p) {
        document.getElementById('p-title').value = p.title || '';
        document.getElementById('p-slug').value = p.slug || '';
        document.getElementById('p-summary').value = p.summary || '';
        document.getElementById('p-body').value = p.body || '';
        document.getElementById('p-published').checked = !!p.published;
        say('Loaded "' + p.slug + '".', 'ok');
      });
  }

  fetch('/api/admin/session', { credentials: 'same-origin' })
    .then(function (r) { return r.json(); })
    .then(function (d) { if (d.signed_in) { editorView(); } else { loginView(); } })
    .catch(loginView);
})();
