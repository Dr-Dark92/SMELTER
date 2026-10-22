/* A single settings centre with searchable, grouped navigation and focus return. */
const SmelterSettings=(()=>{
 let instance=null;
 function create(doc=document){
  if(instance)return instance;
  const dialog=doc.createElement('dialog');dialog.id='settingsDialog';dialog.className='settings-screen';dialog.setAttribute('aria-labelledby','settingsTitle');
  const header=doc.createElement('header');header.className='settings-header';
  const titles=doc.createElement('div'),eyebrow=doc.createElement('p');eyebrow.className='eyebrow';eyebrow.textContent='WORKBENCH PREFERENCES';
  const title=doc.createElement('h2');title.id='settingsTitle';title.textContent='Settings';
  const current=doc.createElement('p');current.className='settings-current';current.setAttribute('aria-live','polite');titles.append(eyebrow,title,current);
  const search=doc.createElement('input');search.type='search';search.placeholder='Find a setting…';search.setAttribute('aria-label','Search settings');search.className='settings-search';
  const close=doc.createElement('button');close.textContent='Close settings';close.className='quiet-button';close.onclick=()=>dialog.close();header.append(titles,search,close);
  const content=doc.createElement('div');content.id='rightbar';const nav=doc.createElement('nav');nav.className='settings-nav';nav.setAttribute('aria-label','Settings sections');
  const picker=doc.createElement('select');picker.className='settings-section-picker';picker.setAttribute('aria-label','Settings section');
  const deck=doc.createElement('div');deck.className='settings-content';content.append(picker,nav,deck);dialog.append(header,content);doc.body.append(dialog);
  const groups=new Map(),options=new Map(),entries=[];let previous=null,activePanel='taskAccessPanel';
  const empty=doc.createElement('p');empty.className='settings-no-results';empty.textContent='No matching settings. Clear or change the search to try again.';empty.setAttribute('role','status');empty.hidden=true;deck.prepend(empty);
  function group(label){if(!groups.has(label)){const section=doc.createElement('section');section.className='settings-nav-group';const heading=doc.createElement('h3');heading.textContent=label;section.append(heading);nav.append(section);groups.set(label,section);const optionGroup=doc.createElement('optgroup');optionGroup.label=label;picker.append(optionGroup);options.set(label,optionGroup)}return groups.get(label)}
  function activate(id){
   const panel=doc.getElementById(id);if(!panel||!deck.contains(panel))return;
   activePanel=id;deck.querySelectorAll('.panel').forEach(x=>x.classList.toggle('active',x===panel));
   nav.querySelectorAll('.navbtn').forEach(x=>{const active=x.dataset.panel===id;x.classList.toggle('active',active);if(active)x.setAttribute('aria-current','page');else x.removeAttribute('aria-current')});
   deck.scrollTop=0;picker.value=id;const entry=entries.find(x=>x.id===id);current.textContent=entry?entry.category+' / '+entry.label:'';
   if(dialog.open)nav.querySelector('[data-panel="'+id+'"]')?.scrollIntoView({block:'nearest'});
  }
  function filter(){const query=search.value.trim().toLowerCase();const aliases={accessPolicyPanel:'locations folders paths read write execute',runtimePanel:'timeout tokens context thinking',taskAccessPanel:'permissions grants tools approval',skillsPanel:'instructions collections skills',mcpPanel:'connections servers protocol',systemStatusPanel:'cpu ram gpu resources storage installed services ollama qwen opencode start stop restart reload'};let count=0;for(const row of entries){const show=(row.label+' '+row.category+' '+(aliases[row.id]||'')).toLowerCase().includes(query);row.button.hidden=!show;row.option.hidden=!show;row.option.disabled=!show;if(show)count++}for(const [label,section]of groups){const show=entries.some(x=>x.category===label&&!x.button.hidden);section.hidden=!show;options.get(label).hidden=!show}empty.hidden=count!==0}
  function open(panel){
   const opening=!dialog.open;if(opening){previous=doc.activeElement;dialog.showModal()}
   search.value='';filter();const id=panel||activePanel;const button=nav.querySelector('[data-panel="'+id+'"]');
   if(button)button.click();else activate(id);
   if(opening){if(panel)close.focus();else search.focus()}
  }
  function addPanel(id,label,section,category='Workspace'){
   section.id=id;section.classList.add('panel');section.setAttribute('aria-label',label);
   const button=doc.createElement('button');button.type='button';button.className='navbtn';button.dataset.panel=id;button.textContent=label;button.onclick=()=>activate(id);group(category).append(button);
   const option=doc.createElement('option');option.value=id;option.textContent=label;options.get(category).append(option);deck.append(section);entries.push({id,label,category,button,option});return button
  }
  picker.onchange=()=>nav.querySelector('[data-panel="'+picker.value+'"]')?.click();search.oninput=filter;
  search.onkeydown=event=>{if(event.key==='Enter'){const first=entries.find(x=>!x.button.hidden);if(first){event.preventDefault();first.button.click();close.focus()}}};
  const toolbar=doc.createElement('div');toolbar.className='workspace-toolbar';
  const summary=doc.createElement('span');summary.id='taskAccessSummary';summary.setAttribute('role','status');
  const task=doc.createElement('section'),heading=doc.createElement('h3');heading.textContent='Access for the next task';task.append(heading);addPanel('taskAccessPanel','Next-task tool access',task);
  const review=doc.createElement('button');review.textContent='Review task access';review.onclick=()=>open('taskAccessPanel');
  const settings=doc.createElement('button');settings.textContent='Settings';settings.onclick=()=>open();toolbar.append(summary,review,settings);
  dialog.addEventListener('close',()=>{if(previous?.isConnected)previous.focus()});
  instance={dialog,content,nav,deck,toolbar,summary,task,open,activate,addPanel};return instance
 }
 return {create,get current(){return instance}};
})();
