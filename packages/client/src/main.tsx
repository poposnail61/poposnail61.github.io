import React from 'react';
import ReactDOM from 'react-dom/client';
import UploadZone from './components/UploadZone';
import StrokeSlider from './components/StrokeSlider';
import IconGrid from './components/IconGrid';
import DownloadPanel from './components/DownloadPanel';

const App = () => (
  <div>
    <UploadZone />
    <StrokeSlider />
    <IconGrid />
    <DownloadPanel />
  </div>
);

ReactDOM.createRoot(document.getElementById('root')!).render(<App />);
