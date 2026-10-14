/* Progressive enhancements shared by full pages and HTMX fragments. */
function nlkToast(message) {
 const toast = document.getElementById('nlk-toast');
 toast.textContent = message; toast.classList.remove('hidden');
 clearTimeout(window.nlkToastTimer);
 window.nlkToastTimer = setTimeout(() => toast.classList.add('hidden'), 6000);
}
function toggleTheme() {
 const dark = document.documentElement.classList.toggle('dark');
 try { localStorage.setItem('theme', dark ? 'dark' : 'light'); } catch (error) {}
 document.querySelectorAll('[data-theme-toggle]').forEach(button => button.setAttribute('aria-pressed', String(dark)));
}
function enhanceForms(root = document) {
 root.querySelectorAll('form').forEach(form => {
  form.querySelectorAll('.field-error, .text-red-600').forEach((error, index) => {
   const label = error.parentElement.querySelector('label[for]');
   const field = label ? document.getElementById(label.htmlFor) : error.previousElementSibling;
   if (field && field.matches('input,textarea,select')) {
    error.id ||= `${field.id}-error-${index}`;
    field.setAttribute('aria-invalid','true');
    field.setAttribute('aria-describedby', [...new Set([...(field.getAttribute('aria-describedby') || '').split(' '), error.id].filter(Boolean))].join(' '));
   }
  });
 });
}
document.addEventListener('click', event => {
 const opener = event.target.closest('[data-dialog-open]');
 if (opener) {
  const dialog = document.getElementById(opener.dataset.dialogOpen);
  dialog.showModal(); opener.setAttribute('aria-expanded','true');
 }
 const closer = event.target.closest('[data-dialog-close]');
 if (closer) closer.closest('dialog').close();
 if (event.target.matches('dialog')) {
  const rect = event.target.getBoundingClientRect();
  if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) event.target.close();
 }
 if (event.target.closest('[data-theme-toggle]')) toggleTheme();
});
document.querySelectorAll('dialog').forEach(dialog => dialog.addEventListener('close', () => {
 document.querySelectorAll(`[data-dialog-open="${dialog.id}"]`).forEach(opener => opener.setAttribute('aria-expanded','false'));
}));
window.matchMedia('(min-width:1024px)').addEventListener('change', event => {
 if(event.matches) document.querySelectorAll('dialog[open]').forEach(dialog => dialog.close());
});
document.querySelectorAll('[data-navigation] a').forEach(link => {
 if (link.pathname === location.pathname) link.setAttribute('aria-current','page');
});
document.querySelectorAll('[data-theme-toggle]').forEach(button => button.setAttribute('aria-pressed', String(document.documentElement.classList.contains('dark'))));
enhanceForms();
document.body.addEventListener('htmx:afterSwap', event => enhanceForms(event.detail.target));
document.body.addEventListener('htmx:beforeRequest', event => {
 if (event.detail.target) event.detail.target.setAttribute('aria-busy','true');
});
document.body.addEventListener('htmx:afterRequest', event => {
 if (event.detail.target) event.detail.target.removeAttribute('aria-busy');
 if (event.detail.failed) nlkToast('Something went wrong. Please try again.');
});
// Keep variant price and quantity limits in sync with the selected option.
document.querySelectorAll('[data-variant-picker]').forEach(picker => {
 const available = Array.from(picker.options).filter(option => option.value && !option.disabled);
 if (available.length === 1) picker.value = available[0].value;
 const sync = () => {
  const option = picker.selectedOptions[0];
  if (!option || !option.value) return;
  document.querySelector('[data-product-price]').textContent = `Rs. ${option.dataset.price}`;
  const quantity = picker.form.querySelector('[name=quantity]');
  quantity.max = option.dataset.stock;
  quantity.value = Math.max(1, Math.min(Number(quantity.value), Number(option.dataset.stock)));
 };
 picker.addEventListener('change', sync); sync();
});
