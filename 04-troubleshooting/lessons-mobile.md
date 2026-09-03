# Mobile lessons — things learned by breaking them

The mobile counterpart. Heavier on native-platform behaviour, because that
is where the surprises are: layout rules that clamp silently, iOS view
semantics that clip children nobody asked to clip, and build-toolchain
interactions that produce errors naming the wrong cause.

Selected from `zelbi.ai/mobile/lessons.md` (404 lines, 325 dated entries) at commit `3413d028`. Each bullet is **verbatim**; `L<n>` is its line number in the
source file. Nothing was reworded.

- `L7` — 2026-08-20 — A rounded rectangle cannot round beyond half its own short side, so raising a hole's corner radius above that clamps and changes nothing; to enlarge a rounded highlight, inflate its RECT, never its radius.
- `L8` — 2026-08-20 — An icon glyph rendered at exactly its container's size cannot centre, because the glyph is drawn as text whose line box is taller than its nominal size; every icon box needs slack on all four sides.
- `L9` — 2026-08-20 — A shadow plus borderRadius on the same iOS view clips children to its rounded bounds even with overflow never set to hidden — a badge overhanging near a rounded end gets cut by that curve.
- `L11` — 2026-07-01 — Never delete package-lock.json to "reinstall"; npm install then re-resolves and can pull an incompatible transitive (e.g. reanimated 4.5.0 vs RN 0.81.5), breaking the tree. Recover a broken node_modules by restoring package.json + package-lock.json from the last commit, then npm ci.
- `L55` — 2026-05-12 — NativeTabs "hidden" prop is NOT a render-hide; per Expo Router docs "Marking a tab as hidden means it cannot be navigated to in any way." Any flow needing hidden-but-pushable destinations must live outside NativeTabs scope (root-level Stack with fullScreenModal presentation is the idiom).
- `L59` — 2026-05-12 — Anthropic 529 `overloaded_error` events do not always appear on `status.claude.com`. The public status page covers the Console UI, not the Messages API. `uvicorn` log at `/tmp/zelbi_uvicorn.log` is the only reliable signal.
- `L61` — 2026-05-12 — When AI is the product's core value proposition, manual-entry graceful degradation is not an acceptable fallback. Provider redundancy is a pre-launch architectural requirement, not a nice-to-have.
- `L65` — 2026-05-12 — iOS `Stack.Screen presentation='fullScreenModal'` creates a separate native UIViewController hierarchy; root-level providers (`KeyboardProvider`) cannot reach into the modal's sibling tree — diagnostic signature is zero behavioral change (vs wrong prop value = wrong behavior); fix is `presentation='card'` or nest a fresh provider inside the modal layout; cost of misdiagnosis: five sessions, four attempts in the wrong layer.
- `L114` — 2026-05-16 — EAS dev client URL is exp+mobile://expo-development-client/?url=http%3A%2F%2F<ip>%3A%2F<port> not http://<ip>:<port>; the latter is Expo Go legacy form and triggers "Failed to connect to http://..." error in dev launcher.
- `L115` — 2026-05-17 — EAS provisioning profile does not auto-include aps-environment when expo-notifications plugin is added; must add explicit ios.entitlements aps-environment entry in app.json (parallel to commit 3ef9274 Apple Sign In shape).
- `L116` — 2026-05-17 — expo-notifications requires expo-device as a direct dep for TypeScript types; npx expo install expo-device must run alongside the notifications install.
- `L118` — 2026-05-17 — expo-device v8 exports Device as a named module, not default; use `const [Device, ...] = await Promise.all([import('expo-device'), ...])`.
- `L121` — 2026-05-17 — Metro --clear restart resolves stale-bundle auth issues presenting as 401 storms (see Section 11 NOTE).
- `L149` — 2026-05-31 — git add on Expo Router bracket routes (e.g. app/listing/[id].tsx) must single-quote the path in zsh or it errors "no matches found" from glob expansion.
- `L153` — 2026-06-03 — expo-linear-gradient scrims: rgba() template-string color stops, and flat-black + low style.opacity over a bright camera preview, both render invisible; bake the alpha into multi-stop colors (e.g. rgba(0,0,0,0.9) → transparent) at full opacity for visible top/bottom scrims.
- `L154` — 2026-06-04 — react-native-vision-camera v5 uses Nitro, not worklets-core; frame processors need reanimated ~4.3 + react-native-worklets ~0.8 (app-wide bump), incompatible with the Expo SDK 54 default 4.1/0.5.1; the conflict surfaces only at native EAS build, not at npm install (peer-dedup looked clean).
- `L155` — 2026-06-04 — vision-camera v5 ships NO Expo config plugin; camera permission goes in app.json ios.infoPlist.NSCameraUsageDescription + android.permissions, never a plugins entry (expo config errors otherwise).
- `L184` — 2026-06-15 — react-native-svg has no conic gradient; a gradient trust ring styled with CSS conic-gradient cannot be reproduced with linearGradient in react-native-svg (only linear and radial exist) — use a flat-color SVG arc instead.
- `L185` — 2026-06-15 — borderWidth on the same View that sets borderRadius + overflow:hidden shrinks the clipped content box asymmetrically; to add a white border to an avatar circle use a white shadow-disc (absolute-positioned white circle behind the avatar, same borderRadius) so the clip geometry is not disturbed.
- `L188` — 2026-06-17 — A repo SVG path named "leaf" (LeafField LEAF_BODY) renders as a teardrop blob, not the Zelbi logo leaf; render-verify named SVG assets before reusing them in a build.
- `L189` — 2026-06-17 — Ring/disc "centering" must be measured to the visible card edge, not the flex column; card padding sits only on the column's outer side, so a column-centered ring reads ~half-padding off toward the divider. Fix by removing the card's horizontal padding so columns span the visible card.
