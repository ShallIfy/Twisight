import fs from 'fs';
import path from 'path';

// Fungsi rekursif untuk menampilkan struktur direktori
function displayTree(dirPath, indent = '') {
    const items = fs.readdirSync(dirPath, { withFileTypes: true });
    
    items.forEach((item, index) => {
        // Lewati folder atau file `.git`
        if (item.name === '.git') return;

        const isLastItem = index === items.length - 1;
        const prefix = isLastItem ? '└── ' : '├── ';
        const fullPath = path.join(dirPath, item.name);

        // Menampilkan nama file atau direktori
        console.log(`${indent}${prefix}${item.name}`);

        // Jika item adalah direktori, lakukan rekursi
        if (item.isDirectory()) {
            const newIndent = indent + (isLastItem ? '    ' : '│   ');
            displayTree(fullPath, newIndent);
        }
    });
}

// Menentukan direktori awal (gunakan '.' untuk direktori saat ini)
const startDir = '.';

// Menampilkan struktur direktori
console.log(`Directory structure of ${path.resolve(startDir)} (excluding .git):\n`);
displayTree(startDir);
