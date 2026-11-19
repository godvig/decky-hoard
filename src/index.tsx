import { addEventListener, callable, definePlugin, removeEventListener } from "@decky/api";
import { ButtonItem, Field, Navigation, PanelSection, PanelSectionRow, staticClasses, ToggleField } from "@decky/ui";
import { useEffect, useState } from "react";

import { patchGamePage } from "./gamePage";
import { Settings, settingsStore, shownState, sortOverrideOn } from "./settings";
import { formatBytes, SizesState, store, totalBytes } from "./sizes";
import { applySizes, clearSizes, setSortOverrideEnabled } from "./sortOverride";
import { KOFI_URL, strings } from "./strings";

const getSizes = callable<[], SizesState>("get_sizes");
const rescan = callable<[], boolean>("rescan");
const getSettings = callable<[], Settings>("get_settings");
const setSetting = callable<[key: keyof Settings, value: boolean], Settings>("set_setting");
const getVersion = callable<[], string>("get_version");

const REAPPLY_DELAY_MS = 1000;

let reapplyTimer: ReturnType<typeof setTimeout> | undefined;
let unpatchGamePage: (() => void) | undefined;

function apply() {
  applySizes(shownState(store.get(), settingsStore.get()));
}

function scheduleApply() {
  clearTimeout(reapplyTimer);
  reapplyTimer = setTimeout(apply, REAPPLY_DELAY_MS);
}

async function refresh() {
  store.set(await getSizes());
  apply();
}

// Brings every feature in line with the settings. With Hoard off, Steam is left as stock:
// its own sizes, and no patch on the game page.
function applySettings(next: Settings) {
  settingsStore.set(next);
  setSortOverrideEnabled(sortOverrideOn(next), shownState(store.get(), next));
  if (next.enabled && !unpatchGamePage) unpatchGamePage = patchGamePage();
  if (!next.enabled && unpatchGamePage) {
    unpatchGamePage();
    unpatchGamePage = undefined;
  }
}

async function changeSetting(key: keyof Settings, value: boolean) {
  applySettings({ ...settingsStore.get(), [key]: value });
  applySettings(await setSetting(key, value));
  // Turning something on can start a scan.
  refresh();
}

function FeatureToggle({ setting, label, description }: { setting: keyof Settings; label: string; description: string }) {
  const [settings, setSettings] = useState(settingsStore.get);

  useEffect(() => settingsStore.subscribe(setSettings), []);

  return (
    <PanelSectionRow>
      <ToggleField
        label={label}
        description={description}
        checked={settings[setting]}
        disabled={!settings.enabled}
        onChange={(value) => changeSetting(setting, value)}
      />
    </PanelSectionRow>
  );
}

function Content() {
  const [state, setState] = useState(store.get);
  const [settings, setSettings] = useState(settingsStore.get);
  const [starting, setStarting] = useState(false);
  const [featuresOpen, setFeaturesOpen] = useState(false);
  const [version, setVersion] = useState("");

  useEffect(() => {
    const unsubscribeSizes = store.subscribe(setState);
    const unsubscribeSettings = settingsStore.subscribe(setSettings);
    refresh();
    getVersion().then(setVersion);
    return () => {
      unsubscribeSizes();
      unsubscribeSettings();
    };
  }, []);

  const shown = shownState(state, settings);
  const sized = Object.values(shown.sizes).length;
  const unsized = Object.values(shown.unsized).length;
  const busy = state.scanning || starting;
  const scanned = state.scanned_at ? new Date(state.scanned_at * 1000).toLocaleString() : strings.notYet;

  return (
    <>
      <PanelSection>
        <PanelSectionRow>
          <ToggleField
            label={strings.enable}
            description={settings.enabled ? strings.enableDescription : strings.offNotice}
            checked={settings.enabled}
            onChange={(value) => changeSetting("enabled", value)}
          />
        </PanelSectionRow>
      </PanelSection>
      {settings.enabled && (
        <PanelSection title={strings.shortcutsTitle}>
          {settings.scan_shortcuts ? (
            <>
              <PanelSectionRow>
                <Field label={strings.sized}>{`${sized} of ${sized + unsized}`}</Field>
              </PanelSectionRow>
              <PanelSectionRow>
                <Field label={strings.total}>{formatBytes(totalBytes(shown))}</Field>
              </PanelSectionRow>
            </>
          ) : (
            <PanelSectionRow>
              <Field label={strings.shortcutsOff} />
            </PanelSectionRow>
          )}
          <PanelSectionRow>
            <Field label={strings.lastScan}>{scanned}</Field>
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
              {busy ? strings.scanning : strings.rescan}
            </ButtonItem>
          </PanelSectionRow>
        </PanelSection>
      )}
      <PanelSection>
        <PanelSectionRow>
          <ButtonItem layout="inline" label={strings.features} onClick={() => setFeaturesOpen(!featuresOpen)}>
            {featuresOpen ? strings.hide : strings.show}
          </ButtonItem>
        </PanelSectionRow>
        {featuresOpen && (
          <>
            <FeatureToggle setting="size_label" label={strings.sizeLabel} description={strings.sizeLabelDescription} />
            <FeatureToggle setting="sort_override" label={strings.includeMods} description={strings.includeModsDescription} />
            <FeatureToggle setting="scan_shortcuts" label={strings.scanShortcuts} description={strings.scanShortcutsDescription} />
          </>
        )}
      </PanelSection>
      {/* Keep this section last: the Ko-fi button is meant to be the panel's last stop. */}
      <PanelSection>
        <PanelSectionRow>
          <Field description={strings.support} bottomSeparator="none" />
        </PanelSectionRow>
        <PanelSectionRow>
          <ButtonItem
            layout="below"
            onClick={() => {
              Navigation.CloseSideMenus();
              Navigation.NavigateToExternalWeb(KOFI_URL);
            }}
          >
            {strings.supportButton}
          </ButtonItem>
        </PanelSectionRow>
        <PanelSectionRow>
          <Field label={strings.version}>{version}</Field>
        </PanelSectionRow>
      </PanelSection>
    </>
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
  const onSizesUpdated = addEventListener("sizes_updated", refresh);
  getSettings().then(applySettings);
  refresh();

  return {
    name: "Hoard",
    titleView: <div className={staticClasses.Title}>Hoard</div>,
    icon,
    content: <Content />,
    onDismount() {
      overviewChanges?.unregister?.();
      unpatchGamePage?.();
      unpatchGamePage = undefined;
      removeEventListener("sizes_updated", onSizesUpdated);
      clearTimeout(reapplyTimer);
      clearSizes();
      // An open game page keeps its last render until something changes it.
      store.set({ ...store.get(), removed: true });
    },
  };
});
