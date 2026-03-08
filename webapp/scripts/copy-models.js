/**
 * Copy STL files from export/ to webapp/public/models/
 * Run with: node scripts/copy-models.js
 */
import { readdirSync, copyFileSync, mkdirSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const exportDir = join(__dirname, '..', '..', 'export');
const modelsDir = join(__dirname, '..', 'public', 'models');

mkdirSync(modelsDir, { recursive: true });

const stlFiles = readdirSync(exportDir).filter(f => f.endsWith('.stl'));
let copied = 0;

for (const file of stlFiles) {
  copyFileSync(join(exportDir, file), join(modelsDir, file));
  copied++;
  console.log(`  Copied: ${file}`);
}

console.log(`\n  ${copied} STL files copied to webapp/public/models/`);
