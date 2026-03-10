document.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.getElementById('fileInput');
    const uploadZone = document.getElementById('uploadZone');
    const processBtn = document.getElementById('processBtn');
    const resultsArea = document.getElementById('resultsArea');
    const cropRatioSelect = document.getElementById('cropRatio');
    const customRatioGroup = document.getElementById('customRatioGroup');
    const customRatioW = document.getElementById('customRatioW');
    const customRatioH = document.getElementById('customRatioH');
    const gapHeightInput = document.getElementById('gapHeight');
    const sampleBtn = document.getElementById('sampleBtn');

    let selectedFiles = [];

    // Show/hide custom ratio inputs
    cropRatioSelect.addEventListener('change', () => {
        customRatioGroup.classList.toggle('visible', cropRatioSelect.value === 'custom');
    });

    // Drag & Drop Handling
    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.classList.add('dragover');
    });

    uploadZone.addEventListener('dragleave', () => {
        uploadZone.classList.remove('dragover');
    });

    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('dragover');
        handleFiles(e.dataTransfer.files);
    });

    uploadZone.addEventListener('click', () => {
        fileInput.click();
    });

    fileInput.addEventListener('change', (e) => {
        handleFiles(e.target.files);
    });

    function handleFiles(files) {
        if (files.length > 0) {
            selectedFiles = Array.from(files).filter(file => file.type.startsWith('image/'));
            if (selectedFiles.length > 0) {
                processBtn.disabled = false;
                processBtn.textContent = `Process ${selectedFiles.length} Image${selectedFiles.length > 1 ? 's' : ''}`;
            } else {
                alert('Please select valid image files.');
            }
        }
    }

    function getRatio() {
        if (cropRatioSelect.value === 'custom') {
            const w = parseFloat(customRatioW.value) || 3;
            const h = parseFloat(customRatioH.value) || 4;
            return { w, h };
        }
        const [w, h] = cropRatioSelect.value.split(':').map(Number);
        return { w, h };
    }

    sampleBtn.addEventListener('click', () => {
        const { w: ratioW, h: ratioH } = getRatio();
        const gap = parseInt(gapHeightInput.value, 10) || 0;

        const sampleWidth = 1080;
        const sectionHeight = Math.round(sampleWidth * (ratioH / ratioW));
        const totalHeight = 10 * sectionHeight + 9 * gap;

        const canvas = document.createElement('canvas');
        canvas.width = sampleWidth;
        canvas.height = totalHeight;
        const ctx = canvas.getContext('2d');

        // 밝은 회색 배경 (무시할 간격 영역)
        ctx.fillStyle = '#d1d5db';
        ctx.fillRect(0, 0, sampleWidth, totalHeight);

        // 10개 흰색 섹션 (잘려질 영역)
        const fontSize = Math.min(Math.round(sectionHeight * 0.25), 220);
        ctx.font = `bold ${fontSize}px Arial`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';

        for (let i = 0; i < 10; i++) {
            const y = i * (sectionHeight + gap);
            ctx.fillStyle = '#ffffff';
            ctx.fillRect(0, y, sampleWidth, sectionHeight);

            // 섹션 번호 (연한 회색 워터마크)
            ctx.fillStyle = '#e5e7eb';
            ctx.fillText(String(i + 1).padStart(2, '0'), sampleWidth / 2, y + sectionHeight / 2);
        }

        canvas.toBlob(blob => {
            saveAs(blob, 'sample_image.png');
        }, 'image/png');
    });

    processBtn.addEventListener('click', async () => {
        const { w: ratioW, h: ratioH } = getRatio();
        const gapHeight = parseInt(gapHeightInput.value, 10) || 0;

        if (!ratioW || !ratioH || ratioW <= 0 || ratioH <= 0) {
            alert('유효한 비율을 입력해주세요.');
            return;
        }

        processBtn.disabled = true;
        processBtn.textContent = 'Processing...';
        resultsArea.innerHTML = '';

        for (const file of selectedFiles) {
            await processImage(file, ratioW, ratioH, gapHeight);
        }

        processBtn.disabled = false;
        processBtn.textContent = 'Process Images';
    });

    async function processImage(file, ratioW, ratioH, gap) {
        const card = document.createElement('div');
        card.className = 'result-card';
        card.innerHTML = `
            <div class="result-header">
                <h3>${file.name}</h3>
                <span class="stat-badge">Processing...</span>
            </div>
        `;
        resultsArea.appendChild(card);

        try {
            const imgBitmap = await createImageBitmap(file);
            const width = imgBitmap.width;
            const height = imgBitmap.height;

            // Calculate split height from image width and ratio
            const splitHeight = Math.round(width * (ratioH / ratioW));

            const zip = new JSZip();
            const folder = zip.folder(file.name.replace(/\.[^/.]+$/, ""));

            let currentY = 0;
            let partIndex = 1;
            const chunks = [];

            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            canvas.width = width;

            while (currentY < height) {
                let chunkHeight = splitHeight;

                if (currentY + chunkHeight > height) {
                    chunkHeight = height - currentY;
                }

                if (chunkHeight <= 0) break;

                canvas.height = chunkHeight;
                ctx.drawImage(imgBitmap, 0, currentY, width, chunkHeight, 0, 0, width, chunkHeight);

                const blob = await new Promise(resolve => canvas.toBlob(resolve, file.type || 'image/png'));

                const ext = file.name.split('.').pop() || 'png';
                const partName = `${file.name.replace(/\.[^/.]+$/, "")}_${String(partIndex).padStart(2, '0')}.${ext}`;
                folder.file(partName, blob);

                chunks.push(partName);

                currentY += splitHeight + gap;
                partIndex++;
            }

            const content = await zip.generateAsync({ type: "blob" });

            card.innerHTML = `
                <div class="result-header">
                    <h3>${file.name}</h3>
                    <span class="stat-badge">${chunks.length} Parts Created</span>
                </div>
                <button class="download-btn">Download ZIP</button>
            `;

            card.querySelector('.download-btn').addEventListener('click', () => {
                saveAs(content, `${file.name.replace(/\.[^/.]+$/, "")}_split.zip`);
            });

        } catch (err) {
            console.error(err);
            card.innerHTML = `
                <div class="result-header">
                    <h3>${file.name}</h3>
                    <span class="stat-badge" style="background: rgba(239, 68, 68, 0.1); color: #ef4444;">Error</span>
                </div>
                <p style="color: var(--text-secondary); font-size: 0.9rem;">Failed to process image.</p>
            `;
        }
    }
});
