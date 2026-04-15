(() => {
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  const setDemoMode = (enabled) => {
    document.documentElement.classList.toggle("demo-mode", enabled);
    try {
      localStorage.setItem("group_meeting_report_demo_mode", enabled ? "1" : "0");
    } catch {}
  };

  const getSavedDemoMode = () => {
    try {
      return localStorage.getItem("group_meeting_report_demo_mode") === "1";
    } catch {
      return false;
    }
  };

  const renderMarkdown = () => {
    $$(".appendix-md").forEach((node) => {
      const tplId = node.getAttribute("data-md-template");
      const tpl = tplId ? $(`#${CSS.escape(tplId)}`) : null;
      const md = tpl ? tpl.innerHTML : "";
      node.innerHTML = window.marked ? window.marked.parse(md) : md;
      $$(".appendix-md pre code", node).forEach((code) => {
        if (window.hljs) window.hljs.highlightElement(code);
      });
    });
  };

  const highlightAllCode = () => {
    if (!window.hljs) return;
    $$("pre code").forEach((el) => window.hljs.highlightElement(el));
  };

  const buildTOC = () => {
    const toc = $("#toc");
    if (!toc) return;
    const sections = $$("[data-toc]");
    const frag = document.createDocumentFragment();

    let currentGroup = "";
    sections.forEach((sec) => {
      const group = sec.getAttribute("data-toc-group") || "";
      if (group !== currentGroup) {
        currentGroup = group;
        const g = document.createElement("div");
        g.className = "group";
        g.textContent = group;
        frag.appendChild(g);
      }

      const a = document.createElement("a");
      a.href = `#${sec.id}`;
      a.textContent = sec.getAttribute("data-toc") || sec.id;
      a.dataset.target = sec.id;
      frag.appendChild(a);
    });

    toc.innerHTML = "";
    toc.appendChild(frag);
  };

  const enableScrollSpy = () => {
    const toc = $("#toc");
    if (!toc) return;
    const links = $$("a[data-target]", toc);
    const byId = new Map(links.map((l) => [l.dataset.target, l]));

    const setActive = (id) => {
      links.forEach((l) => (l.dataset.active = l.dataset.target === id ? "true" : "false"));
    };

    let current = null;
    const obs = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => (a.boundingClientRect.top || 0) - (b.boundingClientRect.top || 0));
        if (!visible.length) return;
        const id = visible[0].target.id;
        if (id && id !== current && byId.has(id)) {
          current = id;
          setActive(id);
        }
      },
      { rootMargin: "-20% 0px -70% 0px", threshold: [0, 0.1, 0.2, 0.3] }
    );

    $$("[data-toc]").forEach((sec) => obs.observe(sec));

    const hash = location.hash ? location.hash.slice(1) : "";
    if (hash && byId.has(hash)) setActive(hash);
  };

  const wireControls = () => {
    const demoBtn = $("#btn-demo");
    if (demoBtn) {
      demoBtn.addEventListener("click", () => {
        const next = !document.documentElement.classList.contains("demo-mode");
        setDemoMode(next);
        demoBtn.setAttribute("aria-pressed", next ? "true" : "false");
      });
      const init = getSavedDemoMode();
      setDemoMode(init);
      demoBtn.setAttribute("aria-pressed", init ? "true" : "false");
    }

    const expandBtn = $("#btn-expand");
    if (expandBtn) {
      expandBtn.addEventListener("click", () => {
        const all = $$("details");
        const openCount = all.filter((d) => d.open).length;
        const shouldOpen = openCount < all.length * 0.65;
        all.forEach((d) => (d.open = shouldOpen));
      });
    }
  };

  const init = () => {
    if (window.marked) {
      const renderer = new window.marked.Renderer();
      renderer.link = (href, title, text) => {
        const label = text || href || "";
        const tail = href && href !== text ? `（${href}）` : "";
        const t = `${label}${tail}`;
        return `<span class="md-link">${window.marked.parseInline(t)}</span>`;
      };
      window.marked.setOptions({
        gfm: true,
        breaks: false,
        renderer,
      });
    }
    buildTOC();
    enableScrollSpy();
    wireControls();
    renderMarkdown();
    highlightAllCode();
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
