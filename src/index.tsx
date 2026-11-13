import { addEventListener, callable, definePlugin, removeEventListener } from "@decky/api";
import { ButtonItem, Field, PanelSection, PanelSectionRow, staticClasses, ToggleField } from "@decky/ui";
import { useEffect, useState } from "react";

import { patchGamePage } from "./gamePage";
import { formatBytes, SizesState, store, totalBytes } from "./sizes";
import { applySizes, clearSizes, setSortOverrideEnabled } from "./sortOverride";

interface Settings {
  sort_override: boolean;
}

const getSizes = callable<[], SizesState>("get_sizes");
const rescan = callable<[], boolean>("rescan");
const getSettings = callable<[], Settings>("get_settings");
const setSetting = callable<[key: keyof Settings, value: boolean], Settings>("set_setting");

const REAPPLY_DELAY_MS = 1000;

let reapplyTimer: ReturnType<typeof setTimeout> | undefined;
let settings: Settings = { sort_override: true };

function scheduleApply() {
  clearTimeout(reapplyTimer);
  reapplyTimer = setTimeout(() => applySizes(store.get()), REAPPLY_DELAY_MS);
}

async function refresh() {
  const next = await getSizes();
  applySizes(next);
  store.set(next);
}

function Content() {
  const [state, setState] = useState(store.get);
  const [sortOverride, setSortOverride] = useState(settings.sort_override);
  const [starting, setStarting] = useState(false);

  useEffect(() => {
    const unsubscribe = store.subscribe(setState);
    refresh();
    return unsubscribe;
  }, []);

  const sized = Object.values(state.sizes).length;
  const unsized = Object.values(state.unsized).length;
  const busy = state.scanning || starting;
  const scanned = state.scanned_at ? new Date(state.scanned_at * 1000).toLocaleString() : "Not yet";

  return (
    <PanelSection title="Non-Steam games">
      <PanelSectionRow>
        <Field label="Sized">{`${sized} of ${sized + unsized}`}</Field>
      </PanelSectionRow>
      <PanelSectionRow>
        <Field label="Total">{formatBytes(totalBytes(state))}</Field>
      </PanelSectionRow>
      <PanelSectionRow>
        <Field label="Last scan">{scanned}</Field>
      </PanelSectionRow>
      <PanelSectionRow>
        <ToggleField
          label="Use in library sort"
          description="Size on disk sorting and filters include non-Steam games and mods."
          checked={sortOverride}
          onChange={async (value) => {
            setSortOverride(value);
            settings = await setSetting("sort_override", value);
            setSortOverrideEnabled(settings.sort_override, store.get());
          }}
        />
      </PanelSectionRow>
      <PanelSectionRow>
        <ButtonItem
          layout="below"
          disabled={busy}
          onClick={async () => {
            setStarting(true);
            await rescan();
            setStarting(false);
            refresh();
          }}
        >
          {busy ? "Scanning..." : "Rescan now"}
        </ButtonItem>
      </PanelSectionRow>
    </PanelSection>
  );
}

const icon = (
  <svg width="1em" height="1em" viewBox="0 0 24 24" fill="currentColor">
    <path d="M3 5h18v4H3zm0 5h18v4H3zm0 5h18v4H3zm13-9h2v2h-2zm0 5h2v2h-2zm0 5h2v2h-2z" />
  </svg>
);

export default definePlugin(() => {
  // Typed as void by @decky/ui, but Steam returns a handle to unregister with.
  const overviewChanges = SteamClient.Apps.RegisterForAppOverviewChanges(scheduleApply) as unknown as
    | { unregister?: () => void }
    | undefined;
  const unpatchGamePage = patchGamePage();
  const onSizesUpdated = addEventListener("sizes_updated", refresh);
  getSettings().then((saved) => {
    settings = saved;
    setSortOverrideEnabled(saved.sort_override, store.get());
  });
  refresh();

  return {
    name: "Hoard",
    titleView: <div className={staticClasses.Title}>Hoard</div>,
    icon,
    content: <Content />,
    onDismount() {
      overviewChanges?.unregister?.();
      unpatchGamePage();
      removeEventListener("sizes_updated", onSizesUpdated);
      clearTimeout(reapplyTimer);
      clearSizes();
      // An open game page keeps its last render until something changes it.
      store.set({ ...store.get(), removed: true });
    },
  };
});
