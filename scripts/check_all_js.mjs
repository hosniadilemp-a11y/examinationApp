import fs from 'fs';
import path from 'path';

globalThis.localStorage = { getItem: () => null, setItem: () => {}, removeItem: () => {} };
globalThis.window = { addEventListener: () => {}, location: { protocol: 'http:', host: 'localhost:8000' } };
globalThis.document = { querySelector: () => null, querySelectorAll: () => [], getElementById: () => null };

async function checkDir(dir) {
  for (const f of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, f.name);
    if (f.isDirectory()) {
      if (f.name !== 'vendor') await checkDir(full);
    } else if (f.name.endsWith('.js')) {
      try {
        const fileUrl = 'file:///' + path.resolve(full).replace(/\\/g, '/');
        await import(fileUrl);
        console.log('OK:', full);
      } catch (err) {
        if (err instanceof SyntaxError) {
          console.error('SYNTAX ERROR in', full, err);
        } else {
          // runtime error
        }
      }
    }
  }
}

await checkDir('./frontend/js');
console.log('ALL_FILES_CHECKED_DONE');

