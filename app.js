/* Load the editorial layer on retained secondary templates. */
(() => {
  if (document.querySelector('link[href="/editorial.css"]')) return;
  const stylesheet = document.createElement('link');
  stylesheet.rel = 'stylesheet';
  stylesheet.href = '/editorial.css';
  document.head.append(stylesheet);
})();

/* Small-screen navigation. */
(() => {
  const menu = document.querySelector('.menu');
  const nav = document.querySelector('nav');
  if (!menu || !nav) return;
  const header = document.querySelector('header');
  menu.textContent = 'Menu';
  if (!nav.id) nav.id = 'primary-navigation';
  menu.setAttribute('aria-controls', nav.id);

  const primaryLinks = [
    ['/', 'Home'],
    ['/wiki/', 'About'],
    ['/media/', 'Media'],
    ['/gallery/', 'Gallery'],
    ['/contact-us/', 'Contact']
  ];
  nav.querySelector('a[href="/initiatives/"]')?.remove();
  nav.querySelector('a[href="/public-profile/"]')?.remove();
  primaryLinks.forEach(([href, label]) => {
    const link = Array.from(nav.querySelectorAll('a')).find(item => item.getAttribute('href') === href);
    if (!link) return;
    link.textContent = label;
    nav.append(link);
  });

  const setMenu = (open, returnFocus = false) => {
    nav.classList.toggle('open', open);
    document.body.classList.toggle('menu-open', open);
    menu.setAttribute('aria-expanded', String(open));
    menu.setAttribute('aria-label', open ? 'Close navigation' : 'Open navigation');
    menu.textContent = open ? 'Close' : 'Menu';
    if (open) nav.querySelector('a')?.focus();
    if (!open && returnFocus) menu.focus();
  };

  menu.addEventListener('click', () => setMenu(!nav.classList.contains('open')));

  nav.addEventListener('click', event => {
    if (event.target.closest('a')) setMenu(false);
  });

  document.addEventListener('keydown', event => {
    if (event.key !== 'Escape') return;
    if (nav.classList.contains('open')) setMenu(false, true);
  });

  const updateHeader = () => header?.classList.toggle('is-scrolled', window.scrollY > 12);
  updateHeader();
  window.addEventListener('scroll', updateHeader, { passive: true });
})();

/* Keep retained legacy footers aligned with the personal-site framing. */
(() => {
  document.querySelectorAll('footer div.brand > p').forEach(copy => {
    copy.textContent = 'An official space for Manasvi’s work, ideas and public conversations.';
  });
})();

/* Accessible image lightbox, used by the gallery pages. */
(() => {
  const box = document.querySelector('#lightbox');
  if (!box) return;
  const close = box.querySelector('.close');
  const image = box.querySelector('img');
  const caption = box.querySelector('p');
  let previous;

  document.querySelectorAll('[data-photo]').forEach(button => {
    button.addEventListener('click', () => {
      previous = button;
      image.src = button.dataset.photo;
      image.alt = button.dataset.caption || '';
      caption.textContent = button.dataset.caption || '';
      box.showModal();
    });
  });

  close?.addEventListener('click', () => box.close());
  box.addEventListener('click', event => {
    if (event.target === box) box.close();
  });
  box.addEventListener('close', () => previous?.focus());
})();

/* Replace repeated social text with consistent accessible SVG platform marks. */
(() => {
  const icons = {
    facebook: {
      label: 'Facebook',
      path: 'M24 12.073C24 5.405 18.627 0 12 0S0 5.405 0 12.073c0 6.025 4.388 11.02 10.125 11.927v-8.437H7.078v-3.49h3.047V9.413c0-3.026 1.792-4.697 4.533-4.697 1.312 0 2.686.235 2.686.235v2.972h-1.513c-1.491 0-1.956.931-1.956 1.887v2.263h3.328l-.532 3.49h-2.796V24C19.612 23.094 24 18.099 24 12.073z'
    },
    x: {
      label: 'X (Twitter)',
      path: 'M18.901 1.153h3.68l-8.04 9.19L24 22.846h-7.406l-5.8-7.584-6.64 7.584H.47l8.6-9.835L0 1.154h7.594l5.243 6.932zm-1.29 19.49h2.039L6.487 3.24H4.3z'
    },
    youtube: {
      label: 'YouTube',
      path: 'M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.121 2.136c1.872.505 9.377.505 9.377.505s7.505 0 9.376-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12z'
    },
    linkedin: {
      label: 'LinkedIn',
      path: 'M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.049c.476-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 1 1 0-4.124 2.062 2.062 0 0 1 0 4.124zM7.119 20.452H3.555V9h3.564zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0z'
    },
    instagram: {
      label: 'Instagram',
      stroke: true,
      path: '<rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r="1" fill="currentColor" stroke="none"/>'
    }
  };
  const platforms = {
    'facebook.com': 'facebook',
    'twitter.com': 'x',
    'x.com': 'x',
    'youtube.com': 'youtube',
    'linkedin.com': 'linkedin',
    'instagram.com': 'instagram'
  };

  function applyIcon(link, platform) {
    const icon = icons[platform];
    if (!icon) return;
    link.setAttribute('aria-label', icon.label);
    link.setAttribute('title', icon.label);
    const content = icon.stroke
      ? icon.path
      : '<path d="' + icon.path + '"/>';
    const attrs = icon.stroke
      ? 'fill="none" stroke="currentColor" stroke-width="2"'
      : 'fill="currentColor"';
    link.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="19" height="19" ' + attrs + ' aria-hidden="true" focusable="false">' + content + '</svg>';
  }

  document.querySelectorAll('.utility a, .social a').forEach(link => {
    const host = new URL(link.href).hostname.replace(/^www\./, '');
    applyIcon(link, platforms[host]);
  });

  document.querySelectorAll('.utility .wrap > div, .social').forEach(group => {
    if (group.querySelector('a[href*="instagram.com"]')) return;
    const link = document.createElement('a');
    link.href = 'https://www.instagram.com/manasvithapar/';
    link.target = '_blank';
    link.rel = 'noopener';
    applyIcon(link, 'instagram');
    group.append(link);
  });
})();
