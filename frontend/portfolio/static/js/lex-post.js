/* One post. The body is stored as plain text with blank-line paragraphs;
   it is escaped and then split, never injected as HTML, so a post can
   never introduce markup into the page. */
(function () {
  'use strict';
  var mount = document.getElementById('post');
  if (!mount) return;

  var slug = decodeURIComponent(location.pathname.replace(/^\/blog\//, '').replace(/\/$/, ''));
  if (!slug) { location.href = '/blog'; return; }

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

  fetch('/api/posts/' + encodeURIComponent(slug), { credentials: 'same-origin' })
    .then(function (r) {
      if (r.status === 404) throw new Error('not found');
      return r.json();
    })
    .then(function (post) {
      document.title = post.title + ' | Lexmakesit';
      var paragraphs = esc(post.body).split(/\n\s*\n/).map(function (block) {
        return '<p class="case-p">' + block.replace(/\n/g, '<br />') + '</p>';
      }).join('');
      mount.innerHTML =
        (post.published ? '' : '<p class="case-hero__kicker">Draft &mdash; not public</p>') +
        '<h1 class="case-hero__title" style="font-size:clamp(30px,4vw,60px)">' + esc(post.title) + '</h1>' +
        '<p class="case-hero__kicker">' + esc(when(post.created_at)) + '</p>' +
        '<div class="case__measure" style="margin-top:clamp(18px,2.2vw,32px)">' + paragraphs + '</div>';
    })
    .catch(function () {
      mount.innerHTML =
        '<h1 class="case-hero__title" style="font-size:clamp(30px,4vw,60px)">Not found.</h1>' +
        '<p class="case-hero__standfirst">That post does not exist, or is not published yet.</p>' +
        '<a class="btn btn--acid" href="/blog"><span class="btn__label">All posts</span></a>';
    });
})();
