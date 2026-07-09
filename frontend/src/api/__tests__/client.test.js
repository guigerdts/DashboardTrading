import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import api from '../client';

describe('API client — FormData guard', () => {
  let fetchMock;

  beforeEach(() => {
    fetchMock = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ status: 'ok' }),
      }),
    );
    global.fetch = fetchMock;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('POST with FormData body does NOT set Content-Type header', async () => {
    const formData = new FormData();
    formData.append('file', new Blob(['data']));
    await api.post('/test', formData);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const callArgs = fetchMock.mock.calls[0];
    const [url, config] = callArgs;

    expect(url).toBe('/api/test');
    expect(config.method).toBe('POST');
    expect(config.headers['Content-Type']).toBeUndefined();
  });

  it('POST with JSON body sets Content-Type to application/json', async () => {
    await api.post('/test', { key: 'value' });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const callArgs = fetchMock.mock.calls[0];
    const [url, config] = callArgs;

    expect(url).toBe('/api/test');
    expect(config.method).toBe('POST');
    expect(config.headers['Content-Type']).toBe('application/json');
  });

  it('GET request preserves default headers', async () => {
    await api.get('/test');

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const callArgs = fetchMock.mock.calls[0];
    const [url, config] = callArgs;

    expect(url).toBe('/api/test');
    expect(config.method).toBe('GET');
    expect(config.headers['Content-Type']).toBe('application/json');
  });

  it('non-ok response with FormData populates error.data', async () => {
    const errorPayload = { detail: 'File too large' };
    fetchMock.mockImplementationOnce(() =>
      Promise.resolve({
        ok: false,
        status: 422,
        statusText: 'Unprocessable Entity',
        json: () => Promise.resolve(errorPayload),
      }),
    );

    const formData = new FormData();
    formData.append('file', new Blob(['data']));

    await expect(api.post('/test', formData)).rejects.toMatchObject({
      status: 422,
      data: errorPayload,
    });
  });

  it('non-ok response with JSON populates error.data', async () => {
    const errorPayload = { detail: 'Bad request' };
    fetchMock.mockImplementationOnce(() =>
      Promise.resolve({
        ok: false,
        status: 400,
        statusText: 'Bad Request',
        json: () => Promise.resolve(errorPayload),
      }),
    );

    await expect(api.post('/test', { key: 'value' })).rejects.toMatchObject({
      status: 400,
      data: errorPayload,
    });
  });
});
