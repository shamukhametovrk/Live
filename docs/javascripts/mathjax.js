// Формулы: $...$ — в строке, $$...$$ — отдельной строкой.
// Рендерит MathJax; arithmatex (generic) оборачивает формулы в .arithmatex
// и переводит их в \( ... \) и \[ ... \]
window.MathJax = {
  tex: {
    inlineMath: [["\\(", "\\)"]],
    displayMath: [["\\[", "\\]"]],
    processEscapes: true,
    processEnvironments: true,
  },
  options: {
    ignoreHtmlClass: ".*|",
    processHtmlClass: "arithmatex",
  },
};

// Material подгружает страницы без перезагрузки — формулы пересчитываем
document$.subscribe(() => {
  MathJax.startup.output.clearCache();
  MathJax.typesetClear();
  MathJax.texReset();
  MathJax.typesetPromise();
});
