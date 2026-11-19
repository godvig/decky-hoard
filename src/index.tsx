import { addEventListener, callable, definePlugin, removeEventListener } from "@decky/api";
import { ButtonItem, Field, Navigation, PanelSection, PanelSectionRow, SliderField, staticClasses, ToggleField } from "@decky/ui";
import { useEffect, useState } from "react";

import { patchGamePage } from "./gamePage";
import { Settings, settingsStore, shownState, sortOverrideOn, Switch } from "./settings";
import { Entry, formatBytes, ModsOverview, NotPlayed, RankedGame, SizesState, store, totalBytes } from "./sizes";
import { applySizes, appTypes, clearSizes, lastPlayed, setSortOverrideEnabled } from "./sortOverride";
import { KOFI_URL, strings } from "./strings";

interface UpdateInfo {
  current: string;
  latest: string | null;
  checked_at: number;
  checking: boolean;
  available: boolean;
  // Built by the backend from the checked version, never taken from GitHub's reply.
  url: string | null;
}

const getSizes = callable<[], SizesState>("get_sizes");
const rescan = callable<[], boolean>("rescan");
const getSettings = callable<[], Settings>("get_settings");
const setSetting = callable<[key: keyof Settings, value: boolean | number], Settings>("set_setting");
const getVersion = callable<[], string>("get_version");
const getUpdate = callable<[], UpdateInfo>("get_update");
const checkUpdatesNow = callable<[], UpdateInfo>("check_updates_now");
const setAppTypes = callable<[types: Record<string, number>], boolean>("set_app_types");
const setLastPlayed = callable<[times: Record<string, number>], boolean>("set_last_played");
const setCountsAsGame = callable<[appid: string, counts: boolean], SizesState>("set_counts_as_game");

const REAPPLY_DELAY_MS = 1000;

let reapplyTimer: ReturnType<typeof setTimeout> | undefined;
let unpatchGamePage: (() => void) | undefined;
let reported = "";

function apply() {
  applySizes(shownState(store.get(), settingsStore.get()));
}

function scheduleApply() {
  clearTimeout(reapplyTimer);
  reapplyTimer = setTimeout(apply, REAPPLY_DELAY_MS);
}

async function refresh() {
  let next = await getSizes();
  // Only the frontend can ask Steam what an app is and when it was last played. What that
  // means is the backend's call.
  const types = appTypes(Object.keys(next.steam ?? {}));
  const times = lastPlayed([...Object.keys(next.steam ?? {}), ...Object.keys(next.sizes ?? {})]);
  if (JSON.stringify([types, times]) !== reported) {
    reported = JSON.stringify([types, times]);
    await Promise.all([setAppTypes(types), setLastPlayed(times)]);
    next = await getSizes();
  }
  store.set(next);
  apply();
}

function openGamePage(appid: string) {
  Navigation.CloseSideMenus();
  Navigation.Navigate(`/library/app/${appid}`);
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

async function changeSetting(key: keyof Settings, value: boolean | number) {
  applySettings({ ...settingsStore.get(), [key]: value });
  applySettings(await setSetting(key, value));
  // Turning something on can start a scan.
  refresh();
}

function FeatureToggle({ setting, label, description }: { setting: Switch; label: string; description: string }) {
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

// Never says "up to date" without an answer from GitHub to back it.
function updateLabel(info: UpdateInfo): string {
  if (!info.latest) return strings.latestUnknown;
  return info.available ? strings.updateAvailable(info.latest) : strings.upToDate(info.current);
}

// Shown only with "Check for updates" on. It only tells: installing stays the user's job.
function UpdateSection() {
  const [info, setInfo] = useState<UpdateInfo | null>(null);
  const [checking, setChecking] = useState(false);

  useEffect(() => {
    const load = () => getUpdate().then(setInfo);
    const listener = addEventListener("updates_changed", load);
    load();
    return () => {
      removeEventListener("updates_changed", listener);
    };
  }, []);

  if (!info) return null;
  const busy = checking || info.checking;
  const checked = info.checked_at ? new Date(info.checked_at * 1000).toLocaleString() : strings.notChecked;

  return (
    <PanelSection title={strings.updatesTitle}>
      <PanelSectionRow>
        <Field
          label={updateLabel(info)}
          description={info.available ? strings.updateHowTo : undefined}
        />
      </PanelSectionRow>
      <PanelSectionRow>
        <Field label={strings.lastChecked}>{checked}</Field>
      </PanelSectionRow>
      {info.available && info.url && (
        <PanelSectionRow>
          <ButtonItem
            layout="below"
            onClick={() => {
              Navigation.CloseSideMenus();
              Navigation.NavigateToExternalWeb(info.url as string);
            }}
          >
            {strings.openRelease}
          </ButtonItem>
        </PanelSectionRow>
      )}
      <PanelSectionRow>
        <ButtonItem
          layout="below"
          disabled={busy}
          onClick={async () => {
            setChecking(true);
            setInfo(await checkUpdatesNow());
            setChecking(false);
          }}
        >
          {busy ? strings.checking : strings.checkNow}
        </ButtonItem>
      </PanelSectionRow>
    </PanelSection>
  );
}

function BiggestGames({ games }: { games: RankedGame[] }) {
  return (
    <PanelSection title={strings.biggestTitle}>
      {games.length === 0 && (
        <PanelSectionRow>
          <Field label={strings.noGames} />
        </PanelSectionRow>
      )}
      {games.map((game) => (
        <GameRow
          key={game.appid}
          game={game}
          description={[strings.sources[game.source] ?? game.source, game.mods > 0 ? strings.withMods(formatBytes(game.mods)) : null]
            .filter(Boolean)
            .join(" · ")}
        />
      ))}
    </PanelSection>
  );
}

function GameRow({ game, description }: { game: RankedGame; description: string }) {
  return (
    <PanelSectionRow>
      <Field label={game.name} description={description} focusable highlightOnFocus onActivate={() => openGamePage(game.appid)}>
        {formatBytes(game.bytes)}
      </Field>
    </PanelSectionRow>
  );
}

// Read-only: selecting a game opens its page, where Steam's own Uninstall is.
function NotPlayedGames({ found, months }: { found: NotPlayed; months: number }) {
  const [showAll, setShowAll] = useState(false);
  const [showUnknown, setShowUnknown] = useState(false);
  const shown = showAll ? found.games : found.games.slice(0, 10);

  return (
    <PanelSection title={strings.notPlayedTitle(months)}>
      <PanelSectionRow>
        <SliderField
          label={strings.months}
          value={months}
          min={1}
          max={36}
          step={1}
          showValue
          onChange={(value) => changeSetting("stale_months", value)}
        />
      </PanelSectionRow>
      <PanelSectionRow>
        <Field label={strings.couldFree(found.games.length, formatBytes(found.bytes))} />
      </PanelSectionRow>
      {shown.map((game) => (
        <GameRow
          key={game.appid}
          game={game}
          description={strings.lastPlayedOn(new Date(game.last_played * 1000).toLocaleDateString())}
        />
      ))}
      {!showAll && found.games.length > shown.length && (
        <PanelSectionRow>
          <ButtonItem layout="below" onClick={() => setShowAll(true)}>
            {strings.showAll(found.games.length - shown.length)}
          </ButtonItem>
        </PanelSectionRow>
      )}
      {found.unknown.length > 0 && (
        <PanelSectionRow>
          <ButtonItem
            layout="below"
            label={strings.noPlayTime(found.unknown.length, formatBytes(found.unknown_bytes))}
            description={strings.noPlayTimeDescription}
            onClick={() => setShowUnknown(!showUnknown)}
          >
            {showUnknown ? strings.hide : strings.showGames(found.unknown.length)}
          </ButtonItem>
        </PanelSectionRow>
      )}
      {showUnknown &&
        found.unknown.map((game) => <GameRow key={game.appid} game={game} description={strings.sources[game.source] ?? game.source} />)}
    </PanelSection>
  );
}

// A game with mods: press A to see where they are, as Hoard found them.
function ModdedGame({ game }: { game: ModsOverview["games"][number] }) {
  const [open, setOpen] = useState(false);
  const places = [...new Set((game.mod_parts ?? []).map((part) => strings.where[part.where] ?? part.where))].join(", ");
  return (
    <>
      <PanelSectionRow>
        <Field
          label={game.name}
          description={`${strings.modsShare(Math.round(game.share * 100), formatBytes(game.bytes))} · ${places}`}
          focusable
          highlightOnFocus
          onActivate={() => setOpen(!open)}
        >
          {formatBytes(game.mods)}
        </Field>
      </PanelSectionRow>
      {open &&
        (game.mod_parts ?? []).map((part) => (
          <PanelSectionRow key={part.shown}>
            <Field
              indentLevel={1}
              label={strings.where[part.where] ?? part.where}
              description={part.where === "loose" ? `${part.shown} · ${strings.looseNote}` : part.shown}
            >
              {formatBytes(part.bytes)}
            </Field>
          </PanelSectionRow>
        ))}
    </>
  );
}

function ModsSection({ overview }: { overview: ModsOverview }) {
  const [showAll, setShowAll] = useState(false);
  const shown = showAll ? overview.games : overview.games.slice(0, 10);
  return (
    <PanelSection title={strings.modsTitle}>
      <PanelSectionRow>
        <Field
          label={overview.games.length ? strings.modsSummary(overview.games.length, formatBytes(overview.bytes)) : strings.modsNone}
          description={strings.modsHowTo}
        />
      </PanelSectionRow>
      {shown.map((game) => (
        <ModdedGame key={game.appid} game={game} />
      ))}
      {!showAll && overview.games.length > shown.length && (
        <PanelSectionRow>
          <ButtonItem layout="below" onClick={() => setShowAll(true)}>
            {strings.showAll(overview.games.length - shown.length)}
          </ButtonItem>
        </PanelSectionRow>
      )}
    </PanelSection>
  );
}

function EntryToggle({ entry }: { entry: Entry }) {
  const description = [strings.kinds[entry.kind], entry.guessed ? strings.guessed : null, entry.overridden ? strings.setByYou : null]
    .filter(Boolean)
    .join(" · ");
  return (
    <PanelSectionRow>
      <ToggleField
        label={entry.name}
        description={description}
        checked={entry.kind === "game"}
        onChange={async (value) => {
          store.set(await setCountsAsGame(entry.appid, value));
          apply();
        }}
      />
    </PanelSectionRow>
  );
}

// Every entry with a "counts as a game" switch: the ones worth a look first, the rest on request.
function GameOrNot({ entries }: { entries: Entry[] }) {
  const [open, setOpen] = useState(false);
  const [showAll, setShowAll] = useState(false);
  const review = entries.filter((entry) => entry.review);
  const rest = entries.filter((entry) => !entry.review);

  return (
    <PanelSection>
      <PanelSectionRow>
        <ButtonItem layout="inline" label={strings.gameOrNot} description={open ? strings.gameOrNotDescription : undefined} onClick={() => setOpen(!open)}>
          {open ? strings.hide : strings.show}
        </ButtonItem>
      </PanelSectionRow>
      {open && review.map((entry) => <EntryToggle key={entry.appid} entry={entry} />)}
      {open && !showAll && rest.length > 0 && (
        <PanelSectionRow>
          <ButtonItem layout="below" onClick={() => setShowAll(true)}>
            {strings.showAll(rest.length)}
          </ButtonItem>
        </PanelSectionRow>
      )}
      {open && showAll && rest.map((entry) => <EntryToggle key={entry.appid} entry={entry} />)}
    </PanelSection>
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
  const counts = shown.counts ?? { shortcut_games: 0, sized_shortcut_games: 0, guessed: 0 };
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
                <Field label={strings.sized}>{strings.sizedOf(counts.sized_shortcut_games, counts.shortcut_games)}</Field>
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
      {settings.enabled && settings.biggest_games && <BiggestGames games={shown.biggest ?? []} />}
      {settings.enabled && settings.not_played && shown.not_played && (
        <NotPlayedGames found={shown.not_played} months={settings.stale_months} />
      )}
      {settings.enabled && settings.mods_overview && shown.mods && <ModsSection overview={shown.mods} />}
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
            <FeatureToggle setting="biggest_games" label={strings.biggestGames} description={strings.biggestGamesDescription} />
            <FeatureToggle setting="not_played" label={strings.notPlayed} description={strings.notPlayedDescription} />
            <FeatureToggle setting="mods_overview" label={strings.modsOverview} description={strings.modsOverviewDescription} />
            <FeatureToggle setting="check_updates" label={strings.checkUpdates} description={strings.checkUpdatesDescription} />
          </>
        )}
      </PanelSection>
      {settings.enabled && <GameOrNot entries={shown.entries ?? []} />}
      {settings.enabled && settings.check_updates && <UpdateSection />}
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
