import type { ThemeConfig } from 'antd';

export const appTheme: ThemeConfig = {
  token: {
    colorPrimary: '#475569',
    colorInfo: '#2563EB',
    colorSuccess: '#0F766E',
    colorError: '#DC2626',
    colorWarning: '#D97706',
    colorText: '#1E293B',
    colorTextSecondary: '#64748B',
    colorBgBase: '#FFFFFF',
    colorBgLayout: '#F8FAFC',
    colorBorder: '#E2E8F0',
    borderRadius: 10,
    controlHeight: 38,
    fontSize: 14,
    wireframe: false
  },
  components: {
    Card: {
      borderRadiusLG: 14,
      headerBg: '#FFFFFF'
    },
    Layout: {
      bodyBg: '#F8FAFC',
      headerBg: '#FFFFFF',
      siderBg: '#FFFFFF'
    },
    Menu: {
      itemSelectedBg: '#EAF2FF',
      itemSelectedColor: '#1E293B'
    },
    Table: {
      headerBg: '#F8FAFC',
      headerColor: '#334155'
    }
  }
};
