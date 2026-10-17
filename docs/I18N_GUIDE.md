# GreenGuard Internationalization (i18n) Guide

GreenGuard's frontend supports **English (`en`, LTR)** and **Urdu (`ur`, RTL)**.
This guide explains how the system works and how to add new screens so they
are bilingual from day one. You never have to "implement Urdu" for a screen:
you write message keys, and the shared setup handles language, direction and
fonts.

---

## 1. How it works

| Concern | Where | Notes |
|---|---|---|
| Library | [`next-intl`](https://next-intl.dev) | Used without locale-prefixed routes. |
| Supported locales | `frontend/lib/i18n/config.ts` | The only locale list in the app (`locales`, `LOCALE_SETTINGS`). |
| Locale resolution | `frontend/lib/i18n/request.ts` | Reads the `NEXT_LOCALE` cookie on every server render, falling back to `en`. |
| Persisting the choice | `frontend/lib/i18n/actions.ts` | Server Action that sets the `NEXT_LOCALE` cookie (1 year, `path=/`, `SameSite=Lax`). |
| `<html lang dir>` | `frontend/app/layout.tsx` | `lang="en" dir="ltr"` or `lang="ur" dir="rtl"`, rendered on the server, so there is no flash of the wrong direction. |
| Client provider | `frontend/providers/i18n-provider.tsx` | `NextIntlClientProvider` plus Base UI `DirectionProvider`. |
| Language switcher | `frontend/components/layout/language-switcher.tsx` | Used in the app navbar, auth layout, home page and legal pages. |
| Messages | `frontend/messages/<locale>/<namespace>.json` | One file per feature or screen, registered in `messages/<locale>/index.ts`. |
| Type safety | `frontend/types/i18n.d.ts` | Every `t("key")` is type-checked against English. `ur/index.ts` is typed against `en`, so a key missing from Urdu fails `tsc`. |
| Consistency check | `frontend/scripts/check-i18n.mjs` | `npm run check:i18n` (see §6). |
| Fallbacks | `frontend/lib/i18n/messages.ts`, `error-handling.ts` | A missing Urdu key renders in English. In development it shows `⟦namespace.key⟧` and logs a console error. |
| Urdu font | `frontend/app/layout.tsx`, `globals.css` | Noto Nastaliq Urdu, loaded only for `lang="ur"`. |

URLs never change with the language (`/dashboard`, not `/ur/dashboard`).
Switching language writes the cookie, flips `<html lang dir>` immediately, and
calls `router.refresh()`. Client state such as half-filled forms or a selected
photo survives the switch.

---

## 2. Adding a new screen (checklist)

1. **Create the namespace files.** Add `messages/en/myFeature.json` and
   `messages/ur/myFeature.json` with the same keys. Group keys by part of the
   screen (`page`, `form`, `table`, `empty`, ...).
2. **Register them.** Import the file in **both** `messages/en/index.ts` and
   `messages/ur/index.ts`, and add it to the exported object.
3. **Use the keys.**
   - Client Component: `const t = useTranslations("myFeature");`
   - Server Component / `generateMetadata`: `const t = await getTranslations("myFeature");`
4. **Reuse shared namespaces** instead of duplicating text:
   `common` (Cancel, Save Changes, Retry, pagination, roles...), `navigation`,
   `units`, `validation`, `errors`, `crops`, `diseases`.
5. **Use logical CSS** (§4), and mirror directional icons.
6. **Run the checks:** `npm run typecheck && npm run check:i18n && npm run lint`.

Example:

```tsx
"use client";
import { useTranslations } from "next-intl";

export function FarmTips() {
  const t = useTranslations("farmTips");
  const tCommon = useTranslations("common");
  return (
    <section aria-labelledby="tips-title">
      <h2 id="tips-title">{t("title")}</h2>
      <p>{t("tipCount", { count: 3 })}</p>
      <button type="button">{tCommon("retry")}</button>
    </section>
  );
}
```

```json
// messages/en/farmTips.json
{ "title": "Farm Tips", "tipCount": "{count, plural, one {# tip} other {# tips}}" }

// messages/ur/farmTips.json
{ "title": "فارم کے مشورے", "tipCount": "{count, plural, one {# مشورہ} other {# مشورے}}" }
```

---

## 3. What to translate, and what never to translate

**Translate**: everything the app itself says, including headings, buttons,
labels, placeholders, helper text, empty, loading and error states, dialogs,
toasts, `aria-label`s, `alt` text, page titles (`generateMetadata`), and
validation messages.

**Never translate or change**: API values, IDs, enum values sent to or
received from the backend, database fields, crop/disease IDs, request
payloads, numbers or measurements, or AI module outputs.

To **display** a raw API value in the active language, look it up and keep
the raw value untouched:

```tsx
import { useMessages } from "next-intl";
import { labelFor } from "@/lib/i18n/labels";

const messages = useMessages();
labelFor(messages.crops, crop);                          // "wheat" -> "گندم"
labelFor(messages.weather.riskLevels, level);            // "High"  -> "زیادہ"
labelFor(messages.soil.options.soilType, value);         // "clay"  -> "چکنی"
```

`labelFor` falls back to the raw value, so a value the AI team adds later
still shows up instead of disappearing. Styling and logic must keep using the
raw value (for example `RISK_STYLES[value]`), never the translated label.

**Free text written by an AI module** (Module 1 `message`, Module 2
`recommendation_notes`, Module 3 `*_reason`) is shown exactly as delivered.
Give it `dir="auto"` so English text reads correctly inside an Urdu page:

```tsx
<p dir="auto">{assessment.fungalDiseaseReason}</p>
```

Do the same for user-entered text such as farm names or file names.

---

## 4. RTL rules

`<html dir="rtl">` flips normal document flow, flexbox and grid automatically.
To keep it working:

| Use | Instead of |
|---|---|
| `ms-*` / `me-*` | `ml-*` / `mr-*` |
| `ps-*` / `pe-*` | `pl-*` / `pr-*` |
| `start-*` / `end-*` | `left-*` / `right-*` |
| `text-start` / `text-end` | `text-left` / `text-right` |
| `border-s` / `border-e`, `rounded-s` / `rounded-e` | `border-l` / `border-r`, `rounded-l` / `rounded-r` |
| `slide-in-from-end` | `slide-in-from-right` |

- **Directional icons** (arrows, chevrons, log out) get `rtl:-scale-x-100`:
  `<ArrowLeft className="size-4 rtl:-scale-x-100" />`.
  Do not mirror icons that have no direction (bell, leaf, cloud).
- **LTR islands:** IDs, emails, URLs, code and numeric input placeholders
  get `dir="ltr"` (e.g. the report ID, the pH input).
- **Charts:** keep axis values numeric, and put translated text in labels,
  legends and tooltips only.
- `globals.css` gives Urdu text a taller line height for the Nastaliq script.
  Avoid fixed heights on text containers.

---

## 5. Formatting, plurals and placeholders

- **Placeholders:** `"Updated at {time}"` → `t("updatedAt", { time })`. The
  `{name}` must be identical in every language. Only the surrounding words
  change.
- **Plurals:** use ICU plural syntax, never `count === 1 ? ... : ...` in code.
- **Rich text:** `"Farm: <strong>{value}</strong>"` with
  `t.rich("farm", { value, strong: (c) => <b>{c}</b> })`.
- **Dates and times:** `useFormatter().dateTime(date, "dateTime")`, using the
  presets in `lib/i18n/formats.ts`. Never use `toLocaleString()` directly.
- **Units:** use the `units` namespace (`tUnits("celsius", { value })`) so unit
  names are translated while the number stays unchanged.

---

## 6. Forms and validation

Zod schemas store **translation keys** instead of English text:

```ts
import { validationKey as v } from "@/lib/i18n/validation";
farmName: z.string().min(1, v("farmNameRequired")),
```

Render errors with `<FieldError message={errors.farmName?.message} />`
(`components/ui/field-error.tsx`). It translates a key, and shows server-side
field errors unchanged. `validationKey` only accepts keys that exist in
`validation.json`, so a typo fails `tsc`.

API errors go through `useParseApiError()` (`lib/i18n/use-api-error.ts`). It
returns the backend's own message when there is one, and otherwise a
localized "something went wrong / can't reach the server" message.

---

## 7. Checks

| Command | Catches |
|---|---|
| `npm run typecheck` | Unknown keys in code, keys missing from Urdu, typos in validation keys. |
| `npm run check:i18n` | Missing or extra keys per locale, empty values, `{placeholder}` or `<tag>` mismatches, JSON files not registered in `index.ts`. Warns when a value is identical to English. Use `--strict` to fail on those warnings too. |
| `npm run lint` | General code quality. |

Run all three before committing a screen.

---

## 8. Writing Urdu for farmers

- Use simple, everyday **Pakistani Urdu**, the way an extension worker would
  speak to a farmer. Avoid heavy Persian or Arabic vocabulary and literal
  word-for-word translation.
- Use the common local names: گندم, کپاس, مکئی, گنا, یوریا, ڈی اے پی,
  ٹیوب ویل, نہر, بارانی, کلر زدہ, پیلی کنگی.
- Keep a technical term in English (or add it in brackets) when farmers
  actually use it that way: pH, DAP, NPK, UV, MB, GreenGuard.
- Use polite imperatives: "براہ کرم دوبارہ کوشش کریں", "تصویر منتخب کریں".
- Keep it short. Urdu labels are often longer than English, so check that
  buttons and badges still fit on mobile.

---

## 9. Adding another language

1. Add the code to `locales` and `LOCALE_SETTINGS` in `lib/i18n/config.ts`
   (with `nativeName` and `dir`).
2. Copy `messages/en/` to `messages/<code>/`, translate it, and type its
   `index.ts` against `en`, as `ur/index.ts` does.
3. Add its loader to `lib/i18n/messages.ts` and its boundary messages to
   `app/global-error.tsx`.
4. If the script needs a font, add it in `app/layout.tsx` and `globals.css`.
5. Run `npm run check:i18n`. It checks every folder under `messages/`
   automatically.
