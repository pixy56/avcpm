const fs = require('fs');
const { execSync } = require('child_process');

const markdown = fs.readFileSync('openclaw-knowledge-management-system.md', 'utf8');

// Simple markdown to HTML conversion
let html = markdown
  .replace(/^# (.*$)/gim, '<h1>$1</h1>')
  .replace(/^## (.*$)/gim, '<h2>$1</h2>')
  .replace(/^### (.*$)/gim, '<h3>$1</h3>')
  .replace(/^---$/gim, '<hr class="page-break"/>')
  .replace(/```\n?([\s\S]*?)```/gim, '<pre><code>$1</code></pre>')
  .replace(/`([^`]+)`/gim, '<code>$1</code>')
  .replace(/^\s*[-•]\s+(.*$)/gim, '<li>$1</li>')
  .replace(/(\n<li>.*<\/li>)+/g, '<ul>$&</ul>')
  .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
  .replace(/\*(.*?)\*/gim, '<em>$1</em>')
  .replace(/^\|(.+)\|$/gim, (match, p1) => {
    const cells = p1.split('|').map(c => c.trim()).filter(c => c);
    return '<tr>' + cells.map(c => '<td>' + c + '</td>').join('') + '</tr>';
  })
  .replace(/\n\n/g, '<br><br>');

const fullHtml = `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>OpenClaw Knowledge Management System</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 40px; line-height: 1.6; }
  h1 { font-size: 28px; border-bottom: 2px solid #333; padding-bottom: 10px; margin-top: 0; }
  h2 { font-size: 22px; color: #333; margin-top: 30px; }
  h3 { font-size: 18px; color: #555; }
  pre { background: #f5f5f5; padding: 15px; border-radius: 5px; overflow-x: auto; font-size: 12px; }
  code { background: #f5f5f5; padding: 2px 5px; border-radius: 3px; font-size: 14px; }
  pre code { padding: 0; background: none; }
  table { border-collapse: collapse; width: 100%; margin: 20px 0; }
  td, th { border: 1px solid #ddd; padding: 8px; text-align: left; font-size: 13px; }
  tr:nth-child(even) { background: #f9f9f9; }
  ul { margin: 10px 0; }
  li { margin: 5px 0; }
  .page-break { page-break-after: always; border: none; margin: 0; }
  @page { size: A4; margin: 20mm; }
  @media print { .page-break { page-break-after: always; } }
</style>
</head>
<body>
${html}
</body>
</html>`;

fs.writeFileSync('presentation.html', fullHtml);
console.log('HTML created');

// Use Chromium to convert to PDF
try {
  execSync('chromium --headless --disable-gpu --print-to-pdf=presentation.pdf --no-sandbox presentation.html', {
    timeout: 30000,
    stdio: 'pipe'
  });
  console.log('PDF created: presentation.pdf');
} catch (e) {
  console.error('Chromium failed:', e.message);
  // Try google-chrome
  try {
    execSync('google-chrome --headless --disable-gpu --print-to-pdf=presentation.pdf --no-sandbox presentation.html', {
      timeout: 30000,
      stdio: 'pipe'
    });
    console.log('PDF created with google-chrome: presentation.pdf');
  } catch (e2) {
    console.error('google-chrome also failed:', e2.message);
  }
}
