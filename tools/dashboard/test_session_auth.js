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
