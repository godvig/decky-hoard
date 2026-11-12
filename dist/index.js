// Hand-written ES module, so there is no build step: Decky loads this file as is.
const manifest = { name: "Non-Steam Sizes" };
const connection = window.__DECKY_SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED_deckyLoaderAPIInit;
const api = connection.connect(2, manifest.name);

const { Fragment, useEffect, useRef, useState } = SP_REACT;
const { createPortal } = SP_REACTDOM;
const { jsx, jsxs } = SP_JSX;
const {
  afterPatch,
  appDetailsClasses,
  ButtonItem,
  createReactTreePatcher,
  Field,
  findInReactTree,
  PanelSection,
  PanelSectionRow,
  playSectionClasses,
  staticClasses,
} = DFL;

const getSizes = api.callable("get_sizes");
const rescan = api.callable("rescan");

const STEAM_GAME_APP_TYPE = 1;
const THIRD_PARTY_APP_TYPE = 1073741824;
const GAME_PAGE_ROUTE = "/library/app/:appid";
const REAPPLY_DELAY_MS = 1000;
const SIZE_STAT_KEY = "nonsteam-sizes";
// Below this the stats row wraps, and a wrapped stat ends up hidden behind the footer.
const FULL_TEXT_MIN_WIDTH = 600;
const MISSING_SECTION_WARN_MS = 5000;

let latest = { sizes: {}, unsized: {}, steam: {}, scanned_at: 0, scanning: false };
// Appid to the value Steam had before we changed it.
const patched = new Map();
const listeners = new Set();
let reapplyTimer = null;
let warnedMissingSection = false;

// Steam's size sort and "size on disk" sections read this field straight from
// each app's overview. It lives in memory only, so nothing is written to Steam.
function setSize(appid, appType, bytes) {
  const overview = appStore.GetAppOverviewByAppID(Number(appid));
  if (overview?.app_type !== appType) return;
  if (!patched.has(overview.appid)) patched.set(overview.appid, overview.size_on_disk);
  const value = String(bytes);
  if (overview.size_on_disk !== value) overview.size_on_disk = value;
}

function restoreSize(appid) {
  const overview = appStore.GetAppOverviewByAppID(appid);
  if (overview) overview.size_on_disk = patched.get(appid);
  patched.delete(appid);
}

function applySizes() {
  if (typeof appStore === "undefined") return;
  for (const [appid, info] of Object.entries(latest.sizes)) {
    setSize(appid, THIRD_PARTY_APP_TYPE, info.bytes);
  }
  // Steam's own number already is right for a Steam game without mods.
  for (const [appid, info] of Object.entries(latest.steam ?? {})) {
    if (info.mods > 0) setSize(appid, STEAM_GAME_APP_TYPE, info.base + info.mods);
    else if (patched.has(Number(appid))) restoreSize(Number(appid));
  }
}

function clearSizes() {
  for (const appid of [...patched.keys()]) restoreSize(appid);
}

function scheduleApply() {
  clearTimeout(reapplyTimer);
  reapplyTimer = setTimeout(applySizes, REAPPLY_DELAY_MS);
}

async function refresh() {
  latest = await getSizes();
  applySizes();
  listeners.forEach((listener) => listener(latest));
}

function formatBytes(bytes) {
  const gib = bytes / 1024 ** 3;
  if (gib >= 1024) return `${(gib / 1024).toFixed(2)} TB`;
  return gib >= 1 ? `${gib.toFixed(1)} GB` : `${Math.round(bytes / 1024 ** 2)} MB`;
}

function sizeText(state, overview, compact) {
  const info = state.sizes[overview.appid] ?? state.steam?.[overview.appid];
  if (info?.base !== undefined) {
    const mods = info.mods > 0 ? `+ ${formatBytes(info.mods)} mods` : "(no mods)";
    return `${formatBytes(info.base)}${compact ? "" : " game"} ${mods}`;
  }
  // A Steam game installed since the last scan: its mods aren't measured yet.
  const bytes = Number(overview.size_on_disk);
  return overview.app_type !== THIRD_PARTY_APP_TYPE && bytes > 0 ? formatBytes(bytes) : null;
}

// The row with Last Played and Play Time, found from a hidden element on the same page.
// Steam can replace it while the page stays open, so keep looking for it.
function useStatsSection() {
  const anchor = useRef(null);
  const [section, setSection] = useState(null);

  useEffect(() => {
    const page = anchor.current?.parentElement;
    if (!page) return undefined;
    const find = () => setSection(page.querySelector(`.${playSectionClasses.GameStatsSection}`));
    const observer = new MutationObserver(find);
    observer.observe(page, { childList: true, subtree: true });
    find();
    // Steam renaming its classes would otherwise hide the stat without a trace.
    const check = setTimeout(() => {
      if (!warnedMissingSection && !page.querySelector(`.${playSectionClasses.GameStatsSection}`)) {
        warnedMissingSection = true;
        console.warn(`[${manifest.name}] stats row not found on the game page, size stat is hidden`);
      }
    }, MISSING_SECTION_WARN_MS);
    return () => {
      observer.disconnect();
      clearTimeout(check);
    };
  }, []);

  return [anchor, section];
}

// Rendered inside Steam's stats row because the page has no spare height: themes
// such as Clean Gameview size the header to fit the play bar exactly above the
// footer, and paint the hero image over anything placed between them.
function SizeStat({ overview }) {
  const [state, setState] = useState(latest);
  const [anchor, section] = useStatsSection();

  useEffect(() => {
    listeners.add(setState);
    return () => listeners.delete(setState);
  }, []);

  const text = state.removed ? null : sizeText(state, overview, section?.clientWidth < FULL_TEXT_MIN_WIDTH);
  const stat = jsx("div", {
    className: `${playSectionClasses.GameStat} ${playSectionClasses.LastPlayed}`,
    // Steam can add its own stats after ours, so keep this one last in the row.
    style: { order: 1 },
    children: jsxs("div", {
      className: `${playSectionClasses.GameStatRight} ${playSectionClasses.LastPlayedRight}`,
      children: [
        jsx("div", { className: playSectionClasses.PlayBarLabel, children: "Size on disk" }),
        jsx("div", { className: playSectionClasses.PlayBarDetailLabel, children: text }),
      ],
    }),
  });

  return jsxs(Fragment, {
    children: [
      jsx("span", { ref: anchor, style: { display: "none" } }),
      section && text ? createPortal(stat, section) : null,
    ],
  });
}

// Same route as other plugins that add to the game page.
function patchGamePage() {
  const patchedRoutes = new WeakSet();
  const patcher = createReactTreePatcher(
    [(tree) => findInReactTree(tree, (node) => node?.props?.children?.props?.overview)?.props?.children ?? null],
    ([{ overview }], rendered) => {
      const rows = findInReactTree(
        rendered,
        (node) => Array.isArray(node?.props?.children) && node?.props?.className?.includes(appDetailsClasses.InnerContainer),
      )?.props?.children;
      if (rows && !rows.some((row) => row?.key === SIZE_STAT_KEY)) {
        rows.push(jsx(SizeStat, { overview }, SIZE_STAT_KEY));
      }
      return rendered;
    },
  );
  return api.routerHook.addPatch(GAME_PAGE_ROUTE, (routerTree) => {
    const route = findInReactTree(routerTree, (node) => node?.renderFunc);
    if (route && !patchedRoutes.has(route)) {
      patchedRoutes.add(route);
      afterPatch(route, "renderFunc", patcher);
    }
    return routerTree;
  });
}

function Content() {
  const [state, setState] = useState(latest);
  const [starting, setStarting] = useState(false);

  useEffect(() => {
    listeners.add(setState);
    refresh();
    return () => listeners.delete(setState);
  }, []);

  const sized = Object.values(state.sizes);
  const unsized = Object.values(state.unsized);
  const total = state.total_bytes ?? sized.reduce((sum, item) => sum + item.bytes, 0);
  const busy = state.scanning || starting;
  const scanned = state.scanned_at ? new Date(state.scanned_at * 1000).toLocaleString() : "Not yet";

  return jsxs(PanelSection, {
    title: "Non-Steam games",
    children: [
      jsx(PanelSectionRow, { children: jsx(Field, { label: "Sized", children: `${sized.length} of ${sized.length + unsized.length}` }) }),
      jsx(PanelSectionRow, { children: jsx(Field, { label: "Total", children: formatBytes(total) }) }),
      jsx(PanelSectionRow, { children: jsx(Field, { label: "Last scan", children: scanned }) }),
      jsx(PanelSectionRow, {
        children: jsx(ButtonItem, {
          layout: "below",
          disabled: busy,
          onClick: async () => {
            setStarting(true);
            await rescan();
            setStarting(false);
            refresh();
          },
          children: busy ? "Scanning..." : "Rescan now",
        }),
      }),
    ],
  });
}

const icon = jsx("svg", {
  width: "1em",
  height: "1em",
  viewBox: "0 0 24 24",
  fill: "currentColor",
  children: jsx("path", { d: "M3 5h18v4H3zm0 5h18v4H3zm0 5h18v4H3zm13-9h2v2h-2zm0 5h2v2h-2zm0 5h2v2h-2z" }),
});

export default function plugin() {
  const overviewChanges = SteamClient.Apps.RegisterForAppOverviewChanges(scheduleApply);
  const gamePagePatch = patchGamePage();
  api.addEventListener("sizes_updated", refresh);
  refresh();

  return {
    name: manifest.name,
    title: jsx("div", { className: staticClasses.Title, children: manifest.name }),
    icon,
    content: jsx(Content, {}),
    onDismount() {
      overviewChanges?.unregister?.();
      api.routerHook.removePatch(GAME_PAGE_ROUTE, gamePagePatch);
      api.removeEventListener("sizes_updated", refresh);
      clearTimeout(reapplyTimer);
      clearSizes();
      // An open game page keeps its last render until something changes it.
      listeners.forEach((listener) => listener({ ...latest, removed: true }));
    },
  };
}
