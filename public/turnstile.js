// Cloudflare Turnstile, drawn only if it has been configured.
//
// The server decides. A page asks /api/turnstile; if the keys are not set it
// answers {enabled:false} and this does nothing at all — no script loaded, no
// widget, no change to the form. That way a deploy without the keys behaves
// exactly as it did before, which is what you want on the day you launch.
//
// Usage, on any page with a form to protect:
//
//     <div id="cfBox"></div>
//     <script src="/turnstile.js"></script>
//     ...
//     await Turnstile.mount('cfBox');          // before the form is usable
//     body['cf-turnstile-response'] = Turnstile.token();
//     Turnstile.reset();                       // after a failed submit
//
// A token is good for one submission and about five minutes, so it is reset
// whenever a submit fails — otherwise the second attempt is refused for a
// reason the person cannot see.
window.Turnstile = (function () {
  let state = null;        // null = not asked yet, false = off, object = on
  let widgetId = null;
  let container = null;

  async function config() {
    if (state !== null) return state;
    try {
      const d = await fetch('/api/turnstile').then(r => r.json());
      state = d && d.enabled && d.sitekey ? d : false;
    } catch (e) { state = false; }
    return state;
  }

  function loadScript() {
    if (window.turnstile) return Promise.resolve();
    if (loadScript._p) return loadScript._p;
    return loadScript._p = new Promise((res, rej) => {
      const s = document.createElement('script');
      s.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';
      s.async = true; s.defer = true;
      s.onload = res;
      s.onerror = () => rej(new Error('Turnstile would not load'));
      document.head.appendChild(s);
    });
  }

  return {
    // Returns true when a widget was drawn, false when it is switched off.
    async mount(elOrId, opts) {
      const cfg = await config();
      if (!cfg) return false;
      container = typeof elOrId === 'string' ? document.getElementById(elOrId) : elOrId;
      if (!container) return false;
      try {
        await loadScript();
        widgetId = window.turnstile.render(container, {
          sitekey: cfg.sitekey,
          theme: (opts && opts.theme) || 'light',
          action: (opts && opts.action) || 'submit'
        });
        return true;
      } catch (e) {
        // Cloudflare unreachable from this browser. The server lets the request
        // through in that case, so the form must stay usable here too.
        container.innerHTML = '';
        return false;
      }
    },
    enabled() { return !!state; },
    token() {
      try { return (window.turnstile && widgetId !== null)
        ? window.turnstile.getResponse(widgetId) : ''; } catch (e) { return ''; }
    },
    reset() {
      try { if (window.turnstile && widgetId !== null) window.turnstile.reset(widgetId); }
      catch (e) {}
    }
  };
})();
