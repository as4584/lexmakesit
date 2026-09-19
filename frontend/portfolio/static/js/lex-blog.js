/* Blog index. Posts come from /api/posts; drafts appear only when an
   admin session cookie is present, and are labelled as drafts. */
(function () {
  'use strict';
  var mount = document.getElementById('post-list');
  if (!mount) return;

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[c];
    });
  }

  function when(iso) {
    try {
      return new Intl.DateTimeFormat(undefined, {
        year: 'numeric', month: 'long', day: 'numeric'
      }).format(new Date(iso));
    } catch (err) { return ''; }
  }

  fetch('/api/posts', { credentials: 'same-origin' })
    .then(function (r) { return r.ok ? r.json() : { posts: [] }; })
    .then(function (data) {
      var posts = data.posts || [];
      if (!posts.length) {
        mount.innerHTML =
          '<p class="case-p">Nothing published yet. When there are notes worth ' +
          'reading, they will show up here.</p>' +
          '<a class="btn btn--acid" href="/#work"><span class="btn__label">' +
          'See the work instead</span><span class="btn__arrow" aria-hidden="true">&rarr;</span></a>';
        return;
      }
      mount.innerHTML = '<ul class="post-list" role="list">' + posts.map(function (p) {
        return '<li><a class="post-card" href="/blog/' + encodeURIComponent(p.slug) + '">' +
          (p.published ? '' : '<span class="post-card__draft">Draft</span>') +
          '<h2 class="post-card__title">' + esc(p.title) + '</h2>' +
          (p.summary ? '<p class="post-card__summary">' + esc(p.summary) + '</p>' : '') +
          '<p class="post-card__date">' + esc(when(p.created_at)) + '</p>' +
          '</a></li>';
      }).join('') + '</ul>';
    })
    .catch(function () {
      mount.innerHTML = '<p class="case-p">Could not load posts right now.</p>';
    });
})();
