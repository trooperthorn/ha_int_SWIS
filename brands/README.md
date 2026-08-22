# Brand assets staging

`icon.png` and `logo.png` at the repo root are what HACS reads directly for
this integration's icon in the HACS UI.

`custom_integrations/swis/` mirrors the layout expected by the
[home-assistant/brands](https://github.com/home-assistant/brands) repository.
That repo is what supplies the icon shown on the native Home Assistant
**Add Integration** search results and on the integration/device pages — it
cannot be sourced from this repository directly. To enable it:

1. Fork [home-assistant/brands](https://github.com/home-assistant/brands).
2. Copy this `custom_integrations/swis/` directory into that fork at the
   same path.
3. Open a PR there. Follow their
   [contributing guide](https://github.com/home-assistant/brands/blob/master/CONTRIBUTING.md)
   (square icon, transparent background, no copyrighted claims of official
   endorsement).
4. Once merged, Home Assistant and HACS will pick up the icon automatically
   — no further change needed in this repository.

| File | Size | Purpose |
| --- | --- | --- |
| `icon.png` | 256×256 | Required. Square icon. |
| `icon@2x.png` | 512×512 | Recommended. High-DPI icon. |
| `logo.png` | height 128 | Optional. Wider logo variant. |
| `logo@2x.png` | height 256 | Optional. High-DPI logo. |
