/**
 * Utility functions for the Trade Intelligence Platform frontend.
 */

/**
 * Merge class names, filtering out falsy values.
 * Tailwind CSS compatible — similar to clsx + tailwind-merge pattern.
 *
 * @param  {...(string|boolean|null|undefined)} classes
 * @returns {string}
 */
export function cn(...classes) {
  return classes.filter(Boolean).join(' ');
}

export default { cn };
