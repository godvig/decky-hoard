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
- [ ] Quick Access → Non-Steam Sizes: "Rescan now" goes to "Scanning..." and back.
- [ ] Disable the plugin in Decky settings: an open game page drops the stat,
      and Steam's sizes go back to the original ones.
- [ ] Controller: you can reach every button on the game page with the D-pad, and focus
      never lands on the size stat.

## If something fails, paste back

1. The row from the table and the game's name.
2. The end of the plugin log:
   ```bash
   tail -50 ~/homebrew/logs/decky-nonsteam-sizes/"$(ls -t ~/homebrew/logs/decky-nonsteam-sizes | head -1)"
   ```
3. A screenshot (Steam + R1).
4. Leave the game page open, switch to Desktop Mode and tell Claude Code to inspect
   it over the CEF debug port (localhost:8080).
