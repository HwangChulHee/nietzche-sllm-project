// electron/main.js — Electron 메인 프로세스
// 역할: BrowserWindow 생성, Next.js dev 서버(:3000) 로드.
// dev mode 한정 — 배포(installer) 빌드는 P2.

const { app, BrowserWindow } = require('electron');
const path = require('path');

const DEV_URL = 'http://localhost:3000';
const isDev = process.argv.includes('--dev');

function createWindow() {
  const win = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1024,
    minHeight: 720,
    backgroundColor: '#f5ecd9', // 세피아, 흰 깜빡임 방지
    title: '차라투스트라와의 동행',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  win.loadURL(DEV_URL);

  if (isDev) {
    win.webContents.openDevTools({ mode: 'detach' });
  }

  // 외부 링크는 OS 기본 브라우저로 (Electron 창 안에서 외부 페이지 열리는 거 차단)
  win.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith(DEV_URL)) return { action: 'allow' };
    require('electron').shell.openExternal(url);
    return { action: 'deny' };
  });
}

app.whenReady().then(() => {
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});