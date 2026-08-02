import { describe, expect, it } from 'vitest';

import { BridgeClient, type ChannelTransport } from './bridge';


class FakeSignal {
  listeners: Array<(value: string) => void> = [];

  connect(listener: (value: string) => void) {
    this.listeners.push(listener);
  }

  emit(value: unknown) {
    const encoded = JSON.stringify(value);
    this.listeners.forEach((listener) => listener(encoded));
  }
}


function transport(): ChannelTransport & { response: FakeSignal; event: FakeSignal } {
  const response = new FakeSignal();
  const event = new FakeSignal();
  return {
    response,
    event,
    request(requestId, command, payload) {
      expect(command).toBe('app.bootstrap');
      expect(JSON.parse(payload)).toEqual({ ready: true });
      response.emit({ id: requestId, ok: true, data: { version: '0.10.3' } });
    },
  };
}


describe('BridgeClient', () => {
  it('resolves successful command responses', async () => {
    const client = new BridgeClient(transport());

    await expect(client.call('app.bootstrap', { ready: true })).resolves.toEqual({
      version: '0.10.3',
    });
  });

  it('rejects structured backend errors', async () => {
    const fake = transport();
    fake.request = (requestId) => {
      fake.response.emit({
        id: requestId,
        ok: false,
        error: { code: 'NO_ACTIVE_SESSION', message: 'Select an account first' },
      });
    };
    const client = new BridgeClient(fake);

    await expect(client.call('library.snapshot')).rejects.toMatchObject({
      code: 'NO_ACTIVE_SESSION',
      message: 'Select an account first',
    });
  });

  it('delivers typed events to subscribers', () => {
    const fake = transport();
    const client = new BridgeClient(fake);
    const events: unknown[] = [];
    client.subscribe((event) => events.push(event));

    fake.event.emit({ name: 'queue_changed', payload: [[{ id: 4 }]] });

    expect(events).toEqual([{ name: 'queue_changed', payload: [[{ id: 4 }]] }]);
  });
});
