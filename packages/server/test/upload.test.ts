import { describe, it, expect } from 'vitest';
import request from 'supertest';
import app from '../src/index';
import path from 'path';

const svgPath = path.join(__dirname, 'fixtures', 'simple.svg');

describe('upload', () => {
  it('rejects non-svg', async () => {
    const res = await request(app)
      .post('/api/upload')
      .attach('files', Buffer.from('abc'), 'a.txt');
    expect(res.status).toBe(500); // multer error
  });
});
