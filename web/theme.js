(() => {
  const $ = (s, root=document) => root.querySelector(s);
  const $$ = (s, root=document) => Array.from(root.querySelectorAll(s));

  function icon(name) {
    const paths = {
      search: '<circle cx="11" cy="11" r="7"></circle><path d="m20 20-4-4"></path>',
      sun: '<circle cx="12" cy="12" r="4"></circle><path d="M12 2v2M12 20v2M4.93 4.93l1.42 1.42M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.42-1.42M17.66 6.34l1.41-1.41"></path>',
      doc: '<path d="M6 2h8l4 4v16H6z"></path><path d="M14 2v5h5M9 13h6M9 17h6"></path>',
      link: '<path d="M10 13a5 5 0 0 0 7.5.5l2-2a5 5 0 0 0-7-7l-1.15 1.15"></path><path d="M14 11a5 5 0 0 0-7.5-.5l-2 2a5 5 0 0 0 7 7l1.15-1.15"></path>'
    };
    return `<svg viewBox="0 0 24 24" width="19" height="19" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name]}</svg>`;
  }

  function addHeader() {
    const file = location.pathname.split('/').pop() || 'index.html';
    const header = document.createElement('header');
    header.className = 'ax-header';
    header.innerHTML = `
      <a class="ax-brand" href="index.html" aria-label="Axiomathic home">
        <span class="ax-brand-mark" aria-hidden="true"><span class="ax-alpha">α</span></span><span class="ax-wordmark">xiomathic</span>
      </a>
      <nav class="ax-nav" aria-label="Site navigation">
        <a href="index.html" data-nav="home">Home</a>
        <a href="index.html#notes" data-nav="notes">Summary Notes</a>
        <a href="index.html#projects" data-nav="projects">Projects</a>
        <a href="Theorem-Style-Guide.html" data-nav="style">Style Guide</a>
        <a href="index.html#about" data-nav="about">About</a>
      </nav>
      <div class="ax-tools">
        <label class="ax-search" aria-label="Search the contents">${icon('search')}<input id="ax-search-input" type="search" placeholder="Search contents…"></label>
        <button class="ax-iconbtn" id="ax-theme-toggle" type="button" aria-label="Toggle dark mode">${icon('sun')}</button>
      </div>`;
    document.body.prepend(header);

    if (file === 'index.html' || file === '') $('[data-nav="home"]')?.classList.add('active');
    else if (file === 'Theorem-Style-Guide.html') $('[data-nav="style"]')?.classList.add('active');
    else if (file === 'Shuffling-Cards.html') $('[data-nav="notes"]')?.classList.add('active');
    else if (file === 'The-easier-Waring-problem.html') $('[data-nav="projects"]')?.classList.add('active');
  }

  function markPage() {
    const file = location.pathname.split('/').pop() || 'index.html';
    if (file === 'index.html' || file === '') document.body.classList.add('ax-home');
    $$('.sidetoc a').forEach(a => {
      const target = (a.getAttribute('href') || '').split('#')[0];
      if (target === file) a.classList.add('is-current');
    });
  }

  function styleCallouts() {
    $$('.shadebox').forEach(box => {
      const name = ($('.amsthmnameplain, .amsthmnamedefinition, .amsthmnameremark', box)?.textContent || '').trim().toLowerCase();
      const types = ['definition','notation','conjecture','theorem','lemma','proposition','corollary','example','caution','warning','remark'];
      const hit = types.find(t => name.includes(t));
      if (hit) box.classList.add(`ax-${hit === 'caution' ? 'warning' : hit}`);
    });
  }

  function buildLanding() {
    if (!document.body.classList.contains('ax-home')) return;
    const body = $('section.textbody');
    if (!body) return;
    body.innerHTML = `
      <main class="ax-landing" aria-label="Axiomathic home">
        <section class="ax-hero">
          <div class="ax-kicker">AXIOMATHIC</div>
          <h1>Mathematics, carefully written.</h1>
          <p>A growing collection of summary notes, mathematical explorations and longer-form projects, all written in LaTeX and published directly to the web.</p>
        </section>

        <section class="ax-home-section" id="notes">
          <div class="ax-section-heading"><span>Summary Notes</span><p>Compact write-ups and worked mathematical ideas.</p></div>
          <div class="ax-card-grid">
            <a class="ax-home-card" href="Shuffling-Cards.html">
              <span class="ax-card-eyebrow">NOTE</span>
              <strong>Shuffling Cards</strong>
              <span>Permutation groups, perfect shuffles and the mathematics of returning a deck to its original order.</span>
            </a>
          </div>
        </section>

        <section class="ax-home-section" id="projects">
          <div class="ax-section-heading"><span>Projects</span><p>Longer investigations and research-style write-ups.</p></div>
          <div class="ax-card-grid">
            <a class="ax-home-card" href="The-easier-Waring-problem.html">
              <span class="ax-card-eyebrow">PROJECT</span>
              <strong>The Easier Waring Problem</strong>
              <span>Density, local obstructions and conjectural structure in signed sums of powers.</span>
            </a>
          </div>
        </section>

        <section class="ax-home-section" id="about">
          <div class="ax-section-heading"><span>About</span></div>
          <div class="ax-about-panel">
            <p>Axiomathic is built from a single LaTeX source: the same files generate the traditional PDF and this web edition. The visual layer is deliberately separate, so mathematical source files stay clean while the site can evolve independently.</p>
            <p class="ax-home-actions"><a href="Axiomathic.pdf" target="_blank" rel="noopener">View compiled PDF</a><a href="Theorem-Style-Guide.html">View theorem style guide</a></p>
          </div>
        </section>
      </main>`;
  }

  function addRightRail() {
    if (document.body.classList.contains('ax-home')) return;
    const headings = $$('section.textbody h4, section.textbody h5');
    const rail = document.createElement('aside');
    rail.className = 'ax-right-rail';
    const list = headings.length ? headings.map(h => {
      const number = $('.sectionnumber', h)?.textContent.trim() || '';
      const clone = h.cloneNode(true);
      $('.sectionnumber', clone)?.remove();
      const cls = h.tagName.toLowerCase() === 'h5' ? ' class="ax-subsection"' : '';
      return `<li${cls}><a href="#${h.id}">${number ? number + ' ' : ''}${clone.textContent.trim()}</a></li>`;
    }).join('') : '<li><span class="ax-quiet">No sections on this page</span></li>';
    rail.innerHTML = `
      <h3>On this page</h3>
      <ol class="ax-onpage">${list}</ol>
      <div class="ax-rail-tools">
        <a class="ax-rail-action" href="Axiomathic.pdf" target="_blank" rel="noopener">${icon('doc')}<span>View PDF</span></a>
        <button class="ax-rail-action" id="ax-copy-link" type="button">${icon('link')}<span>Copy page link</span></button>
        <div class="ax-copy-status" id="ax-copy-status" aria-live="polite"></div>
      </div>`;
    document.body.append(rail);
  }

  function wireSearch() {
    const input = $('#ax-search-input');
    if (!input) return;
    const links = $$('.sidetoccontents a, .ax-home-card');
    input.addEventListener('input', () => {
      const q = input.value.trim().toLowerCase();
      links.forEach(a => a.classList.toggle('ax-search-hit', q.length > 1 && a.textContent.toLowerCase().includes(q)));
    });
    input.addEventListener('keydown', e => {
      if (e.key === 'Enter') {
        const hit = $('.sidetoccontents a.ax-search-hit, .ax-home-card.ax-search-hit');
        if (hit) location.href = hit.href;
      }
    });
  }

  function wireTheme() {
    const stored = localStorage.getItem('axiomathic-theme');
    if (stored === 'dark') document.body.classList.add('ax-dark');
    $('#ax-theme-toggle')?.addEventListener('click', () => {
      document.body.classList.toggle('ax-dark');
      localStorage.setItem('axiomathic-theme', document.body.classList.contains('ax-dark') ? 'dark' : 'light');
    });
  }

  function wireCopy() {
    $('#ax-copy-link')?.addEventListener('click', async () => {
      const status = $('#ax-copy-status');
      try {
        await navigator.clipboard.writeText(location.href);
        status.textContent = 'Copied';
        setTimeout(() => status.textContent = '', 1500);
      } catch (_) {
        status.textContent = 'Copy unavailable';
      }
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    markPage();
    addHeader();
    styleCallouts();
    buildLanding();
    addRightRail();
    wireSearch();
    wireTheme();
    wireCopy();
  });
})();
