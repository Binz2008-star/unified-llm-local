export const isMac = (): boolean => {
  if (typeof window === 'undefined') return false;
  return /(Mac|iPhone|iPod|iPad)/i.test(navigator.platform || navigator.userAgent);
};

export const getModifierKey = (): string => {
  return isMac() ? '⌘' : 'Ctrl';
};

export const isTouchDevice = (): boolean => {
  if (typeof window === 'undefined') return false;
  return 'ontouchstart' in window || navigator.maxTouchPoints > 0;
};
