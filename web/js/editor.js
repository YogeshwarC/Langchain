// editor.js
// Handles Monaco Editor initialization

require.config({ paths: { 'vs': 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.44.0/min/vs' } });

let editor;

export function initEditor() {
    return new Promise((resolve) => {
        require(['vs/editor/editor.main'], function () {
            editor = monaco.editor.create(document.getElementById('editor-container'), {
                value: [
                    '<!DOCTYPE html>',
                    '<html>',
                    '<head>',
                    '    <style>',
                    '        body { font-family: sans-serif; padding: 20px; }',
                    '        .box {',
                    '            width: 100px;',
                    '            height: 100px;',
                    '            background: #6366f1;',
                    '            border-radius: 8px;',
                    '            display: flex;',
                    '            align-items: center;',
                    '            justify-content: center;',
                    '            color: white;',
                    '        }',
                    '    </style>',
                    '</head>',
                    '<body>',
                    '    <h1>Hello AI Tutor</h1>',
                    '    <div class="box">Box</div>',
                    '</body>',
                    '</html>'
                ].join('\n'),
                language: 'html',
                theme: 'vs-dark',
                minimap: { enabled: false },
                fontSize: 14,
                width: "100%",
                height: "100%",
                padding: { top: 16 }
            });

            // Handle resize
            window.addEventListener('resize', () => {
                editor.layout();
            });

            // Also resize when panels are dragged/dropped (layout changes)
            // A clearer way is needed but for now windows resize generic covers basic snaps

            resolve(editor);
        });
    });
}

export function getCode() {
    if (editor) return editor.getValue();
    return "";
}

export function setCode(code) {
    if (editor) editor.setValue(code);
}
