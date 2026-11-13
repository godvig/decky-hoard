import { routerHook } from "@decky/api";
import { afterPatch, appDetailsClasses, createReactTreePatcher, findInReactTree, playSectionClasses } from "@decky/ui";
import { ReactElement, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

import { OverviewLike, sizeText, store } from "./sizes";

const GAME_PAGE_ROUTE = "/library/app/:appid";
const SIZE_STAT_KEY = "hoard-size";
// Below this the stats row wraps, and a wrapped stat ends up hidden behind the footer.
const FULL_TEXT_MIN_WIDTH = 600;
const MISSING_SECTION_WARN_MS = 5000;

let warnedMissingSection = false;

interface TreeNode {
  key?: unknown;
  renderFunc?: unknown;
  props?: { children?: unknown; className?: string; overview?: OverviewLike };
}

// The row with Last Played and Play Time, found from a hidden element on the same page.
// Steam can replace it while the page stays open, so keep looking for it.
function useStatsSection() {
  const anchor = useRef<HTMLSpanElement>(null);
  const [section, setSection] = useState<HTMLElement | null>(null);

  useEffect(() => {
    const page = anchor.current?.parentElement;
    if (!page) return undefined;
    const selector = `.${playSectionClasses.GameStatsSection}`;
    const find = () => setSection(page.querySelector<HTMLElement>(selector));
    const observer = new MutationObserver(find);
    observer.observe(page, { childList: true, subtree: true });
    find();
    // Steam renaming its classes would otherwise hide the stat without a trace.
    const check = setTimeout(() => {
      if (!warnedMissingSection && !page.querySelector(selector)) {
        warnedMissingSection = true;
        console.warn("[Hoard] stats row not found on the game page, size stat is hidden");
      }
    }, MISSING_SECTION_WARN_MS);
    return () => {
      observer.disconnect();
      clearTimeout(check);
    };
  }, []);

  return [anchor, section] as const;
}

// Rendered inside Steam's stats row because the page has no spare height: themes
// such as Clean Gameview size the header to fit the play bar exactly above the
// footer, and paint the hero image over anything placed between them.
function SizeStat({ overview }: { overview: OverviewLike }) {
  const [state, setState] = useState(store.get);
  const [anchor, section] = useStatsSection();

  useEffect(() => store.subscribe(setState), []);

  const compact = section !== null && section.clientWidth < FULL_TEXT_MIN_WIDTH;
  const text = state.removed ? null : sizeText(state, overview, compact);
  const stat = (
    // Steam can add its own stats after ours, so keep this one last in the row.
    <div className={`${playSectionClasses.GameStat} ${playSectionClasses.LastPlayed}`} style={{ order: 1 }}>
      <div className={playSectionClasses.GameStatRight}>
        <div className={playSectionClasses.PlayBarLabel}>Size on disk</div>
        <div className={playSectionClasses.PlayBarDetailLabel}>{text}</div>
      </div>
    </div>
  );

  return (
    <>
      <span ref={anchor} style={{ display: "none" }} />
      {section && text ? createPortal(stat, section) : null}
    </>
  );
}

// Same route as other plugins that add to the game page. Returns the undo.
export function patchGamePage(): () => void {
  const patchedRoutes = new WeakSet<object>();
  const patcher = createReactTreePatcher(
    [(tree: unknown) => findInReactTree(tree, (node: TreeNode) => !!(node?.props?.children as TreeNode | undefined)?.props?.overview)?.props?.children ?? null],
    ([{ overview }]: { overview: OverviewLike }[], rendered: unknown) => {
      const rows = findInReactTree(
        rendered,
        (node: TreeNode) => Array.isArray(node?.props?.children) && !!node?.props?.className?.includes(appDetailsClasses.InnerContainer),
      )?.props?.children as ReactElement[] | undefined;
      // Insert next to Steam's rows, never in place of one.
      if (rows && !rows.some((row) => row?.key === SIZE_STAT_KEY)) {
        rows.push(<SizeStat key={SIZE_STAT_KEY} overview={overview} />);
      }
      return rendered;
    },
  );
  const routePatch = routerHook.addPatch(GAME_PAGE_ROUTE, (routerTree) => {
    const route = findInReactTree(routerTree, (node: TreeNode) => !!node?.renderFunc);
    if (route && !patchedRoutes.has(route)) {
      patchedRoutes.add(route);
      afterPatch(route, "renderFunc", patcher);
    }
    return routerTree;
  });
  return () => routerHook.removePatch(GAME_PAGE_ROUTE, routePatch);
}
