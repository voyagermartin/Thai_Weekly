/**
 * Thai_Weekly (泰語學習週報) Service Worker
 * 提供完整的 PWA 離線快取、離線可用性與背景資源更新機制
 */

const CACHE_VERSION = 'v1';
const CACHE_NAME = `thai-weekly-${CACHE_VERSION}`;

// 核心 App Shell 靜態資源
const STATIC_ASSETS = [
  './',
  './index.html',
  './lesson.html',
  './manifest.json',
  './favicon.svg',
  './icons/icon-192.png',
  './icons/icon-512.png',
  './icons/icon-maskable-192.png',
  './icons/icon-maskable-512.png',
  './icons/apple-touch-icon.png'
];

// 安裝階段：快取靜態核心資產
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(async (cache) => {
      // 容錯快取各個資源，避免單一資源失敗導致整個安裝中止
      await Promise.all(
        STATIC_ASSETS.map(async (asset) => {
          try {
            await cache.add(asset);
          } catch (err) {
            console.warn(`[SW] 快取預載略過: ${asset}`, err);
          }
        })
      );
    }).then(() => self.skipWaiting())
  );
});

// 啟用階段：清除舊版快取並立即接管控制權
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            console.log(`[SW] 清除過期快取: ${key}`);
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// 擷取事件：依資源特性套用分流快取策略
self.addEventListener('fetch', (event) => {
  const req = event.request;
  const url = new URL(req.url);

  // 僅處理 http/https 協議
  if (!url.protocol.startsWith('http')) return;

  // 策略 1：GAS Web App (Gemini AI 即時說文解字) ➔ Network-Only + 離線友善回覆
  if (url.hostname.includes('script.google.com')) {
    event.respondWith(
      fetch(req).catch(() => {
        return new Response(
          JSON.stringify({
            status: 'error',
            error_type: 'OFFLINE',
            message: '目前處於離線狀態，即時說文解字 AI 需連線運作，請確認網路連線。'
          }),
          {
            headers: { 'Content-Type': 'application/json; charset=utf-8' }
          }
        );
      })
    );
    return;
  }

  // 策略 2：Google Sheet GViz 資料庫 ➔ Network-First (失敗退回快取)
  if (url.hostname.includes('docs.google.com') && url.pathname.includes('/gviz/tq')) {
    event.respondWith(
      fetch(req)
        .then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200) {
            const resClone = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(req, resClone));
          }
          return networkResponse;
        })
        .catch(async () => {
          const cached = await caches.match(req);
          if (cached) return cached;
          return new Response('/* Offline: No cached spreadsheet data */', { status: 503 });
        })
    );
    return;
  }

  // 策略 3：HTML 導航請求 ➔ Network-First (離線回傳快取頁面)
  if (req.mode === 'navigate' || req.headers.get('accept')?.includes('text/html')) {
    event.respondWith(
      fetch(req)
        .then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200) {
            const resClone = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(req, resClone));
          }
          return networkResponse;
        })
        .catch(async () => {
          const cached = await caches.match(req);
          if (cached) return cached;
          // 若無對應快取，依目標退回 index.html 或 lesson.html
          if (url.pathname.includes('lesson')) {
            return (await caches.match('./lesson.html')) || (await caches.match('./index.html'));
          }
          return caches.match('./index.html');
        })
    );
    return;
  }

  // 策略 4：靜態資源 (SVG, PNG, CSS, JS, 字型, 語音) ➔ Stale-While-Revalidate
  event.respondWith(
    caches.match(req).then((cachedResponse) => {
      const fetchPromise = fetch(req).then((networkResponse) => {
        if (networkResponse && networkResponse.status === 200) {
          const resClone = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(req, resClone));
        }
        return networkResponse;
      }).catch(() => null);

      return cachedResponse || fetchPromise;
    })
  );
});
