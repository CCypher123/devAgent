function setCopyStatus(btn, msg){
  const original = btn.dataset.originalText || btn.textContent;
  btn.dataset.originalText = original;
  btn.textContent = msg;
  window.clearTimeout(btn.__t);
  btn.__t = window.setTimeout(()=>{btn.textContent = original;}, 1200);
}

async function copyText(text){
  if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(text);
    return;
  }
  const ta = document.createElement('textarea');
  ta.value = text;
  ta.style.position = 'fixed';
  ta.style.left = '-9999px';
  ta.style.top = '0';
  document.body.appendChild(ta);
  ta.focus();
  ta.select();
  document.execCommand('copy');
  ta.remove();
}

function initCopyButtons(){
  document.querySelectorAll('[data-copy-target]')?.forEach(btn=>{
    btn.addEventListener('click', async ()=>{
      const sel = btn.getAttribute('data-copy-target');
      const el = document.querySelector(sel);
      if(!el){setCopyStatus(btn,'Not found'); return;}
      const txt = el.textContent;
      try{
        await copyText(txt);
        setCopyStatus(btn,'Copied');
      }catch(e){
        setCopyStatus(btn,'Copy failed');
      }
    });
  });
}

document.addEventListener('DOMContentLoaded', ()=>{
  initCopyButtons();
});
