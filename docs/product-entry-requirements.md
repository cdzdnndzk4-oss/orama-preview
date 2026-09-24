# ORAMA product entry requirements

## Product photos

- Three catalog photos: front, three-quarter, side.
- Processed previews use pure white background, including through clear prescription lenses, and approximately 85% horizontal product fill.
- Owner reviews processed versus original photos and may keep either version per view.

## Product details

- The fourth photo of a temple marking, label, or price card is optional.
- When supplied, automatic reading may prefill brand, model, color code, lens/bridge/temple dimensions, and price only when those details are visible.
- Every field remains manually editable, including automatically read values. Details may be entered entirely by hand without the fourth photo.
- Price and stock per store must not be inferred from the product photo. If absent, they remain empty until entered.
- The assistant provides an initial short description of about 35–60 words and an initial material selection when possible. Both fields remain manually editable. Material selected from appearance stays marked for owner review and is not treated as verified technical data.
- A product stays a draft until the owner reviews and approves its details and photos. No automatic public publication from uncertain readings.
- Bulk import must support the same fields and retain a review step for errors.

## Current status

A local-only product-entry prototype now provides manual creation and editing, including the suggested description and material, separate dimensions, one unit per selected store, three-photo upload and preview, and CSV import. Its local, no-charge description library selects from 300 wording paths using verified style, audience and visual detail; another version can be requested and manually edited. It does not infer these traits from images. It seeds the five photo-approved records and saves changes in a local SQLite file. The local admin now generates a heuristic white-background/crop draft from each new photo and shows it beside the original. The owner chooses which version to save per view. This still needs visual quality review, especially with clear or pale frames; it does not publish changes to the public site. The GitHub Pages demo still does not implement the real administration, checkout, or stock-reservation flow.
