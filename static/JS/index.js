// static/js/index.js

// Modal helpers
function openModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.remove('hidden');
}
function closeModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.add('hidden');
}
function toggleMobile() {
  // simple mobile nav: open page or alert
  alert('Mobile navigation — add links or implement sidebar as needed.');
}

// Copy short url
function copyToClipboard() {
  const input = document.getElementById('short-url');
  if (!input) return;
  navigator.clipboard.writeText(input.value).then(() => {
    // small feedback
    const old = input.value;
    input.value = 'Copied!';
    setTimeout(() => input.value = old, 900);
  });
}

// AJAX submit for shorten form
document.addEventListener('DOMContentLoaded', function () {
  const form = document.getElementById('shorten-form');
  if (!form) return;

  form.addEventListener('submit', async function (e) {
    // If user has JS, prevent normal submit and do AJAX
    e.preventDefault();

    const data = new FormData(form);
    const url = form.getAttribute('action') || '/shorten';

    // small UI lock
    const btn = document.getElementById('shorten-btn');
    btn.disabled = true;
    btn.innerText = 'Shortening...';

    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'x-requested-with': 'XMLHttpRequest' }, // server detects AJAX
        body: data
      });
      const payload = await res.json();
      if (!res.ok) {
        alert(payload.error || 'Failed to shorten');
        return;
      }

      // show result UI
      const result = document.getElementById('result');
      const input = document.getElementById('short-url');
      const openLink = document.getElementById('open-link');

      input.value = payload.short_url;
      openLink.href = payload.short_url;
      openLink.innerText = 'Open link';
      result.classList.remove('hidden');

      // also update URL (optional) without reload
      history.replaceState(null, '', `/?original_url=${encodeURIComponent(document.getElementById('original_url').value)}&custom_alias=${encodeURIComponent(document.getElementById('custom_alias').value || '')}&ttl=${document.getElementById('ttl').value}`);
    } catch (err) {
      console.error(err);
      alert('Error creating short link');
    } finally {
      btn.disabled = false;
      btn.innerHTML = 'Shorten Link';
    }
  });
});
