import { ChangeEvent } from 'react';
import useStore from '../store';

export default function UploadZone() {
  const setSession = useStore(s => s.setSession);
  const onChange = async (e: ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;
    const form = new FormData();
    Array.from(files).forEach(f => form.append('files', f));
    const res = await fetch('/api/upload', { method: 'POST', body: form });
    const data = await res.json();
    setSession(data.sessionId);
  };
  return <input type="file" multiple accept=".svg" onChange={onChange} />;
}
