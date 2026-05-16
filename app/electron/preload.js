// electron/preload.js — Electron preload 스크립트
// 역할: renderer(웹페이지)와 main 프로세스 사이의 안전한 다리.
// P0에선 비워둠. ml-backend가 HTTP 서버라 IPC 불필요.
// 미래 용도 (P1+): 세이브 파일 OS 경로, 모델 파일 선택 다이얼로그, 앱 종료 hook 등.

const { contextBridge } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  // 미래 추가 자리. 예: saveDialog: () => ipcRenderer.invoke('save-dialog')
});