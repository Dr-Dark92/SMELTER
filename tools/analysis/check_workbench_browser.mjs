/* Actual HTTP/UI/GLB contracts with synthetic inference and disposable data. */
import {createRequire} from 'node:module';
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import fs from 'node:fs';
import assert from 'node:assert/strict';
const require=createRequire(import.meta.url);
const {chromium}=require(process.env.SMELTER_TEST_PLAYWRIGHT||'playwright');
const repo=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const args=process.argv.slice(2);
if(args.length&&(args.length!==2||args[0]!=='--output'))throw Error('Use --output with a new evidence directory');
const output=args.length?path.resolve(args[1]):path.join(repo,'.smelter/ui-checks');
if(args.length&&fs.existsSync(output))throw Error('Browser evidence directory already exists; no overwrite');
fs.mkdirSync(output,{recursive:true});
const fixture=spawn(process.env.SMELTER_TEST_PYTHON||'python',['tools/analysis/offline_gui_fixture.py','--port','0','--viewer-root',repo],{cwd:repo,stdio:['ignore','pipe','pipe']});
let logs='',url,phase='fixture startup',browser,page;
const ready=new Promise((resolve,reject)=>{fixture.stdout.on('data',chunk=>{logs+=chunk.toString();const found=logs.match(/http:\/\/127\.0\.0\.1:\d+\/#token=[A-Za-z0-9_-]+/);if(found){url=found[0];resolve(url)}});fixture.on('error',reject);fixture.on('exit',code=>{if(!url)reject(Error('Fixture exited: '+code))})});
const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
function syntheticGlb(){
 const positions=Buffer.from(new Float32Array([-.5,0,0,.5,0,0,0,1,0]).buffer);
 const indices=Buffer.from(new Uint16Array([0,1,2]).buffer),times=Buffer.from(new Float32Array([0,1]).buffer),motion=Buffer.from(new Float32Array([0,0,0,0,.25,0]).buffer);
 const binary=Buffer.concat([positions,indices,Buffer.alloc(2),times,motion]);
 const document={asset:{version:'2.0'},scene:0,scenes:[{nodes:[0]}],nodes:[{mesh:0}],meshes:[{primitives:[{attributes:{POSITION:0},indices:1,material:0}]}],
  materials:[{doubleSided:true,pbrMetallicRoughness:{baseColorFactor:[1,.45,.15,1],metallicFactor:0,roughnessFactor:.8}}],
  buffers:[{byteLength:binary.length}],bufferViews:[{buffer:0,byteOffset:0,byteLength:36,target:34962},{buffer:0,byteOffset:36,byteLength:6,target:34963},{buffer:0,byteOffset:44,byteLength:8},{buffer:0,byteOffset:52,byteLength:24}],
  accessors:[{bufferView:0,componentType:5126,count:3,type:'VEC3',min:[-.5,0,0],max:[.5,1,0]},{bufferView:1,componentType:5123,count:3,type:'SCALAR'},{bufferView:2,componentType:5126,count:2,type:'SCALAR',min:[0],max:[1]},{bufferView:3,componentType:5126,count:2,type:'VEC3'}],
  animations:[0,1].map(i=>({name:'Fixture_'+i,samplers:[{input:2,output:3}],channels:[{sampler:0,target:{node:0,path:'translation'}}]}))};
 let json=Buffer.from(JSON.stringify(document));json=Buffer.concat([json,Buffer.alloc((4-json.length%4)%4,32)]);
 const header=Buffer.alloc(20);header.write('glTF');header.writeUInt32LE(2,4);header.writeUInt32LE(20+json.length+8+binary.length,8);header.writeUInt32LE(json.length,12);header.writeUInt32LE(0x4e4f534a,16);
 const binHeader=Buffer.alloc(8);binHeader.writeUInt32LE(binary.length,0);binHeader.writeUInt32LE(0x004e4942,4);
 return Buffer.concat([header,json,binHeader,binary]);
}
const findings={liveInference:false,liveDocker:false,syntheticAssets:true,pageErrors:[],externalRequests:[]};
try{
 let timer;try{await Promise.race([ready,new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('Fixture startup timed out')),15000)})])}finally{clearTimeout(timer)}
 const origin=new URL(url).origin;
 browser=await chromium.launch({headless:true,args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 page=await browser.newPage({viewport:{width:1440,height:1000},acceptDownloads:true});
 page.on('pageerror',error=>findings.pageErrors.push(error.message));page.on('request',request=>{if(/^https?:/.test(request.url())&&!request.url().startsWith(origin+'/'))findings.externalRequests.push(request.url())});
 await page.goto(url);await page.locator('#shell').waitFor({state:'visible'});
 phase='workbench empty state';await page.getByRole('heading',{name:'Start a conversation.',exact:true}).waitFor();assert.equal(await page.getByRole('button',{name:'Create conversation',exact:true}).count(),1);
 await page.screenshot({path:path.join(output,'workbench-desktop.png')});
 phase='settings navigation';await page.getByRole('button',{name:'Settings',exact:true}).click();await page.getByRole('searchbox',{name:'Search settings',exact:true}).fill('locations');await page.getByRole('searchbox',{name:'Search settings',exact:true}).press('Enter');await page.locator('.locations-table tbody tr[data-location-id="source"]').waitFor();assert.equal(await page.locator('.settings-nav .navbtn:visible').count(),1);
 await page.getByRole('searchbox',{name:'Search settings',exact:true}).fill('');await page.screenshot({path:path.join(output,'settings-locations-desktop.png')});
 phase='folder browsing';await page.getByRole('button',{name:'+ Add',exact:true}).click();const editor=page.getByRole('dialog',{name:'Add registered location',exact:true});await editor.getByRole('button',{name:'Browse…',exact:true}).click();const folder=page.getByRole('dialog',{name:'Browse folders',exact:true});await folder.getByRole('button',{name:'Current checkout',exact:true}).click();await folder.getByRole('button',{name:'Open Assets',exact:true}).click();await folder.getByRole('button',{name:'Open Characters',exact:true}).waitFor();assert.equal(await folder.getByText('notes.txt',{exact:true}).count(),0);await page.screenshot({path:path.join(output,'folder-browser.png')});await folder.getByRole('button',{name:'Select folder',exact:true}).click();await editor.getByRole('textbox',{name:'Location name',exact:true}).fill('Browser assets');await editor.getByRole('button',{name:'Add to draft',exact:true}).click();await page.getByRole('button',{name:'Apply',exact:true}).click();await page.locator('.locations-status').filter({hasText:'Applied.'}).waitFor();
 phase='skills table';await page.getByRole('button',{name:'Skills',exact:true}).click();await page.getByRole('button',{name:'Expand demo-design',exact:true}).click();await page.getByRole('checkbox',{name:'Select demo-design/spacing',exact:true}).check();page.once('dialog',dialog=>dialog.accept());await page.getByRole('button',{name:'Enable',exact:true}).click();await page.waitForFunction(()=>document.querySelector('tr[data-skill-id="demo-design/spacing"]').innerText.includes('Enabled'));await page.getByRole('button',{name:'Use in next task',exact:true}).click();await page.screenshot({path:path.join(output,'settings-skills-desktop.png')});
 phase='large skill catalogue';await page.getByRole('button',{name:'+ Add',exact:true}).click();const importer=page.getByRole('dialog',{name:'Import skills',exact:true});await importer.getByLabel('GitHub skill or repository URL',{exact:true}).fill('https://github.com/offline/catalogue');await importer.getByRole('button',{name:'Discover',exact:true}).click();await importer.getByText(/311 manifests found/).waitFor();assert.equal(await importer.locator('.import-candidates input:checked').count(),0);assert.equal(await importer.locator('.import-candidates input').count(),311);await importer.getByLabel('Filter discovered skills',{exact:true}).fill('catalogue-007');assert.equal(await importer.locator('.import-candidates label:visible').count(),1);await importer.getByLabel('Filter discovered skills',{exact:true}).fill('');await importer.locator('.import-candidates input').evaluateAll(nodes=>nodes.slice(0,41).forEach(node=>{node.checked=true;node.dispatchEvent(new Event('change',{bubbles:true}))}));await importer.getByRole('button',{name:'Review selected manifests',exact:true}).click();await importer.getByText('Select at most 40 manifests per reviewed import.',{exact:true}).waitFor();assert.equal(await importer.getByRole('button',{name:'Import reviewed skills',exact:true}).isDisabled(),true);await importer.getByRole('button',{name:'Close',exact:true}).click();findings.largeSkillCatalogue=true;
 await page.getByRole('button',{name:'Close settings',exact:true}).click();
 phase='titled chat and offline send';await page.getByRole('button',{name:'New chat',exact:true}).click();await page.getByLabel('Conversation title',{exact:true}).fill('Offline workbench review');await page.getByRole('dialog',{name:'New conversation',exact:true}).getByRole('button',{name:'Create conversation',exact:true}).click();await page.locator('.chat-dialog').waitFor({state:'detached'});assert.equal(await page.locator('#chatEngine').inputValue(),'opencode');await page.getByLabel('Message',{exact:true}).fill('Hello fixture');await page.getByRole('button',{name:'Send via OpenCode',exact:true}).click();assert.match(await page.locator('#requestStatus').innerText(),/approve this session/);await page.locator('#chatEngine').selectOption('ollama');await page.getByRole('button',{name:'Send',exact:true}).click();await page.waitForFunction(()=>document.querySelector('#requestStatus').textContent.startsWith('Completed'));await page.getByText('Offline fixture response. No model was called.',{exact:true}).waitFor();
 phase='startup retry does not duplicate workflow choices';
 const workflowChoices=await page.locator('#workflow option').count();
 const workflowReload=page.waitForResponse(response=>response.url().endsWith('/api/workflows'));
 await page.evaluate(()=>startup());
 await workflowReload;
 await page.waitForFunction(expected=>document.querySelectorAll('#workflow option').length===expected,workflowChoices);
 assert.equal(await page.locator('#workflow option').count(),workflowChoices);
 phase='Stop and refresh recovery';
 await page.getByLabel('Message',{exact:true}).fill('slow fixture');
 await page.getByRole('button',{name:'Send',exact:true}).click();
 await page.waitForFunction(()=>document.querySelector('#requestStatus').textContent.includes('Offline fixture waiting for Stop'));
 const savedTask=await page.evaluate(()=>JSON.parse(sessionStorage.getItem('smelterActiveJob')).id);
 await page.reload();
 await page.waitForFunction(()=>[...document.querySelectorAll('button')].some(node=>node.textContent==='Stop'&&!node.disabled));
 await page.getByRole('button',{name:'Stop',exact:true}).click();
 await page.waitForFunction(()=>document.querySelector('#requestStatus').textContent.startsWith('Stopped'));
 const recovered=await page.evaluate(async id=>{
  const response=await fetch('/api/chat-jobs/'+id,{headers:{'X-Smelter-Token':SmelterAuth.token()}});
  return response.json();
 },savedTask);
 assert.equal(recovered.state,'cancelled');findings.stopAndRefreshRecovery=true;
 phase='coding receipt presentation';
 const states=await page.evaluate(()=>{
  const section=executionCards({events:[
   {tool:'run_coding_tests',result:{status:'coding_tests_failed',stage:'ERROR',profile:'node',exit_code:1}},
   {tool:'run_coding_tests',result:{status:'coding_tests_failed',stage:'RED',profile:'python',exit_code:1}},
   {tool:'review_coding_workspace',result:{status:'coding_workspace_reviewed',all_current_tests_passed:false}}
  ]});
  return [...section.querySelectorAll('.execution-card')].map(node=>({className:node.className,text:node.textContent}));
 });
 assert.match(states[0].className,/execution-error/);assert.match(states[0].text,/Runner\/import failure/);
 assert.match(states[1].className,/execution-warning/);assert.match(states[1].text,/Expected failing assertion/);
 assert.match(states[2].className,/execution-warning/);assert.match(states[2].text,/incomplete or stale/);
 findings.codingReceiptStates=true;
 // A reload intentionally clears the previous task-skill selection. Select
 // the same enabled fixture again before checking the outgoing payload.
 await page.getByRole('button',{name:'Settings',exact:true}).click();
 await page.getByRole('button',{name:'Skills',exact:true}).click();
 await page.getByRole('button',{name:'Expand demo-design',exact:true}).click();
 await page.getByRole('checkbox',{name:'Select demo-design/spacing',exact:true}).check();
 await page.getByRole('button',{name:'Use in next task',exact:true}).click();
 await page.getByRole('button',{name:'Close settings',exact:true}).click();
 phase='OpenCode GUI forwarding';
 await page.route('**/api/opencode/agent',route=>route.fulfill({json:{endpoint:'fixture only',version:'1.19.3',directory:'fixture',expected_directory:'fixture',agent_ready:true,models:[{key:'local/qwen3.5:9b'}],reason:'Synthetic readiness response; no runtime started'}}));
 await page.locator('#chatEngine').selectOption('opencode');await page.getByRole('button',{name:'Settings',exact:true}).click();await page.getByRole('button',{name:'Next-task tool access',exact:true}).click();await page.getByRole('button',{name:'Check managed OpenCode',exact:true}).click();await page.locator('#opencodeAgentApprove').check();await page.locator('#approveDiagnostics').check();await page.locator('#approveCodingWorkspace').check();await page.getByRole('button',{name:'Close settings',exact:true}).click();
 let admitted;
 const intercept=async route=>{const body=route.request().postDataJSON();if(body.action!=='start')return route.continue();admitted=body;await route.fulfill({status:400,json:{error:'Synthetic admission capture; no model task was started'}})};
 await page.route('**/api/chats',intercept);await page.getByLabel('Message',{exact:true}).fill('Verify selected skill and tool forwarding');await page.getByRole('button',{name:'Send via OpenCode',exact:true}).click();await page.waitForFunction(()=>document.querySelector('#requestStatus').textContent.includes('Synthetic admission capture'));
 assert.equal(admitted.engine,'opencode');assert.deepEqual(admitted.skills,['demo-design/spacing']);assert.equal(admitted.tool_permissions.write_diagnostics,true);assert.equal(admitted.tool_permissions.coding_workspace,true);assert.equal(admitted.opencode_approval,true);assert.equal(await page.locator('#opencodeAgentApprove').isChecked(),false);assert.equal(await page.locator('#approveDiagnostics').isChecked(),false);assert.equal(await page.locator('#approveCodingWorkspace').isChecked(),false);
 await page.unroute('**/api/chats',intercept);await page.unroute('**/api/opencode/agent');await page.locator('#chatEngine').selectOption('ollama');findings.openCodeGuiForwarding=true;
 phase='attachments';await page.getByRole('button',{name:'Add attachment',exact:true}).click();await page.getByRole('menuitem',{name:/Photos & screenshots/}).waitFor();await page.keyboard.press('Escape');assert.equal(await page.getByRole('menu',{name:'Supported attachments'}).isVisible(),false);
 phase='GLB upload and rendering';await page.locator('#modelFile').setInputFiles({name:'animated-fixture.glb',mimeType:'model/gltf-binary',buffer:syntheticGlb()});await page.waitForFunction(()=>document.querySelector('#requestStatus').textContent.startsWith('GLB saved'));
 const card=page.locator('.model-card');async function load(){await card.getByRole('button',{name:'Load 3D preview',exact:true}).click();await card.getByRole('status').filter({hasText:'Ready · drag'}).waitFor({timeout:60000})}
 await load();assert.equal(await card.locator('model-viewer').evaluate(v=>v.availableAnimations.length),2);
 phase='GLB animation playback';
 await card.getByLabel('Animation clip',{exact:true}).selectOption('1');
 await card.getByRole('button',{name:'Play animation',exact:true}).click();
 // Selecting the controls can scroll the stage out of the chat viewport.
 // model-viewer intentionally suspends offscreen animation; observe a visible stage.
 await card.locator('model-viewer').scrollIntoViewIfNeeded();
 await page.waitForFunction(()=>document.querySelector('model-viewer').currentTime>0);
 await card.getByRole('button',{name:'Pause animation',exact:true}).click();
 await card.getByLabel('Animation label',{exact:true}).fill('Verified fixture clip');await card.getByRole('button',{name:'Save animation name',exact:true}).click();await card.getByRole('status').filter({hasText:'Animation name saved.'}).waitFor();
 let downloads=0;page.on('download',()=>downloads++);const pngEvent=page.waitForEvent('download');await card.getByRole('button',{name:'Save PNG',exact:true}).click();await (await pngEvent).saveAs(path.join(output,'model-preview.png'));assert(fs.statSync(path.join(output,'model-preview.png')).size>100);
 const webmEvent=page.waitForEvent('download',{timeout:120000});await card.getByRole('button',{name:'Export turntable (WebM)',exact:true}).click();await (await webmEvent).saveAs(path.join(output,'model-turntable.webm'));assert(fs.statSync(path.join(output,'model-turntable.webm')).size>100);
 phase='GLB release during export';await card.locator('model-viewer').evaluate(v=>{window.oldViewer=v;v.toBlob=()=>new Promise(resolve=>window.finishSnapshot=resolve)});await card.getByRole('button',{name:'Export turntable (WebM)',exact:true}).click();await page.waitForFunction(()=>typeof window.finishSnapshot==='function');await card.getByRole('button',{name:'Release preview',exact:true}).click();await page.evaluate(()=>window.finishSnapshot(new Blob(['fixture'],{type:'image/png'})));await delay(150);assert.match(await card.getByRole('status').first().innerText(),/Preview released/);
 await load();assert.equal(await card.getByLabel('Animation clip',{exact:true}).isDisabled(),false);await page.evaluate(()=>window.oldViewer.dispatchEvent(new Event('load')));
 await card.locator('model-viewer').evaluate(v=>window.releasedViewer=v);await card.getByRole('button',{name:'Release preview',exact:true}).click();await page.evaluate(()=>window.releasedViewer.dispatchEvent(new Event('load')));assert.equal(await card.getByRole('button',{name:'Save PNG',exact:true}).isDisabled(),true);assert.equal(await card.getByLabel('Animation clip',{exact:true}).isDisabled(),true);
 phase='GLB stale PNG continuation';await load();await card.locator('model-viewer').evaluate(v=>{v.toBlob=()=>new Promise(resolve=>window.finishPng=resolve)});await card.getByRole('button',{name:'Save PNG',exact:true}).click();await page.waitForFunction(()=>typeof window.finishPng==='function');await card.getByRole('button',{name:'Release preview',exact:true}).click();await page.evaluate(()=>window.finishPng(new Blob(['fixture'],{type:'image/png'})));await delay(150);assert.equal(downloads,2);assert.equal(await card.getByRole('button',{name:'Save PNG',exact:true}).isDisabled(),true);
 phase='GLB error and reload';await load();await card.locator('model-viewer').evaluate(v=>v.dispatchEvent(new CustomEvent('error')));assert.equal(await card.getByRole('button',{name:'Save PNG',exact:true}).isDisabled(),true);await load();assert.equal(await card.getByLabel('Animation clip',{exact:true}).isDisabled(),false);await page.screenshot({path:path.join(output,'chat-and-glb-desktop.png')});await card.getByRole('button',{name:'Release preview',exact:true}).click();
 phase='responsive layouts';for(const width of [375,768,1024,1440]){await page.setViewportSize({width,height:900});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'Page overflow at '+width);if(width===375){await page.getByRole('button',{name:'Open conversations',exact:true}).click();assert.equal(await page.locator('#leftbar').isVisible(),true);assert.equal(await page.locator('#workspace').evaluate(n=>n.inert),true);await page.keyboard.press('Escape');assert.equal(await page.locator('#leftbar').isVisible(),false);assert.equal(await page.locator('#workspace').evaluate(n=>n.inert),false)}await page.screenshot({path:path.join(output,'chat-'+width+'.png')});await page.getByRole('button',{name:'Settings',exact:true}).click();if(width<=800){await page.getByRole('combobox',{name:'Settings section',exact:true}).selectOption('accessPolicyPanel');await page.locator('.locations-table').waitFor()}else await page.getByRole('button',{name:'Workspaces & Access',exact:true}).click();assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'Settings overflow at '+width);await page.screenshot({path:path.join(output,'settings-'+width+'.png')});await page.getByRole('button',{name:'Close settings',exact:true}).click()}
 phase='reduced motion';await page.emulateMedia({reducedMotion:'reduce'});assert(await page.getByRole('button',{name:'Settings',exact:true}).evaluate(node=>parseFloat(getComputedStyle(node).transitionDuration)<.02));
 phase='system component status and operator controls';
 await page.getByRole('button',{name:'Settings',exact:true}).click();
 await page.getByRole('button',{name:'System status',exact:true}).click();
 await page.locator('.component-table tbody tr[data-component="python"]').waitFor();
 assert.equal(await page.locator('.component-table tbody tr').count(),9);
 assert.equal(await page.getByRole('button',{name:'Start Python',exact:true}).isDisabled(),true);
 await page.getByRole('button',{name:'Status Python',exact:true}).click();
 await page.getByText('Status check completed.',{exact:true}).waitFor();
 await page.evaluate(()=>refreshSystem());
 assert.equal(await page.locator('.component-table tbody tr').count(),9);
 await page.getByRole('button',{name:'Stop MCP',exact:true}).click();
 await page.locator('tr[data-component="mcp"] .component-state').filter({hasText:'disabled'}).waitFor();
 assert.equal(await page.getByRole('button',{name:'Stop MCP',exact:true}).isDisabled(),true);
 await page.screenshot({path:path.join(output,'system-status-desktop.png')});
 await page.setViewportSize({width:375,height:900});
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'System status page overflow');
 await page.screenshot({path:path.join(output,'system-status-375.png')});
 await page.getByRole('button',{name:'Close settings',exact:true}).click();
 findings.systemComponentControls=true;
 assert.deepEqual(findings.pageErrors,[]);assert.deepEqual(findings.externalRequests,[]);
 Object.assign(findings,{result:'passed',settingsSearch:true,registeredLocations:true,folderBrowse:true,skillsBulk:true,titledChat:true,attachmentMenu:true,glbRender:true,animationPlaybackAndLabels:true,png:true,webm:true,releaseDuringExport:true,lateLoadIgnored:true,latePngIgnored:true,errorReload:true,widths:[375,768,1024,1440],reducedMotion:true});
 fs.writeFileSync(path.join(output,'result.json'),JSON.stringify(findings,null,2));console.log(JSON.stringify(findings));
}catch(error){if(page)await page.screenshot({path:path.join(output,'failure.png')}).catch(()=>{});fs.writeFileSync(path.join(output,'result.json'),JSON.stringify({...findings,result:'failed',phase,error:String(error).replace(/#token=[A-Za-z0-9_-]+/g,'#token=[REDACTED]')},null,2));console.error(('Browser check failed in '+phase+': '+error.stack).replace(/#token=[A-Za-z0-9_-]+/g,'#token=[REDACTED]'));process.exitCode=1}
finally{if(browser)await browser.close();fixture.kill('SIGTERM');await Promise.race([new Promise(resolve=>fixture.once('exit',resolve)),delay(5000)]);if(fixture.exitCode===null)fixture.kill('SIGKILL')}
