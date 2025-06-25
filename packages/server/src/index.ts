import express from 'express';
import multer from 'multer';
import { v4 as uuidv4 } from 'uuid';
import fs from 'fs';
import path from 'path';

const app = express();
app.use(express.json());

const upload = multer({
  limits: { fileSize: 2 * 1024 * 1024 },
  fileFilter: (req, file, cb) => {
    if (file.mimetype === 'image/svg+xml') cb(null, true);
    else cb(new Error('Invalid file type'));
  }
});

app.post('/api/upload', upload.array('files', 200), (req, res) => {
  const files = req.files as Express.Multer.File[];
  const sessionId = uuidv4();
  const dest = path.join('/tmp', sessionId, 'raw');
  fs.mkdirSync(dest, { recursive: true });
  files.forEach(f => {
    fs.writeFileSync(path.join(dest, f.originalname), f.buffer);
  });
  res.json({ sessionId });
});

app.patch('/api/stroke-weight', (req, res) => {
  const { factor } = req.body as { factor: number };
  if (typeof factor !== 'number') return res.status(400).end();
  // TODO: implement stroke weight adjustment
  res.json({ ok: true });
});

app.post('/api/build-subset', (req, res) => {
  const { selected } = req.body as { selected: string[] };
  if (!Array.isArray(selected)) return res.status(400).end();
  // TODO: call python script and package fonts
  res.json({ ok: true });
});

const port = process.env.PORT || 3000;
if (process.env.NODE_ENV !== 'test') {
  app.listen(port, () => console.log(`Server running on ${port}`));
}

export default app;
