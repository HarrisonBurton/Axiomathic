(() => {
  const $ = (s, root=document) => root.querySelector(s);
  const $$ = (s, root=document) => Array.from(root.querySelectorAll(s));
  const CONFIG = window.AXIOMATHIC_SITE || {sections: [], utilityPages: []};

  function icon(name) {
    const paths = {
      search: '<circle cx="11" cy="11" r="7"></circle><path d="m20 20-4-4"></path>',
      sun: '<circle cx="12" cy="12" r="4"></circle><path d="M12 2v2M12 20v2M4.93 4.93l1.42 1.42M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.42-1.42M17.66 6.34l1.41-1.41"></path>',
      doc: '<path d="M6 2h8l4 4v16H6z"></path><path d="M14 2v5h5M9 13h6M9 17h6"></path>',
      link: '<path d="M10 13a5 5 0 0 0 7.5.5l2-2a5 5 0 0 0-7-7l-1.15 1.15"></path><path d="M14 11a5 5 0 0 0-7.5-.5l-2 2a5 5 0 0 0 7 7l1.15-1.15"></path>'
    };
    return `<svg viewBox="0 0 24 24" width="19" height="19" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name]}</svg>`;
  }

  function currentFile() {
    return location.pathname.split('/').pop() || 'index.html';
  }

  function categoryFor(file) {
    return (CONFIG.sections || []).find(s => (s.pages || []).some(p => p.file === file)) || null;
  }

  function utilityFor(file) {
    return (CONFIG.utilityPages || []).find(p => p.file === file) || null;
  }

  function addHeader() {
    const file = currentFile();
    const header = document.createElement('header');
    header.className = 'ax-header';

    const nav = [
      `<a href="index.html" data-nav="home">Home</a>`,
      ...(CONFIG.sections || []).map(s => `<a href="index.html#${s.id}" data-nav="${s.id}">${s.label}</a>`),
      `<a href="index.html#about" data-nav="about">About</a>`
    ].join('');

    header.innerHTML = `
      <a class="ax-brand" href="index.html" aria-label="Axiomathic home">
        <img class="ax-brand-logo" src="assets/axiomathic-alpha.png" alt="" aria-hidden="true">
        <span class="ax-wordmark">xiomathic</span>
      </a>
      <nav class="ax-nav" aria-label="Site navigation">${nav}</nav>
      <div class="ax-tools">
        <label class="ax-search" aria-label="Search the contents">${icon('search')}<input id="ax-search-input" type="search" placeholder="Search contents…"></label>
        <button class="ax-iconbtn" id="ax-theme-toggle" type="button" aria-label="Toggle dark mode">${icon('sun')}</button>
      </div>`;
    document.body.prepend(header);

    const category = categoryFor(file);
    if (file === 'index.html' || file === '') $('[data-nav="home"]')?.classList.add('active');
    else if (category) $(`[data-nav="${category.id}"]`)?.classList.add('active');
  }

  function markPage() {
    const file = currentFile();
    if (file === 'index.html' || file === '') document.body.classList.add('ax-home');
  }

  function replaceLeftRail() {
    if (document.body.classList.contains('ax-home')) return;
    const container = $('.sidetoccontainer');
    if (!container) return;

    const file = currentFile();
    const category = categoryFor(file);
    const utility = utilityFor(file);

    if (category) {
      const links = (category.pages || []).map(p =>
        `<a class="${p.file === file ? 'is-current' : ''}" href="${p.file}">${p.title}</a>`
      ).join('');
      container.innerHTML = `
        <nav class="ax-local-nav" aria-label="${category.label}">
          <div class="ax-local-title">${category.label}</div>
          <div class="ax-local-description">${category.description || ''}</div>
          <div class="ax-local-links">${links}</div>
        </nav>`;
    } else if (utility) {
      container.innerHTML = `
        <nav class="ax-local-nav" aria-label="${utility.label || utility.title}">
          <div class="ax-local-title">${utility.label || utility.title}</div>
          <div class="ax-local-links">
            <a class="is-current" href="${utility.file}">${utility.title}</a>
          </div>
        </nav>`;
    } else {
      container.style.display = 'none';
      document.body.classList.add('ax-no-left-rail');
    }
  }

  function buildLanding() {
    if (!document.body.classList.contains('ax-home')) return;
    const body = $('section.textbody');
    if (!body) return;

    const sectionHtml = (CONFIG.sections || []).map(section => `
      <section class="ax-home-section" id="${section.id}">
        <div class="ax-section-heading"><span>${section.label}</span><p>${section.description || ''}</p></div>
        <div class="ax-card-grid">
          ${(section.pages || []).map(page => `
            <a class="ax-home-card" href="${page.file}">
              <span class="ax-card-eyebrow">${page.eyebrow || section.label}</span>
              <strong>${page.title}</strong>
              <span>${page.description || ''}</span>
            </a>`).join('')}
        </div>
      </section>`).join('');

    const utilityCards = (CONFIG.utilityPages || []).length ? `
      <section class="ax-home-section" id="style-guide">
        <div class="ax-section-heading"><span>Style Guide</span><p>Reference examples for theorem environments and notation used across Axiomathic.</p></div>
        <div class="ax-utility-grid">
          ${(CONFIG.utilityPages || []).map(p => `
            <a class="ax-utility-card" href="${p.file}">
              <strong>${p.title}</strong>
              <span>Review the theorem, definition, notation, conjecture and related environment styles.</span>
            </a>`).join('')}
        </div>
      </section>` : '';

    const utilityLinks = (CONFIG.utilityPages || []).map(p =>
      `<a href="${p.file}">${p.title}</a>`
    ).join('');

    body.innerHTML = `
      <main class="ax-landing" aria-label="Axiomathic home">
        <section class="ax-hero">
          <div class="ax-kicker">AXIOMATHIC</div>
          <h1>${CONFIG.tagline || 'Mathematics, carefully written.'}</h1>
          <p>${CONFIG.intro || ''}</p>
        </section>
        ${sectionHtml}
        ${utilityCards}
        <section class="ax-home-section" id="about">
          <div class="ax-section-heading"><span>About</span></div>
          <div class="ax-about-panel">
            <p>${CONFIG.about || ''}</p>
            <p class="ax-home-actions"><a href="Axiomathic.pdf" target="_blank" rel="noopener">View compiled PDF</a>${utilityLinks}</p>
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
    const searchable = [
      ...(CONFIG.sections || []).flatMap(s => s.pages || []),
      ...(CONFIG.utilityPages || [])
    ];
    input.addEventListener('keydown', e => {
      if (e.key !== 'Enter') return;
      const q = input.value.trim().toLowerCase();
      if (!q) return;
      const hit = searchable.find(p =>
        `${p.title || ''} ${p.description || ''}`.toLowerCase().includes(q)
      );
      if (hit) location.href = hit.file;
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
    replaceLeftRail();
    buildLanding();
    addRightRail();
    wireSearch();
    wireTheme();
    wireCopy();
  });
})();
