/**
 * Shared visual language copied from the original Outlook Mail frontend.
 * Keep semantic colors here so Ant Design pages do not silently fall back to
 * its default blue/yellow/green palette.
 */
export const OUTLOOK_COLORS = {
  primary: '#B85C38',
  primaryDark: '#8E3E22',
  primaryLight: '#D4795A',
  accent: '#C8963E',
  jade: '#3A7D44',
  jadeLight: '#5AA35F',
  danger: '#B6473B',
  success: '#3A7D44',
  warn: '#C07F2C',
  background: '#F5EDE0',
  container: '#FDFAF5',
  sidebar: '#2C1A0E',
  text: '#2C1810',
  textSecondary: '#6B4226',
  textMuted: '#7D5F44',
  border: '#D9C4A8',
  borderLight: '#EDE0CE',
  backgroundSecondary: '#F0E8D8',
  backgroundHover: 'rgba(184, 92, 56, 0.06)',
} as const;

/** Ant Design seed/alias tokens shared by every route. */
export const OUTLOOK_ANTD_TOKENS = {
  colorPrimary: OUTLOOK_COLORS.primary,
  colorPrimaryHover: OUTLOOK_COLORS.primaryLight,
  colorPrimaryActive: OUTLOOK_COLORS.primaryDark,
  colorInfo: OUTLOOK_COLORS.primary,
  colorSuccess: OUTLOOK_COLORS.success,
  colorWarning: OUTLOOK_COLORS.warn,
  colorError: OUTLOOK_COLORS.danger,
  colorLink: OUTLOOK_COLORS.primary,
  colorBgLayout: OUTLOOK_COLORS.background,
  colorBgContainer: OUTLOOK_COLORS.container,
  colorBgElevated: OUTLOOK_COLORS.container,
  colorFillAlter: OUTLOOK_COLORS.backgroundSecondary,
  colorText: OUTLOOK_COLORS.text,
  colorTextSecondary: OUTLOOK_COLORS.textSecondary,
  colorTextTertiary: OUTLOOK_COLORS.textMuted,
  colorBorder: OUTLOOK_COLORS.border,
  colorBorderSecondary: OUTLOOK_COLORS.borderLight,
  colorPrimaryBg: '#F7EDE8',
  colorInfoBg: '#F7EDE8',
  colorSuccessBg: '#EDF3EA',
  colorWarningBg: '#FAF1E2',
  colorErrorBg: '#F9ECE9',
  colorPrimaryBorder: '#E4B9A8',
  colorInfoBorder: '#E4B9A8',
  colorSuccessBorder: '#BCD3B8',
  colorWarningBorder: '#E8CDA0',
  colorErrorBorder: '#E4B6AE',
  borderRadius: 8,
  borderRadiusSM: 6,
};
