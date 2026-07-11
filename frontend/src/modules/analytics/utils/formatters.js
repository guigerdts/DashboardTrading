/**
 * Format a currency value in USD.
 * @param {number|null|undefined} value
 * @returns {string} Formatted currency or em-dash for null/undefined
 */
export function formatCurrency(value) {
  if (value == null || value === '') return '\u2014';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

/**
 * Format a decimal ratio as a percentage string.
 * @param {number|null|undefined} value — decimal (e.g. 0.65 → "65.00%")
 * @returns {string}
 */
export function formatPercent(value) {
  if (value == null || value === '') return '\u2014';
  return `${(value * 100).toFixed(2)}%`;
}

/**
 * Format a ratio with 4 decimal places.
 * @param {number|null|undefined} value
 * @returns {string}
 */
export function formatRatio(value) {
  if (value == null || value === '') return '\u2014';
  return value.toFixed(4);
}

/**
 * Format an ISO date string as "MMM DD, YYYY".
 * @param {string|null|undefined} value
 * @returns {string}
 */
export function formatDate(value) {
  if (value == null || value === '') return '\u2014';
  try {
    return new Date(value).toLocaleDateString('en-US', {
      month: 'short',
      day: '2-digit',
      year: 'numeric',
    });
  } catch {
    return '\u2014';
  }
}

/**
 * Format a number with locale commas (trade counts).
 * @param {number|null|undefined} value
 * @returns {string}
 */
export function formatNumber(value) {
  if (value == null || value === '') return '\u2014';
  return new Intl.NumberFormat('en-US').format(value);
}

/**
 * Format a decimal to 2 fixed places (avg R multiple).
 * @param {number|null|undefined} value
 * @returns {string}
 */
export function formatDecimal(value) {
  if (value == null || value === '') return '\u2014';
  return value.toFixed(2);
}
