// Preload script — secure bridge between Electron and renderer
const { contextBridge } = require('electron');

contextBridge.exposeInMainWorld('winnersApp', {
  platform: process.platform,
  version: '1.0.0',
  appName: 'Winners Academy',
});
