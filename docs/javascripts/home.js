/* Progressive enhancement: navigation and examples also work without JavaScript. */
(() => {
  const button = document.querySelector('[data-copy]');
  const status = document.getElementById('px-copy-status');
  if (button && status) {
    button.addEventListener('click', async () => {
      const command = document.getElementById(button.dataset.copy);
      try {
        await navigator.clipboard.writeText(command.textContent);
        status.textContent = 'Installation command copied.';
      } catch {
        const selection = window.getSelection();
        const range = document.createRange();
        range.selectNodeContents(command);
        selection.removeAllRanges();
        selection.addRange(range);
        status.textContent = 'Command selected. Press Ctrl+C or ⌘C to copy.';
      }
    });
  }
  const menu = document.querySelector('.px-mobile-nav');
  if (menu) {
    menu.addEventListener('click', (event) => {
      if (event.target.closest('a')) menu.open = false;
    });
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && menu.open) {
        menu.open = false;
        menu.querySelector('summary').focus();
      }
    });
    document.addEventListener('click', (event) => {
      if (!menu.contains(event.target)) menu.open = false;
    });
  }
  const search = document.querySelector('.px-search-trigger');
  if (search) search.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      document.getElementById('__search').checked = true;
      document.querySelector('.md-search__input')?.focus();
    }
  });
})();
