import type { ProLayoutProps } from '@ant-design/pro-components';
import { OUTLOOK_COLORS } from './theme';

/**
 * OutlookEmail 前端布局默认设置
 */
const Settings: ProLayoutProps & {
  logo?: string;
} = {
  // Keep ProLayout in light mode so content surfaces use the original cream palette.
  // The sider is styled as the original ink-brown navigation in global.less.
  navTheme: 'light',
  colorPrimary: OUTLOOK_COLORS.primary,
  layout: 'mix',
  siderWidth: 220,
  contentWidth: 'Fluid',
  fixedHeader: true,
  fixSiderbar: true,
  colorWeak: false,
  title: 'Outlook 邮件管理',
  logo: '/img/ico.png',
  iconfontUrl: '',
  token: {
    // https://procomponents.ant.design/components/layout#%E9%80%9A%E8%BF%87-token-%E4%BF%AE%E6%94%B9%E6%A0%B7%E5%BC%8F
  },
};

export default Settings;
