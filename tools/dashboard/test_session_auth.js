const {test}=require('node:test');
const assert=require('node:assert/strict');
const auth=require('./session_auth.js');
test('token is read from the current fragment on every request',()=>{
 const location={hash:'#token=old-session-token'};
 assert.equal(auth.token(location),'old-session-token');
 location.hash='#token=new-session-token';
 assert.equal(auth.token(location),'new-session-token');
 location.hash='';assert.equal(auth.token(location),'');
});
test('same-origin launch URLs and plain tokens are accepted',()=>{
 assert.equal(auth.parse('http://127.0.0.1:8768/#token=new-session-token','http://127.0.0.1:8768'),'new-session-token');
 const location={origin:'http://127.0.0.1:8768',hash:''};
 auth.apply('new-session-token',location);assert.equal(auth.token(location),'new-session-token');
});
test('different origins, paths and malformed tokens are rejected',()=>{
 for(const value of ['http://evil.test/#token=new-session-token','http://127.0.0.1:8769/#token=new-session-token','http://127.0.0.1:8768/other#token=new-session-token','http://127.0.0.1:8768/','abc','<script>']){
  assert.throws(()=>auth.parse(value,'http://127.0.0.1:8768'));
 }
});
test('one rejected request halts every later request with that token until the token changes',async()=>{
 let calls=0,notices=0;const fetchImpl=async()=>{calls++;return new Response('{}',{status:calls===1?403:200})};
 const f=auth.guard(fetchImpl,()=>notices++),old={headers:{'X-Smelter-Token':'stale-token-1'}};
 assert.equal((await f('/api/native-progress',old)).status,403);
 for(const path of ['/api/native-progress','/api/task-trace/artifacts','/api/skills/status'])assert.equal((await f(path,old)).status,403);
 assert.equal(calls,1);assert.equal(notices,1);assert.ok(auth.isRejected('stale-token-1'));
 assert.equal((await f('/api/native-progress',{headers:{'X-Smelter-Token':'fresh-token-2'}})).status,200);assert.equal(calls,2);
 await f('/assets/x.js');assert.equal(calls,3);
});
