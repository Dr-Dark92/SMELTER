/* Settings owns a navigation rail and one independently scrolling content pane. */
const SmelterSettings=(()=>{
 let instance=null;
 function create(doc=document){
  if(instance)return instance;
  const dialog=doc.createElement('dialog');dialog.id='settingsDialog';dialog.className='settings-screen';dialog.setAttribute('aria-labelledby','settingsTitle');
  const header=doc.createElement('header');header.className='settings-header';const title=doc.createElement('h2');title.id='settingsTitle';title.textContent='Settings';
  const close=doc.createElement('button');close.textContent='Close settings';close.className='quiet-button';close.onclick=()=>dialog.close();header.append(title,close);
  const content=doc.createElement('div');content.id='rightbar';const nav=doc.createElement('nav');nav.className='settings-nav';nav.setAttribute('aria-label','Settings sections');
  const picker=doc.createElement('select');picker.className='settings-section-picker';picker.setAttribute('aria-label','Settings section');
  const deck=doc.createElement('div');deck.className='settings-content';content.append(picker,nav,deck);dialog.append(header,content);doc.body.append(dialog);
  const groups=new Map(),options=new Map();let previous=null;
  function group(label){if(!groups.has(label)){const section=doc.createElement('section');section.className='settings-nav-group';const heading=doc.createElement('h3');heading.textContent=label;section.append(heading);nav.append(section);groups.set(label,section);const optionGroup=doc.createElement('optgroup');optionGroup.label=label;picker.append(optionGroup);options.set(label,optionGroup)}return groups.get(label)}
  function activate(id){const panel=doc.getElementById(id);if(!panel||!deck.contains(panel))return;deck.querySelectorAll('.panel').forEach(x=>x.classList.toggle('active',x===panel));nav.querySelectorAll('.navbtn').forEach(x=>{const active=x.dataset.panel===id;x.classList.toggle('active',active);x.setAttribute('aria-current',active?'page':'false')});deck.scrollTop=0;picker.value=id;nav.querySelector('[data-panel="'+id+'"]')?.scrollIntoView({block:'nearest'})}
  function open(panel){if(!dialog.open){previous=doc.activeElement;dialog.showModal()}if(panel)activate(panel)}
  function addPanel(id,label,section,category='Workspace'){section.id=id;section.classList.add('panel');section.setAttribute('aria-label',label);const button=doc.createElement('button');button.type='button';button.className='navbtn';button.dataset.panel=id;button.textContent=label;button.onclick=()=>activate(id);group(category).append(button);const option=doc.createElement('option');option.value=id;option.textContent=label;options.get(category).append(option);deck.append(section);return button}
  picker.onchange=()=>nav.querySelector('[data-panel="'+picker.value+'"]')?.click();
  const toolbar=doc.createElement('div');toolbar.className='workspace-toolbar';const summary=doc.createElement('span');summary.id='taskAccessSummary';summary.setAttribute('role','status');
  const task=doc.createElement('section');const heading=doc.createElement('h3');heading.textContent='Access for the next task';task.append(heading);addPanel('taskAccessPanel','Next-task tool access',task);
  const review=doc.createElement('button');review.textContent='Review task access';review.onclick=()=>open('taskAccessPanel');const settings=doc.createElement('button');settings.textContent='Settings';settings.onclick=()=>open();toolbar.append(summary,review,settings);
  dialog.addEventListener('close',()=>{if(previous?.isConnected)previous.focus()});
  instance={dialog,content,nav,deck,toolbar,summary,task,open,activate,addPanel};return instance;
 }
 return {create,get current(){return instance}};
})();
