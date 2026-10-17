import type { Formats } from "next-intl";

/**
 * Named date/time presets shared by every component, used as
 * `format.dateTime(date, "dateTime")`. The output adapts to the active
 * locale (English vs Urdu month names); the underlying timestamp never changes.
 */
export const formats = {
  dateTime: {
    /** 10/4/2026 -- same fields as Date#toLocaleDateString(). */
    date: { year: "numeric", month: "numeric", day: "numeric" },
    /** October 4, 2026 */
    dateLong: { year: "numeric", month: "long", day: "numeric" },
    /** Sunday, October 4 */
    weekdayLong: { weekday: "long", month: "long", day: "numeric" },
    /** Oct 4, 2026, 7:05 PM */
    dateTimeMedium: { dateStyle: "medium", timeStyle: "short" },
    /** 10/4/2026, 7:05:00 PM -- same fields as Date#toLocaleString(). */
    dateTime: {
      year: "numeric",
      month: "numeric",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
      second: "2-digit",
    },
    /** 7:05 PM */
    time: { hour: "numeric", minute: "2-digit" },
  },
} satisfies Formats;
