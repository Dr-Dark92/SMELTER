/* One attachment entry point, backed only by the supported image and GLB inputs. */
const SmelterAttachments=(()=>{
 function mount(host,{imageInput,modelInput,canAttach,onError},doc=document){
  imageInput.hidden=true;modelInput.hidden=true;const root=doc.createElement('div');root.className='attachment-control';const button=doc.createElement('button');button.type='button';button.className='attachment-add';button.textContent='+';button.setAttribute('aria-label','Add attachment');button.setAttribute('aria-haspopup','menu');button.setAttribute('aria-expanded','false');
  const menu=doc.createElement('div');menu.className='attachment-menu';menu.hidden=true;menu.setAttribute('role','menu');menu.setAttribute('aria-label','Supported attachments');const caption=doc.createElement('p');caption.textContent='ADD A FILE';menu.append(caption);
  function close(focus=false){menu.hidden=true;button.setAttribute('aria-expanded','false');if(focus)button.focus()}
  for(const [title,note,input] of [['Photos & screenshots','PNG, JPEG, WebP · up to 2 MiB',imageInput],['3D models','GLB · up to 25 MiB',modelInput]]){const item=doc.createElement('button');item.type='button';item.setAttribute('role','menuitem');const label=doc.createElement('strong');label.textContent=title;const description=doc.createElement('small');description.textContent=note;item.append(label,description);item.onclick=()=>{if(!canAttach())return;close();input.click()};menu.append(item)}
  const chip=doc.createElement('span');chip.className='attachment-chip';chip.hidden=true;const name=doc.createElement('span');const remove=doc.createElement('button');remove.type='button';remove.textContent='×';remove.setAttribute('aria-label','Remove attached image');remove.onclick=()=>{if(canAttach()){imageInput.value='';refresh()}};chip.append(name,remove);
  function refresh(){const file=imageInput.files?.[0];chip.hidden=!file;name.textContent=file?.name||'';button.disabled=!canAttach();remove.disabled=!canAttach()}
  imageInput.addEventListener('change',()=>{const file=imageInput.files?.[0];if(file&&file.size>2*1024*1024){imageInput.value='';onError('Image exceeds 2 MiB')}refresh()});
  button.onclick=()=>{if(!canAttach())return;menu.hidden=!menu.hidden;button.setAttribute('aria-expanded',String(!menu.hidden));if(!menu.hidden)menu.querySelector('[role=menuitem]').focus()};button.onkeydown=e=>{if(e.key==='ArrowDown'){e.preventDefault();if(menu.hidden)button.click()}};
  menu.onkeydown=e=>{const items=[...menu.querySelectorAll('[role=menuitem]')],index=items.indexOf(doc.activeElement);if(e.key==='Escape'){e.preventDefault();close(true)}else if(['ArrowDown','ArrowUp'].includes(e.key)){e.preventDefault();items[(index+(e.key==='ArrowDown'?1:-1)+items.length)%items.length].focus()}};
  doc.addEventListener('click',event=>{if(!root.contains(event.target))close()});doc.addEventListener('keydown',event=>{if(event.key==='Escape'&&!menu.hidden)close(true)});
  new MutationObserver(refresh).observe(imageInput,{attributes:true,attributeFilter:['disabled']});root.append(button,menu,chip);host.append(root);return {button,refresh};
 }
 return {mount};
})();
