const menu=document.querySelector('.menu');const nav=document.querySelector('nav');menu.addEventListener('click',()=>{const open=nav.classList.toggle('open');menu.setAttribute('aria-expanded',String(open));menu.setAttribute('aria-label',open?'Close navigation':'Open navigation')});document.addEventListener('keydown',e=>{if(e.key==='Escape'){nav.classList.remove('open');menu.setAttribute('aria-expanded','false')}});const box=document.querySelector('#lightbox');let previous;document.querySelectorAll('[data-photo]').forEach(b=>b.addEventListener('click',()=>{previous=b;box.querySelector('img').src=b.dataset.photo;box.querySelector('img').alt=b.dataset.caption;box.querySelector('p').textContent=b.dataset.caption;box.showModal()}));box.querySelector('.close').addEventListener('click',()=>box.close());box.addEventListener('click',e=>{if(e.target===box)box.close()});box.addEventListener('close',()=>previous?.focus());

/* Use platform logos for shared social links on every page. */
(() => {
  const logos = {
    facebook: {label: 'Facebook', path: 'M24 12.073C24 5.405 18.627 0 12 0S0 5.405 0 12.073c0 6.025 4.388 11.02 10.125 11.927v-8.437H7.078v-3.49h3.047V9.413c0-3.026 1.792-4.697 4.533-4.697 1.312 0 2.686.235 2.686.235v2.972h-1.513c-1.491 0-1.956.931-1.956 1.887v2.263h3.328l-.532 3.49h-2.796V24C19.612 23.094 24 18.099 24 12.073z'},
    x: {label: 'X (Twitter)', path: 'M18.901 1.153h3.68l-8.04 9.19L24 22.846h-7.406l-5.8-7.584-6.64 7.584H.47l8.6-9.835L0 1.154h7.594l5.243 6.932zm-1.29 19.49h2.039L6.487 3.24H4.3z'},
    youtube: {label: 'YouTube', path: 'M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.121 2.136c1.872.505 9.377.505 9.377.505s7.505 0 9.376-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12z'},
    linkedin: {label: 'LinkedIn', path: 'M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.049c.476-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 1 1 0-4.124 2.062 2.062 0 0 1 0 4.124zM7.119 20.452H3.555V9h3.564zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0z'}
  };
  function logo(node, platform) {
    const icon = logos[platform];
    node.setAttribute('aria-label', icon.label);
    node.setAttribute('title', icon.label);
    node.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="22" height="22" fill="currentColor" aria-hidden="true" focusable="false"><path d="' + icon.path + '"/></svg>';
    node.style.display = 'inline-flex';
    node.style.alignItems = 'center';
    node.style.justifyContent = 'center';
    node.style.minWidth = '44px';
    node.style.minHeight = '44px';
    node.style.marginLeft = '0';
    node.style.padding = '8px';
    node.style.borderBottom = '0';
  }
  document.querySelectorAll('.utility a, .social a').forEach(link => {
    const host = new URL(link.href).hostname.replace(/^www\\./, '');
    const platform = {'facebook.com':'facebook', 'twitter.com':'x', 'x.com':'x', 'youtube.com':'youtube', 'linkedin.com':'linkedin'}[host];
    if (platform) logo(link, platform);
  });
  document.querySelectorAll('.feed-heading h3').forEach(heading => {
    const platform = /twitter|^x$/i.test(heading.textContent.trim()) ? 'x' : /linkedin/i.test(heading.textContent) ? 'linkedin' : null;
    if (platform) logo(heading, platform);
  });
})();
