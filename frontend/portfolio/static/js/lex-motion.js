/* ============================================================
   LEXMAKESIT - MOTION SYSTEM
   GSAP 3 + ScrollTrigger.

   Principles:
   - One choreographed entrance, not fifty independent fades.
   - Everything animated is transform or opacity (compositor only).
   - gsap.matchMedia() owns every breakpoint and the reduced-motion
     branch, so contexts revert cleanly instead of leaking.
   - The page is complete and usable if this file never loads.
   ============================================================ */
(function () {
  'use strict';

  var root = document.documentElement;

  // Nav / menu work with or without GSAP, so they are wired first.
  initMenu();
  initYear();

  if (!window.gsap) {
    // No animation library - reveal everything and stop.
    root.classList.remove('js-motion');
    return;
  }

  gsap.registerPlugin(ScrollTrigger);

  // Defaults keep the whole page on one motion vocabulary.
  gsap.defaults({ ease: 'power3.out', duration: 0.8 });

  var mm = gsap.matchMedia();

  /* ==========================================================
     REDUCED MOTION
     The collage still assembles, but instantly. Nothing moves.
     ========================================================== */
  mm.add('(prefers-reduced-motion: reduce)', function () {
    gsap.set('.anim-row > span, .anim-fade, .anim-rise, .anim-strip', {
      clearProps: 'all', opacity: 1, y: 0, x: 0
    });
    root.classList.remove('js-motion');
  });

  /* ==========================================================
     SHARED ENTRANCE + SCROLL CHOREOGRAPHY
     Runs for every viewport where motion is allowed. Breakpoint
     specific behaviour (parallax, hover) is added separately.
     ========================================================== */
  mm.add('(prefers-reduced-motion: no-preference)', function () {

    /* Case-study pages share the chrome but not the hero collage.
       Running the homepage timeline there would animate nothing and
       log a GSAP target warning for every missing selector. */
    if (!document.querySelector('.hero')) {
      caseMotion();
      return;
    }

    /* ---- A. PAGE ENTRANCE --------------------------------
       One timeline. The headline rows arrive first and slightly
       out of step with each other, the sculpture rises out of
       the dark underneath them, the censor strip snaps on last,
       then the paper and the handwriting land on top - which is
       the order somebody would actually build the collage in. */
    // will-change is a promise to the compositor, not a free win:
    // holding layers for the life of the page costs memory. The CSS
    // sets it for the entrance; we hand it back as soon as the
    // entrance is done.
    var tl = gsap.timeline({
      defaults: { ease: 'power3.out' },
      onComplete: function () {
        gsap.set('.nav .anim-fade, .hero .anim-row > span, .hero .anim-fade, .hero .anim-rise, .anim-strip',
          { willChange: 'auto' });
      }
    });

    tl.to('.wordmark, .nav .btn--acid', {
        opacity: 1, duration: 0.5, stagger: 0.08
      })

      // Headline rows wipe up through their masks. The stagger is
      // uneven on purpose - typeset rows landing in lockstep read
      // as a template.
      .to('.anim-row > span', {
        y: '0%', duration: 0.9, ease: 'expo.out',
        stagger: { each: 0.085, from: 'start' }
      }, '-=0.2')

      // The sculpture lifts out of darkness.
      .fromTo('.statue__img',
        { opacity: 0, y: 34, scale: 1.04 },
        { opacity: 1, y: 0, scale: 1, duration: 1.15, ease: 'power2.out' },
        '-=0.75')

      // The strip snaps into place - fast in, no bounce, like
      // tape being pressed down.
      .to('.anim-strip', {
        opacity: 1, x: 0, duration: 0.42, ease: 'power4.out'
      }, '-=0.5')

      // Copy, buttons and the paper stack settle last.
      .to('.hero__col--copy .anim-rise', {
        opacity: 1, y: 0, duration: 0.7, stagger: 0.09
      }, '-=0.55')

      .to('.hero__col--papers .anim-rise', {
        opacity: 1, y: 0, duration: 0.7, stagger: 0.11
      }, '-=0.5')

      // Handwriting appears after the composition exists, the way
      // annotation actually happens.
      .to('.hero .anim-fade:not(.statue__img)', {
        opacity: 1, duration: 0.55, stagger: 0.07
      }, '-=0.45');

    /* ---- C. SCROLL CHOREOGRAPHY -------------------------- */

    // Project cards enter in batches, each at a slightly different
    // angle, then straighten as they settle onto the page.
    // Any new section must be listed here or its .anim-rise elements
    // stay at opacity 0 forever - which is exactly what happened when
    // the experience section was added.
    ScrollTrigger.batch('.projects__grid .anim-rise, .experience .anim-rise', {
      start: 'top 88%',
      once: true,
      onEnter: function (batch) {
        gsap.to(batch, {
          opacity: 1, y: 0, duration: 0.85, ease: 'power3.out',
          stagger: 0.09,
          // rotation is left to CSS so the hover state stays
          // authoritative; we only animate position/opacity here.
          overwrite: true,
          onComplete: function () { gsap.set(batch, { willChange: 'auto' }); }
        });
      }
    });

    // The hand-drawn underline draws itself.
    gsap.utils.toArray('.draw-line').forEach(function (path) {
      var len = path.getTotalLength();
      gsap.set(path, { strokeDasharray: len, strokeDashoffset: len });
      gsap.to(path, {
        strokeDashoffset: 0, duration: 0.9, ease: 'power2.inOut',
        scrollTrigger: { trigger: path, start: 'top 90%', once: true }
      });
    });

    // Outro marks.
    ScrollTrigger.batch('.outro .anim-rise', {
      start: 'top 92%',
      once: true,
      onEnter: function (batch) {
        gsap.to(batch, {
          opacity: 1, y: 0, duration: 0.75, stagger: 0.08, overwrite: true,
          onComplete: function () { gsap.set(batch, { willChange: 'auto' }); }
        });
      }
    });
    gsap.to('.outro .anim-fade', {
      opacity: 1, duration: 0.6,
      scrollTrigger: { trigger: '.outro', start: 'top 92%', once: true }
    });

    // NOTE: the grain deliberately has NO scroll tween. It is a
    // position:fixed layer, so it already sits still while the
    // content moves past it - the strongest possible "slower than
    // foreground" parallax. Scrubbing it repainted a layer twice the
    // viewport in each dimension on every scroll frame and cost
    // roughly 17fps, which is not worth 6% of drift nobody can see.

    return function () {
      // matchMedia revert restores the inline state it set; the
      // batched triggers are killed with the context.
    };
  });

  /* ==========================================================
     CASE STUDY MOTION
     A document, not a poster: the entrance is a short settle and
     the rest reveals on scroll. No parallax, nothing that delays
     reading.
     ========================================================== */
  function caseMotion() {
    var tl = gsap.timeline({
      defaults: { ease: 'power3.out' },
      onComplete: function () {
        gsap.set('.case-hero .anim-rise, .nav .anim-fade', { willChange: 'auto' });
      }
    });

    tl.to('.case-hero .anim-rise', {
      opacity: 1, y: 0, duration: 0.7, stagger: 0.08
    });

    ScrollTrigger.batch('.case-section .anim-rise, .shot.anim-rise, .shot-row.anim-rise', {
      start: 'top 90%',
      once: true,
      onEnter: function (batch) {
        gsap.to(batch, {
          opacity: 1, y: 0, duration: 0.7, ease: 'power3.out', stagger: 0.08,
          overwrite: true,
          onComplete: function () { gsap.set(batch, { willChange: 'auto' }); }
        });
      }
    });
  }

  /* ==========================================================
     B. HERO DEPTH - desktop pointer parallax
     Deliberately tiny: 4-16px. The collage should breathe, not
     fly apart. Pointer-driven only, quickAddTo keeps it off the
     layout path entirely.
     ========================================================== */
  mm.add('(min-width: 1100px) and (prefers-reduced-motion: no-preference) and (pointer: fine)', function () {
    var hero = document.querySelector('.hero');
    if (!hero) return;

    // Each layer gets its own depth. Background texture moves
    // least, handwriting on top moves most.
    var layers = [
      { el: '.statue',            depth: 7 },
      { el: '.strip',             depth: 12 },
      { el: '.hero__col--papers', depth: 10 },
      { el: '.headline',          depth: 4 },
      { el: '.annot',             depth: 16 }
    ];

    var setters = layers.map(function (l) {
      var targets = gsap.utils.toArray(l.el);
      return {
        depth: l.depth,
        x: targets.map(function (t) { return gsap.quickTo(t, 'x', { duration: 0.7, ease: 'power3.out' }); }),
        y: targets.map(function (t) { return gsap.quickTo(t, 'y', { duration: 0.7, ease: 'power3.out' }); })
      };
    });

    function onMove(e) {
      var r = hero.getBoundingClientRect();
      // -1..1 from the centre of the hero.
      var nx = gsap.utils.clamp(-1, 1, (e.clientX - r.left - r.width / 2) / (r.width / 2));
      var ny = gsap.utils.clamp(-1, 1, (e.clientY - r.top - r.height / 2) / (r.height / 2));
      setters.forEach(function (s) {
        s.x.forEach(function (fn) { fn(-nx * s.depth); });
        s.y.forEach(function (fn) { fn(-ny * s.depth * 0.6); });
      });
    }

    function onLeave() {
      setters.forEach(function (s) {
        s.x.forEach(function (fn) { fn(0); });
        s.y.forEach(function (fn) { fn(0); });
      });
    }

    window.addEventListener('pointermove', onMove, { passive: true });
    hero.addEventListener('pointerleave', onLeave);

    return function () {
      window.removeEventListener('pointermove', onMove);
      hero.removeEventListener('pointerleave', onLeave);
      onLeave();
    };
  });

  /* ==========================================================
     E. MAGNETIC CTA - desktop only
     The acid button leans toward the cursor. Small enough that
     it reads as weight, not as a gimmick.
     ========================================================== */
  mm.add('(min-width: 1100px) and (prefers-reduced-motion: no-preference) and (pointer: fine)', function () {
    var cleanups = [];

    gsap.utils.toArray('.btn--acid, .btn-circle').forEach(function (btn) {
      var xTo = gsap.quickTo(btn, 'x', { duration: 0.4, ease: 'power3.out' });
      var yTo = gsap.quickTo(btn, 'y', { duration: 0.4, ease: 'power3.out' });

      function move(e) {
        var r = btn.getBoundingClientRect();
        xTo(gsap.utils.clamp(-8, 8, (e.clientX - (r.left + r.width / 2)) * 0.32));
        yTo(gsap.utils.clamp(-8, 8, (e.clientY - (r.top + r.height / 2)) * 0.32));
      }
      function reset() { xTo(0); yTo(0); }

      btn.addEventListener('pointermove', move);
      btn.addEventListener('pointerleave', reset);
      cleanups.push(function () {
        btn.removeEventListener('pointermove', move);
        btn.removeEventListener('pointerleave', reset);
        gsap.set(btn, { x: 0, y: 0 });
      });
    });

    return function () { cleanups.forEach(function (fn) { fn(); }); };
  });

  /* ==========================================================
     Fonts change metrics; recompute trigger positions once they
     land so nothing enters at the wrong scroll position.
     ========================================================== */
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(function () { ScrollTrigger.refresh(); });
  }

  /* ==========================================================
     MENU  (works without GSAP)
     ========================================================== */
  function initMenu() {
    var burger = document.querySelector('.burger');
    var menu = document.getElementById('menu');
    if (!burger || !menu) return;

    var closeBtn = menu.querySelector('.menu__close');
    var lastFocus = null;

    function open() {
      lastFocus = document.activeElement;
      menu.hidden = false;
      burger.setAttribute('aria-expanded', 'true');
      burger.setAttribute('aria-label', 'Close menu');
      document.body.style.overflow = 'hidden';

      // The rest of the page is not reachable while the dialog is up.
      // This must happen BEFORE we move focus: making the burger's
      // ancestor inert kicks focus to <body>, and that fixup would
      // otherwise land after our own focus() call and undo it.
      setInert(true);

      // Next frame so the transition actually runs.
      requestAnimationFrame(function () {
        menu.dataset.open = 'true';
        // A second frame: the dialog is still `visibility: hidden` on
        // the frame the class flips, and a hidden element cannot take
        // focus, so focusing here would silently do nothing.
        requestAnimationFrame(function () {
          (closeBtn || menu.querySelector('a')).focus();
        });
      });
    }

    function close() {
      menu.dataset.open = 'false';
      burger.setAttribute('aria-expanded', 'false');
      burger.setAttribute('aria-label', 'Open menu');
      document.body.style.overflow = '';
      setInert(false);
      window.setTimeout(function () { menu.hidden = true; }, 340);
      if (lastFocus) lastFocus.focus();
    }

    burger.addEventListener('click', function () {
      menu.dataset.open === 'true' ? close() : open();
    });
    if (closeBtn) closeBtn.addEventListener('click', close);

    menu.addEventListener('click', function (e) {
      if (e.target.tagName === 'A') close();
    });

    function setInert(on) {
      ['header', 'main', 'footer'].forEach(function (sel) {
        var el = document.querySelector(sel);
        if (!el) return;
        if (on) el.setAttribute('inert', '');
        else el.removeAttribute('inert');
      });
    }

    document.addEventListener('keydown', function (e) {
      if (menu.dataset.open !== 'true') return;

      if (e.key === 'Escape') { close(); return; }

      // Focus trap: an aria-modal dialog must not leak Tab to the
      // page behind it. inert covers browsers that support it; this
      // keeps the cycle correct everywhere.
      if (e.key !== 'Tab') return;
      var f = menu.querySelectorAll('a[href], button');
      if (!f.length) return;
      var first = f[0], last = f[f.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    });
  }

  function initYear() {
    var y = document.getElementById('year');
    if (y) y.textContent = new Date().getFullYear();
  }
})();
