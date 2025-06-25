const fileInput = document.getElementById('fileInput');
const grid = document.getElementById('grid');
const weightRange = document.getElementById('weight');
const thinnerBtn = document.getElementById('thinner');
const thickerBtn = document.getElementById('thicker');
const downloadBtn = document.getElementById('downloadBtn');

let icons = [];
let factor = 1;

fileInput.addEventListener('change', handleFiles);
weightRange.addEventListener('input', () => {
  factor = parseFloat(weightRange.value);
});
thinnerBtn.addEventListener('click', () => {
  factor = Math.max(0.2, factor / 2);
  weightRange.value = factor;
});
thickerBtn.addEventListener('click', () => {
  factor = Math.min(5, factor * 2);
  weightRange.value = factor;
});

downloadBtn.addEventListener('click', downloadZip);

function handleFiles() {
  icons = [];
  grid.innerHTML = '';
  const files = Array.from(fileInput.files || []);
  if (files.length > 200) {
    alert('Max 200 files');
    return;
  }
  files.forEach(f => {
    if (f.size > 2 * 1024 * 1024 || !f.name.toLowerCase().endsWith('.svg')) return;
    const reader = new FileReader();
    reader.onload = e => {
      const content = e.target.result;
      const url = URL.createObjectURL(new Blob([content], { type: 'image/svg+xml' }));
      const id = icons.length;
      icons.push({ name: f.name.replace(/\.svg$/i, ''), content });
      const div = document.createElement('div');
      div.className = 'icon-item';
      div.innerHTML = `\n        <img src="${url}" />\n        <input type="text" value="${f.name.replace(/\.svg$/i,'')}">\n        <label><input type="checkbox" checked> Select</label>`;
      grid.appendChild(div);
    };
    reader.readAsText(f);
  });
}

function downloadZip() {
  const zip = new JSZip();
  const selected = Array.from(grid.querySelectorAll('.icon-item')).map((el, i) => {
    const checkbox = el.querySelector('input[type="checkbox"]');
    const nameInput = el.querySelector('input[type="text"]');
    return { selected: checkbox.checked, name: nameInput.value };
  });
  const cssLines = [];
  selected.forEach((info, i) => {
    if (!info.selected) return;
    const icon = icons[i];
    const filename = info.name + '.svg';
    zip.file(filename, icon.content);
    cssLines.push(`.icon-${info.name} { background: url(${filename}) no-repeat center/contain; }`);
  });
  zip.file('style.css', cssLines.join('\n'));
  zip.generateAsync({ type: 'blob' }).then(content => {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(content);
    a.download = 'icons.zip';
    a.click();
  });
}
