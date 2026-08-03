import { beforeEach, describe, expect, it, vi } from 'vitest';

const { outlookRequestMock } = vi.hoisted(() => ({
  outlookRequestMock: vi.fn(),
}));

vi.mock('./request', () => ({
  outlookRequest: outlookRequestMock,
}));

import {
  fetchHealth,
  normalizePollingSettings,
  updatePollingSettings,
} from './settings';

describe('settings service contracts', () => {
  beforeEach(() => {
    outlookRequestMock.mockReset();
    outlookRequestMock.mockResolvedValue({ success: true });
  });

  it('normalizes polling settings to backend-supported bounds', () => {
    expect(normalizePollingSettings(0, -3)).toEqual({
      polling_interval: 1,
      polling_count: 0,
    });
    expect(normalizePollingSettings(5000, 1200)).toEqual({
      polling_interval: 3600,
      polling_count: 999,
    });
  });

  it('persists mailbox polling settings through the shared settings endpoint', async () => {
    await updatePollingSettings(20, 0);

    expect(outlookRequestMock).toHaveBeenCalledWith('/api/settings', {
      method: 'PUT',
      data: { polling_interval: 20, polling_count: 0 },
      skipErrorHandler: true,
    });
  });

  it('reads the backend application version from healthz', async () => {
    await fetchHealth();

    expect(outlookRequestMock).toHaveBeenCalledWith('/healthz', {
      method: 'GET',
      skipErrorHandler: true,
    });
  });
});
