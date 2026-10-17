export type PasswordStrengthLevel = "weak" | "fair" | "good" | "strong";

export interface PasswordStrength {
  score: number; // 0-4
  /** Display label comes from messages: auth.passwordStrength.<level>. */
  level: PasswordStrengthLevel;
  percent: number;
}

const LEVELS: PasswordStrengthLevel[] = ["weak", "weak", "fair", "good", "strong"];

export function getPasswordStrength(password: string): PasswordStrength {
  if (!password) {
    return { score: 0, level: "weak", percent: 0 };
  }

  let score = 0;
  if (password.length >= 8) score += 1;
  if (password.length >= 12) score += 1;
  if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score += 1;
  if (/\d/.test(password)) score += 1;
  if (/[^A-Za-z0-9]/.test(password)) score += 1;

  const clamped = Math.min(score, 4);
  const level = LEVELS[clamped];

  return { score: clamped, level, percent: (clamped / 4) * 100 };
}
