window.MathJax = {
  tex: {
    inlineMath: [["\\(", "\\)"], ["$", "$" ]],
    displayMath: [["\\[", "\\]"], ["$$", "$$"]],
    processEscapes: true,
    processEnvironments: true
  },
  options: {
    ignoreHtmlClass: "\\b(?:tex2jax_ignore|mathjax_ignore)\\b",
    processHtmlClass: "\\b(?:tex2jax_process|mathjax_process)\\b"
  }
};
