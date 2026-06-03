#!/usr/bin/env node
// Usage: node seed-architect-works.js <site-url> <admin-user> <admin-pass> <works-file>
const https=require('https'), http=require('http'), fs=require('fs'), path=require('path');
const [,,siteUrl,user,pass,file]=process.argv;
if(!siteUrl||!user||!pass||!file){console.error('Usage: node seed-architect-works.js <url> <user> <pass> <file>');process.exit(1);}
const data=JSON.parse(fs.readFileSync(path.resolve(file),'utf8'));
const base=siteUrl.replace(/\/$/,''), lib=base.startsWith('https')?https:http;
function req(method,p,body,cookie){return new Promise((res,rej)=>{const u=new URL(base+p),bs=body?JSON.stringify(body):null,opts={hostname:u.hostname,port:u.port||(base.startsWith('https')?443:80),path:u.pathname,method,headers:{'Content-Type':'application/json',...(bs?{'Content-Length':Buffer.byteLength(bs)}:{}),...(cookie?{Cookie:cookie}:{})}};const r=lib.request(opts,resp=>{let d='';resp.on('data',c=>d+=c);resp.on('end',()=>res({status:resp.statusCode,body:JSON.parse(d||'null'),headers:resp.headers}))});r.on('error',rej);if(bs)r.write(bs);r.end();});}
(async()=>{
  console.log('Logging in...');
  const login=await req('POST','/api/login',{username:user,password:pass});
  if(login.status!==200){console.error('Login failed:',login.body);process.exit(1);}
  const cookie=login.headers['set-cookie']?.[0]?.split(';')[0];
  console.log('Logged in. Seeding works for person',data.person_id);
  let added=0,failed=0;
  for(const w of data.works){
    const r=await req('POST','/api/architect-works',{...w,person_id:data.person_id},cookie);
    if(r.body?.ok){added++;process.stdout.write('.')}else{failed++;console.log('\nFailed:',w.name,r.body?.error);}
  }
  console.log(`\nDone: ${added} added, ${failed} failed`);
})();
