/* Server-side directory names, selected by the operator; no upload or policy write. */
const SmelterFolderBrowser=(()=>{
 function choose(api,{initialPath='',doc=document}={}){
  return new Promise(resolve=>{
   const el=(tag,text,cls)=>{const n=doc.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n};
   const dialog=el('dialog',undefined,'folder-dialog');dialog.setAttribute('aria-label','Browse folders');const heading=el('div',undefined,'section-heading');heading.append(el('h2','Choose a folder'),el('p','Browse folders on the machine running SMELTER. Selection does not grant access.'));
   const addressBar=el('div',undefined,'folder-address');const up=el('button','↑');up.type='button';up.setAttribute('aria-label','Parent folder');const address=el('input');address.setAttribute('aria-label','Folder address');address.placeholder='Choose a shortcut or enter an absolute path';const go=el('button','Go');go.type='button';addressBar.append(up,address,go);
   const crumbs=el('div',undefined,'folder-breadcrumbs');crumbs.setAttribute('aria-label','Folder breadcrumbs');const layout=el('div',undefined,'folder-layout'),shortcuts=el('nav',undefined,'folder-shortcuts'),list=el('div',undefined,'folder-list');shortcuts.setAttribute('aria-label','Folder shortcuts');layout.append(shortcuts,list);
   const hidden=el('input');hidden.type='checkbox';const hiddenLabel=el('label',undefined,'folder-hidden');hiddenLabel.append(hidden,doc.createTextNode(' Show hidden folders'));const search=el('input');search.type='search';search.placeholder='Filter folders';search.setAttribute('aria-label','Filter folders');const filters=el('div',undefined,'folder-filters');filters.append(search,hiddenLabel);
   const status=el('p');status.setAttribute('role','status');const actions=el('div',undefined,'dialog-actions');const cancel=el('button','Cancel'),select=el('button','Select folder');select.className='primary-button';select.disabled=true;actions.append(cancel,select);dialog.append(heading,addressBar,crumbs,filters,layout,status,actions);doc.body.append(dialog);
   const previous=doc.activeElement;let current=null,chosen=null,request=0,closed=false;
   function render(){list.replaceChildren();const rows=(current?.directories||[]).filter(row=>row.name.toLowerCase().includes(search.value.toLowerCase()));for(const row of rows){const button=el('button',undefined,'folder-entry');button.type='button';button.setAttribute('aria-label','Open '+row.name);button.append(el('span','▱','folder-icon'),el('span',row.name),el('span','›','folder-chevron'));button.onclick=()=>load(row.path);list.append(button)}if(!rows.length)list.append(el('p',current?.current_path?'No subfolders shown. You can select the current folder.':'Choose a shortcut to begin.','folder-empty'))}
   async function load(path=''){
    const generation=++request;select.disabled=up.disabled=go.disabled=true;current=null;list.textContent='Loading folders…';address.value=path;search.value='';status.textContent='';
    try{const data=await api('/api/location-browser?hidden='+(hidden.checked?'1':'0')+(path?'&path='+encodeURIComponent(path):''));if(closed||generation!==request)return;current=data;address.value=data.current_path||'';shortcuts.replaceChildren();for(const row of data.roots){const button=el('button',row.name);button.type='button';button.title=row.path;button.onclick=()=>load(row.path);shortcuts.append(button)}crumbs.replaceChildren();for(const row of data.breadcrumbs){const button=el('button',row.name);button.type='button';button.onclick=()=>load(row.path);crumbs.append(button)}up.disabled=!data.parent;select.disabled=!data.selectable;status.textContent=data.truncated?'This folder list is limited. Navigate by address if the folder is not shown.':data.current_path?(data.selectable?'Selected path: '+data.current_path:'Open a subfolder. Whole filesystem/drive roots cannot be registered.'):'Only directory names are listed. No files are uploaded.';render()}
    catch(error){if(!closed&&generation===request){list.replaceChildren();status.textContent=error.message;select.disabled=true}}
    finally{if(!closed&&generation===request)go.disabled=false}
   }
   cancel.onclick=()=>dialog.close();select.onclick=()=>{if(current?.selectable){chosen=current.current_path;dialog.close()}};up.onclick=()=>{if(current?.parent)load(current.parent)};go.onclick=()=>load(address.value.trim());address.onkeydown=event=>{if(event.key==='Enter'){event.preventDefault();load(address.value.trim())}};hidden.onchange=()=>load(address.value.trim());search.oninput=render;
   dialog.addEventListener('close',()=>{closed=true;request++;dialog.remove();if(previous?.isConnected)previous.focus();resolve(chosen)});dialog.showModal();load(initialPath);
  });
 }
 return {choose};
})();
