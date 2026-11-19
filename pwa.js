/**
 * Thai_Weekly (泰語學習週報) PWA 核心控制腳本
 * 支援 Service Worker 註冊、離線快取同步、Android/桌面與 iOS 獨立 App 安裝提示
 */

(function () {
  'use strict';

  let deferredInstallPrompt = null;

  // 1. 註冊 Service Worker (範疇: ./)
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('./sw.js', { scope: './' })
        .then((reg) => {
          console.log('[PWA] ServiceWorker 註冊成功，範疇 (Scope):', reg.scope);
          reg.addEventListener('updatefound', () => {
            const newWorker = reg.installing;
            if (newWorker) {
              newWorker.addEventListener('statechange', () => {
                if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                  console.log('[PWA] 檢測到新版本已快取完畢，重整即可套用最新功能。');
                }
              });
            }
          });
        })
        .catch((err) => {
          console.warn('[PWA] ServiceWorker 註冊失敗:', err);
        });
    });
  }

  // 2. 判斷是否已處於獨立 App (Standalone) 模式
  function isRunningStandalone() {
    return (
      (window.matchMedia && window.matchMedia('(display-mode: standalone)').matches) ||
      (typeof navigator !== 'undefined' && 'standalone' in navigator && navigator.standalone === true) ||
      (typeof document !== 'undefined' && document.referrer && document.referrer.includes('android-app://'))
    );
  }

  // 3. 判斷 iOS 裝置
  function isIosDevice() {
    const ua = (typeof navigator !== 'undefined' && navigator.userAgent) ? navigator.userAgent.toLowerCase() : '';
    return /iphone|ipad|ipod/.test(ua);
  }

  // 4. 動態注入 iOS / 一般安裝指引 Modal
  function ensureModal() {
    if (document.getElementById('pwa-install-modal')) return;

    const modal = document.createElement('div');
    modal.id = 'pwa-install-modal';
    modal.className = 'pwa-modal-overlay';
    modal.innerHTML = `
      <div class="pwa-modal-card">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
          <div style="display:flex; align-items:center; gap:10px;">
            <div style="width:36px; height:36px; border-radius:8px; background:linear-gradient(135deg, #7e22ce, #a855f7); display:flex; align-items:center; justify-content:center; font-size:18px;">🇹🇭</div>
            <div style="font-size:18px; font-weight:800; color:#fde68a;">安裝泰語學習週報 App</div>
          </div>
          <button id="pwa-modal-close-btn" style="background:none; border:none; color:#a78bfa; font-size:22px; cursor:pointer; line-height:1; padding:4px;" title="關閉">✕</button>
        </div>
        
        <p style="font-size:14.5px; color:#cbd5e1; line-height:1.6; margin-bottom:16px;">
          將《泰語學習週報》安裝至手機主畫面，享有全螢幕沉浸式閱讀、快速原地語音播放與離線教材學習體驗！
        </p>

        <div id="pwa-modal-steps" style="background:rgba(13,8,20,0.6); border:1px solid #443063; border-radius:12px; padding:14px 16px; margin-bottom:20px; font-size:14px; line-height:1.7; color:#f8fafc;">
          <!-- 依平台動態填入指引 -->
        </div>

        <div style="text-align:right;">
          <button id="pwa-modal-confirm-btn" style="background:linear-gradient(135deg, #f59e0b 0%, #d97706 100%); color:#0d0814; font-weight:800; border:none; padding:10px 22px; border-radius:10px; cursor:pointer; font-size:14.5px; box-shadow:0 0 12px rgba(245,158,11,0.3);">我知道了</button>
        </div>
      </div>
    `;

    document.body.appendChild(modal);

    const close = () => { modal.style.display = 'none'; };
    document.getElementById('pwa-modal-close-btn').addEventListener('click', close);
    document.getElementById('pwa-modal-confirm-btn').addEventListener('click', close);
    modal.addEventListener('click', (e) => {
      if (e.target === modal) close();
    });
  }

  function showInstallInstructions() {
    ensureModal();
    const modal = document.getElementById('pwa-install-modal');
    const stepsEl = document.getElementById('pwa-modal-steps');
    if (!modal || !stepsEl) return;

    if (isIosDevice()) {
      stepsEl.innerHTML = `
        <div style="font-weight:700; color:#fde047; margin-bottom:8px;">📱 iPhone / iPad 安裝步驟：</div>
        <div style="margin-bottom:6px;">1. 點擊 Safari 底部工具列的<b>【分享】</b>圖示（方框帶箭頭 <span style="font-size:16px;">⎋</span>）</div>
        <div style="margin-bottom:6px;">2. 在分享選單中向下滑動，點選<b>【加入主畫面】</b>（<span style="font-size:16px;">⊞</span>）</div>
        <div>3. 點擊右上角的<b>【新增】</b>，即可在手機桌面直接啟動 App！</div>
      `;
    } else {
      stepsEl.innerHTML = `
        <div style="font-weight:700; color:#fde047; margin-bottom:8px;">📱 Android / Chrome 安裝步驟：</div>
        <div style="margin-bottom:6px;">1. 點擊瀏覽器右上角<b>【⋮】功能選單</b></div>
        <div style="margin-bottom:6px;">2. 點選<b>【安裝應用程式】</b>或<b>【新增至主螢幕】</b></div>
        <div>3. 確認安裝，即可在手機桌面享有獨立 App 體驗！</div>
      `;
    }

    modal.style.display = 'flex';
  }

  // 5. 初始化安裝按鈕狀態
  function initInstallUi() {
    if (isRunningStandalone()) {
      console.log('[PWA] 已於獨立 App 模式運行中');
      return;
    }

    const installButtons = document.querySelectorAll('.btn-pwa-install');
    installButtons.forEach((btn) => {
      // 若為 iOS，直接顯示「加到主畫面」按鈕
      if (isIosDevice()) {
        btn.style.display = 'inline-flex';
        btn.innerHTML = '<span>📲</span> <span>加到主畫面</span>';
      }

      btn.addEventListener('click', (e) => {
        e.preventDefault();
        if (deferredInstallPrompt) {
          deferredInstallPrompt.prompt();
          deferredInstallPrompt.userChoice.then((choice) => {
            if (choice.outcome === 'accepted') {
              installButtons.forEach((b) => (b.style.display = 'none'));
            }
            deferredInstallPrompt = null;
          });
        } else {
          showInstallInstructions();
        }
      });
    });

    // 監聽原生 beforeinstallprompt 事件 (Chrome / Android / Edge)
    window.addEventListener('beforeinstallprompt', (e) => {
      e.preventDefault();
      deferredInstallPrompt = e;
      installButtons.forEach((btn) => {
        btn.style.display = 'inline-flex';
        btn.innerHTML = '<span>📲</span> <span>安裝 App</span>';
      });
      console.log('[PWA] beforeinstallprompt 觸發，已顯示安裝按鈕');
    });

    // 監聽 appinstalled 事件
    window.addEventListener('appinstalled', () => {
      installButtons.forEach((btn) => (btn.style.display = 'none'));
      deferredInstallPrompt = null;
      console.log('[PWA] 應用程式安裝成功');
      const toast = document.getElementById('toast');
      if (toast) {
        toast.innerText = '🎉 泰語學習週報已成功安裝至主畫面！';
        toast.style.display = 'flex';
        setTimeout(() => { toast.style.display = 'none'; }, 3000);
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initInstallUi);
  } else {
    initInstallUi();
  }
})();
