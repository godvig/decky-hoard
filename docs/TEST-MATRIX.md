# Manual test matrix (Gaming Mode)

Run after every change to the game-page patch. For each row: open the game from
the Library, wait 2 s, check both columns, then press the D-pad down/up once.

| Game | "Size on disk" in the stats row | Play/Install/Update button visible and focused |
|---|---|---|
| Steam game, internal drive, no mods | [ ] matches Steam's size | [ ] |
| Steam game on SD card | [ ] | [ ] |
| Steam game on extra library | [ ] | [ ] |
| Steam game with workshop mods | [ ] shows "+ X mods" | [ ] |
| Non-Steam folder game (~/Games/...) | [ ] | [ ] |
| Non-Steam game with Mod Organizer | [ ] shows "+ X mods" | [ ] |
| Emulated ROM (EmuDeck) | [ ] | [ ] |
| Not installed Steam game | [ ] no stat, no error | [ ] Install visible |
| Game with update pending | [ ] | [ ] Update visible |
| Same page with CSS Loader theme (Clean Gameview) on | [ ] | [ ] |

Also check:

- [ ] Library → sort by Size on disk: non-Steam games are in the list with sizes.
- [ ] Quick Access → Hoard: "Rescan now" goes to "Scanning..." and back.
- [ ] Disable the plugin in Decky settings: an open game page drops the stat,
      and Steam's sizes go back to the original ones.
- [ ] Controller: you can reach every button on the game page with the D-pad, and focus
      never lands on the size stat.

Quick Access panel (since Enable Hoard and Features):

- [ ] Turn **Enable Hoard** off with a game page open: the stat goes away, and Library → sort by
      Size on disk shows Steam's own sizes (non-Steam games without a size). Play is still visible
      and focused.
- [ ] Turn it back on: the stat and Hoard's sizes come back without a restart. Play is visible and
      focused.
- [ ] Restart Steam with Hoard off: it stays off, and no scan runs (the log has no "sized ..." line).
- [ ] With Hoard off, **Rescan now** is gone and the Features switches are greyed out.
- [ ] Features → each switch on its own: the size on the game page, Include mods in sorting
      (a modded Steam game sorts by its base size when off), Non-Steam scanning (the panel says
      it's off, shortcuts lose their size in the sort, and turning it on starts a scan).
- [ ] D-pad down from the top of the panel: Enable Hoard, Rescan now, Features, the feature
      switches when shown, then **Support on Ko-fi** last. Focus never lands on the version.
- [ ] **Support on Ko-fi** closes Quick Access and opens the Ko-fi page in Steam's browser. B goes back.

Update check:

- [ ] Fresh install: **Check for updates** is off and no Updates section shows.
- [ ] Turn it on: the Updates section appears and a check runs at once. On the latest release it
      says `Up to date (vX.Y.Z)` with the time of the check.
- [ ] With an older Hoard installed: `Update available: vX.Y.Z` and the install steps show.
      **Open release page** closes Quick Access and opens that release on GitHub. B goes back.
- [ ] Offline (Wi-Fi off), press **Check now**: no error, the label and last check stay as they were.
- [ ] Turn **Enable Hoard** off: the Updates section goes away, and no check runs.
- [ ] D-pad: **Support on Ko-fi** is still the last item you can focus.

## If something fails, paste back

1. The row from the table and the game's name.
2. The end of the plugin log:
   ```bash
   tail -50 ~/homebrew/logs/Hoard/"$(ls -t ~/homebrew/logs/Hoard | head -1)"
   ```
3. A screenshot (Steam + R1).
4. Leave the game page open, switch to Desktop Mode and tell Claude Code to inspect
   it over the CEF debug port (localhost:8080).

## Honest counts and Biggest games

- [ ] After updating, Hoard rescans once. The panel says `Sized X of Y games`, with emulators,
      web apps and launchers left out of Y.
- [ ] **Biggest games** lists ten games, largest first, no Proton or runtime among them, and an
      emulator or launcher never shows up even if it is large.
- [ ] D-pad onto a game in **Biggest games** and press A: Quick Access closes and the game's page
      opens, Steam or non-Steam. Play is visible and focused.
- [ ] **Game or not** → Show: emulators, apps and tools first. Switch one on: the counts go up by
      one and it says "set by you". Switch it off again: "set by you" goes away.
- [ ] **Show more** lists the games; switching one off takes it out of the counts and Biggest games.
- [ ] Turn Non-Steam scanning off: Biggest games and Game or not show Steam apps only.
- [ ] D-pad: **Support on Ko-fi** is still the last item you can focus, also with Game or not open.

## Faster scans

- [ ] Leave Hoard alone for a scan after the first: the log's "sized ..." line shows a shorter
      time than the first scan.
- [ ] Copy a 20 MB file into a Steam game without mods, in its top folder. After the next
      automatic scan (or Rescan now) the game page shows "+ 20 MB mods".
- [ ] **Rescan now** takes about as long as the first scan: everything is measured.

## Not played in X months

- [ ] The section title follows the slider: move it from 6 to 1 and to 36, and the list and the
      "you could free" sum change with it. The value is kept after a restart.
- [ ] A game you played this week is not in the list at 1 month. A game not played for a year is.
- [ ] No emulator, app or tool is in the list, however long since it was opened.
- [ ] **No play time recorded** shows games never played, and **Show** lists them. None of them is
      in the list above.
- [ ] Press A on a game in either list: Quick Access closes and its game page opens, with
      Uninstall reachable in Steam's own menu. Play is visible and focused.
- [ ] Features → Not played off: the section goes away. Features → Biggest games off: that one too.
- [ ] D-pad: the slider moves with left/right without leaving the row, and **Support on Ko-fi**
      is still the last item you can focus.
