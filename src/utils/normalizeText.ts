/**
 * Normalize text for accent-insensitive comparisons.
 *
 *   normalizeText('Psicóloga') === 'psicologa'
 *   normalizeText('  Mínas  ') === 'minas'
 *
 * Always returns a string. Safe with non-string inputs.
 */
export function normalizeText(value: unknown): string {
  return String(value ?? '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim();
}
