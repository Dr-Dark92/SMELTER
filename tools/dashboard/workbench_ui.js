/* Workbench presentation and accessible controls; no filesystem or model authority. */
const SmelterWorkbench = (() => {
  let resourcePreference=null, lastResources=null;
  const paths = {
    forge:'M4 5h16v4H4z M7 9v5l5 6 5-6V9 M12 3v2',
    menu:'M4 6h16 M4 12h16 M4 18h16',
    close:'m6 6 12 12 M18 6 6 18',
    settings:'M4 6h16 M4 12h16 M4 18h16 M8 3v6 M16 9v6 M10 15v6',
    plus:'M12 5v14 M5 12h14',
    arrow:'M5 12h14 m-6-6 6 6-6 6',
    shield:'M12 3 4 6v6c0 4 8 9 8 9s8-5 8-9V6z m-4 9 3 3 5-6',
    search:'M21 21l-5-5 M18 10a7 7 0 1 1-14 0 7 7 0 0 1 14 0',
    cube:'m12 3 9 5v8l-9 5-9-5V8z M3 8l9 5 9-5 M12 13v8',
    layers:'m12 3 10 5-10 5L2 8z M2 12l10 5 10-5 M2 16l10 5 10-5'
  };
  function icon(name, doc=document) {
    const svg=doc.createElementNS('http://www.w3.org/2000/svg','svg');
    svg.setAttribute('viewBox','0 0 24 24');svg.setAttribute('fill','none');svg.setAttribute('stroke','currentColor');
    svg.setAttribute('stroke-width','1.7');svg.setAttribute('stroke-linecap','round');svg.setAttribute('stroke-linejoin','round');
    svg.setAttribute('aria-hidden','true');svg.setAttribute('focusable','false');svg.classList.add('ui-icon');
    const path=doc.createElementNS('http://www.w3.org/2000/svg','path');path.setAttribute('d',paths[name]||paths.layers);svg.append(path);return svg;
  }
  function labelButton(button, name, doc=document) { button.prepend(icon(name,doc));button.classList.add('icon-label-button'); }
  function notify(message, doc=document) {
    let host=doc.getElementById('workbenchNotifications');
    if(!host){host=doc.createElement('div');host.id='workbenchNotifications';host.className='notifications';doc.body.append(host)}
    host.replaceChildren();const notice=doc.createElement('div');notice.className='notification';notice.setAttribute('role','alert');
    const text=doc.createElement('span');text.textContent=String(message);const close=doc.createElement('button');close.type='button';close.setAttribute('aria-label','Dismiss notification');close.append(icon('close',doc));close.onclick=()=>notice.remove();notice.append(text,close);host.append(notice);
  }
  function empty(log,{hasConversation=false,onNew,onSettings,onAttach},doc=document) {
    log.replaceChildren();const box=doc.createElement('section');box.className='workbench-empty';
    const mark=doc.createElement('div');mark.className='empty-mark';mark.append(icon('forge',doc));
    const eyebrow=doc.createElement('p');eyebrow.className='eyebrow';eyebrow.textContent='LOCAL AI WORKBENCH';
    const heading=doc.createElement('h2');heading.textContent=hasConversation?'Conversation ready.':'Start a conversation.';
    const copy=doc.createElement('p');copy.textContent=hasConversation?'Write a message or attach a model. Choose tool access before asking the AI to work on files.':'Type a message below to start. The conversation is named from your first message.';
    box.append(mark,eyebrow,heading,copy);
    const cards=doc.createElement('div');cards.className='starter-grid';
    for(const [symbol,title,note,action] of [
      ['cube','Preview a 3D model','View GLBs, play clips and export a frame.',onAttach],
      ['layers','Choose your skills','Review instructions available to the AI.',()=>onSettings('skillsPanel')],
      ['shield','Set file boundaries','Register folders and review permissions.',()=>onSettings('accessPolicyPanel')]
    ]){const button=doc.createElement('button');button.className='starter-card';const text=doc.createElement('strong');text.textContent=title;const sub=doc.createElement('span');sub.textContent=note;button.append(icon(symbol,doc),text,sub);button.onclick=action;cards.append(button)}
    const note=doc.createElement('p');note.className='empty-boundary';note.textContent='Skills guide the work. Approved tools perform the actions.';box.append(cards,note);log.append(box);
  }
  function mount({main,shell,left,workspace,log,input,newChat,settings,engineLabel,status,onAttach,onEmpty},doc=document) {
    const appbar=doc.createElement('header');appbar.className='appbar';
    const brand=doc.createElement('div');brand.className='app-brand';
    const h1=main.querySelector(':scope > h1');h1.textContent='SMELTER';brand.append(icon('forge',doc),h1);
    const subtitle=main.querySelector(':scope > p');subtitle.className='app-subtitle';brand.append(subtitle);
    const runtime=doc.createElement('span');runtime.id='configuredRuntime';runtime.className='runtime-chip';runtime.textContent='Configuration loading';
    const menu=doc.createElement('button');menu.id='historyToggle';menu.type='button';menu.className='history-toggle';menu.setAttribute('aria-controls','leftbar');menu.setAttribute('aria-expanded','false');menu.setAttribute('aria-label','Open conversations');menu.append(icon('menu',doc));
    appbar.append(menu,brand,runtime);main.prepend(appbar);
    const skip=doc.createElement('a');skip.className='skip-link';skip.href='#workspace';skip.textContent='Skip to workbench';main.prepend(skip);workspace.tabIndex=-1;
    const scrim=doc.createElement('button');scrim.className='history-scrim';scrim.type='button';scrim.hidden=true;scrim.setAttribute('aria-label','Close conversations');shell.append(scrim);
    const closeHistory=()=>{workspace.inert=false;shell.classList.remove('history-open');scrim.hidden=true;menu.setAttribute('aria-expanded','false');menu.setAttribute('aria-label','Open conversations')};
    menu.onclick=()=>{const open=!shell.classList.contains('history-open');shell.classList.toggle('history-open',open);workspace.inert=open;scrim.hidden=!open;menu.setAttribute('aria-expanded',String(open));menu.setAttribute('aria-label',open?'Close conversations':'Open conversations');if(open)newChat.focus()};
    scrim.onclick=closeHistory;
    const updateMenu=()=>{menu.disabled=shell.hidden;if(shell.hidden)closeHistory()};new MutationObserver(updateMenu).observe(shell,{attributes:true,attributeFilter:['hidden']});updateMenu();
    doc.addEventListener('keydown',event=>{if(event.key==='Escape'&&!settings.dialog.open&&shell.classList.contains('history-open')){closeHistory();menu.focus()}});
    window.addEventListener('resize',()=>{if(matchMedia('(min-width:801px)').matches)closeHistory();if(resourcePreference===null&&lastResources)resources(lastResources.status,lastResources.settings,doc)});
    left.addEventListener('click',event=>{if(event.target.closest('.chat-open'))closeHistory()});
    newChat.addEventListener('click',closeHistory);newChat.textContent='New chat';labelButton(newChat,'plus',doc);
    left.querySelector('h2').textContent='Conversations';
    const search=doc.getElementById('chatSearch'),searchLabel=doc.createElement('label');searchLabel.htmlFor='chatSearch';searchLabel.className='field-caption';searchLabel.textContent='Find a conversation';search.before(searchLabel);
    const footer=doc.createElement('p');footer.className='sidebar-note';footer.textContent='Local conversations. Explicit access. Recorded results.';left.append(footer);
    // The conversation title leads the workspace toolbar instead of taking its own row.
    const title=doc.getElementById('chatTitle');settings.toolbar.prepend(title);
    input.placeholder='Ask a question, describe a task, or attach a file…';
    const inputLabel=doc.createElement('label');inputLabel.htmlFor=input.id;inputLabel.className='visually-hidden';inputLabel.textContent='Message';input.before(inputLabel);
    engineLabel.classList.add('composer-engine');
    input.title='Enter to send · Shift+Enter for a new line';
    status.classList.add('task-status');
    const statusState=()=>{const text=status.textContent.toLowerCase();status.dataset.state=/failed|error|unavailable|rejected/.test(text)?'error':/partial|unknown|stopp/.test(text)?'warning':/completed|saved|ready/.test(text)?'ready':'working'};
    new MutationObserver(statusState).observe(status,{childList:true,subtree:true,characterData:true});statusState();
    for(const [id,label] of [['archivepath','Archive file path'],['mediapath','Media file path'],['dbdirectory','Database directory'],['aeroInput','Task to classify']]){
      const field=doc.getElementById(id);if(!field)continue;const visible=doc.createElement('label');visible.htmlFor=id;visible.className='field-caption';visible.textContent=label;field.before(visible)
    }
    labelButton(settings.toolbar.querySelector('button:last-child'),'settings',doc);
    const add=doc.querySelector('.attachment-add');if(add){add.replaceChildren(icon('plus',doc))}
    window.showEmptyConversation=onEmpty;onEmpty();
    return {closeHistory};
  }
  function context(configuration,doc=document) {
    const target=doc.getElementById('configuredRuntime');if(!target)return;
    target.textContent=configuration?.model?'Configured · '+configuration.model:'Configuration unavailable';
    target.title='Saved model selection. This is not an inference-readiness check.';
  }
  function resources(status,settings,doc=document) {
    const host=doc.getElementById('sysfooter');if(!host)return;
    lastResources={status,settings};
    const expanded=resourcePreference ?? matchMedia('(min-width:900px)').matches;
    const details=doc.createElement('details');details.className='resource-details';details.open=expanded;
    const summary=doc.createElement('summary');summary.textContent='Host resources · DB '+status.database.status;summary.onclick=()=>{resourcePreference=!details.open};
    const list=doc.createElement('div');list.className='resource-grid';
    const gb=n=>Number.isFinite(n)?(n/1073741824).toFixed(1)+' GiB':'unavailable';
    for(const [label,value] of [
      ['CPU',status.cpu.status==='ready'?status.cpu.percent+'%':status.cpu.status],
      ['RAM',status.memory.status==='ready'?gb(status.memory.used_bytes)+' / '+gb(status.memory.total_bytes):status.memory.status],
      ['GPU allocation',status.gpu.status==='ready'?gb(status.gpu.allocated_bytes):'unavailable'],
      ['Loaded model',status.models.status==='ready'?(status.models.models.map(m=>m.name).join(', ')||'none'):'unavailable'],
      ['Free disk',gb(status.storage.free_bytes)]
    ]){const item=doc.createElement('span');const name=doc.createElement('strong');name.textContent=label;item.append(name,doc.createTextNode(String(value)));list.append(item)}
    const button=doc.createElement('button');button.textContent='System details';button.type='button';button.onclick=()=>settings.open('systemStatusPanel');list.append(button);details.append(summary,list);host.replaceChildren(details);
    host.title='Host observations, not container quotas. GPU allocation comes from Ollama and is not utilization; iGPU memory is shared with RAM.';
  }
  return {icon,labelButton,notify,empty,mount,context,resources};
})();
