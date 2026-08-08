import { describe, expect, it } from 'vitest';
import { createClientTraceId, normalizeMetricName } from './performance';

describe('performance metrics', () => {
  it('removes query strings and normalizes dynamic route segments', () => {
    expect(normalizeMetricName('/api/emails/123?folder=inbox')).toBe(
      '/api/emails/:id',
    );
    expect(normalizeMetricName('/emails/person@example.com')).toBe(
      '/emails/:id',
    );
  });

  it('creates a non-empty client trace id', () => {
    expect(createClientTraceId().length).toBeGreaterThan(8);
  });
});
