/* Own the Settings surface before child controls mount; no post-mount reparenting. */
const SmelterSettings=(()=>{
 let instance=null;
 function create(doc=document){
  if(instance)return instance;
  const dialog=doc.createElement('dialog');dialog.id='settingsDialog';dialog.className='settings-screen';
  const header=doc.createElement('header');header.className='settings-header';const title=doc.createElement('h2');title.textContent='SMELTER settings';
  const close=doc.createElement('button');close.textContent='Close settings';close.onclick=()=>dialog.close();header.append(title,close);
  const content=doc.createElement('aside');content.id='rightbar';dialog.append(header,content);doc.body.append(dialog);
  const toolbar=doc.createElement('div');toolbar.className='workspace-toolbar';
  const summary=doc.createElement('span');summary.id='taskAccessSummary';summary.setAttribute('role','status');
  let previous=null;
  function open(panel){previous=doc.activeElement;if(!dialog.open)dialog.showModal();if(panel)activate(panel)}
  function activate(id){const panel=doc.getElementById(id);if(!panel||!content.contains(panel))return;content.querySelectorAll('.panel').forEach(x=>x.classList.toggle('active',x===panel));content.querySelectorAll('.navbtn').forEach(x=>x.classList.toggle('active',x.dataset.panel===id))}
  function addPanel(id,label,section){section.id=id;section.classList.add('panel');const button=doc.createElement('button');button.className='navbtn';button.dataset.panel=id;button.textContent=label;button.onclick=()=>activate(id);content.append(button,section);return button}
  const task=doc.createElement('section');const heading=doc.createElement('h3');heading.textContent='Access for the next task';task.append(heading);addPanel('taskAccessPanel','Next-task tool access',task);
  const review=doc.createElement('button');review.textContent='Review task access';review.onclick=()=>open('taskAccessPanel');
  const settings=doc.createElement('button');settings.textContent='Settings';settings.onclick=()=>open();toolbar.append(summary,review,settings);
  dialog.addEventListener('close',()=>{if(previous?.isConnected)previous.focus()});
  instance={dialog,content,toolbar,summary,task,open,activate,addPanel};return instance;
 }
 return {create,get current(){return instance}};
})();
