import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import App from './App';
import { connectNativeBridge } from './bridge';
import './index.css';
import { MockBridge } from './mockBridge';


async function start() {
  const native = await connectNativeBridge();
  const allowMock = import.meta.env.DEV || new URLSearchParams(window.location.search).has('mock');
  if (!native && !allowMock) {
    document.getElementById('root')!.innerHTML = '<main class="boot-screen"><h1>Desktop bridge unavailable</h1><p>Launch this interface through Trackma.</p></main>';
    return;
  }
  const bridge = native ?? new MockBridge();
  createRoot(document.getElementById('root')!).render(
    <StrictMode><App bridge={bridge} /></StrictMode>,
  );
}

void start();
