// 记录到底点中了哪个元素 —— 断言「点成功了」不够，必须断言「点的是哪一个」。
window.CLICKED = [];
document.addEventListener('click', e => {
  const t = e.target;
  window.CLICKED.push(t.dataset.name || t.id || t.className || t.tagName);
});
