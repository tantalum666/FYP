const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '../../../');
const front = path.join(root, 'desk-companion/frontend');
const ts = require(path.join(front, 'node_modules/typescript'));
const src = path.join(front, 'src');
const files=[];
function walk(dir) { for (const item of fs.readdirSync(dir,{withFileTypes:true})) {const p=path.join(dir,item.name); if(item.isDirectory()) walk(p); else files.push(p);}}
walk(src);
const options=ts.parseJsonConfigFileContent(JSON.parse(fs.readFileSync(path.join(front,'tsconfig.json'),'utf8')), ts.sys, front).options;
function resolve(specifier, containing, paths, insensitive) {
 const fileMap=new Map(paths.map(p=>[insensitive?p.toLowerCase():p,p]));
 const dirs=new Set(); for(const f of paths) { let p=path.dirname(f); while(p!==path.dirname(p)){dirs.add(insensitive?p.toLowerCase():p);p=path.dirname(p);}}
 const canonical=p=>insensitive?p.toLowerCase():p;
 const host={fileExists:p=>fileMap.has(canonical(p)),readFile:p=>fs.readFileSync(fileMap.get(canonical(p)),'utf8'),directoryExists:p=>dirs.has(canonical(p)),getCurrentDirectory:()=>front,useCaseSensitiveFileNames:()=>!insensitive};
 return ts.resolveModuleName(specifier,containing,options,host).resolvedModule?.resolvedFileName;
}
const agent=path.join(src,'workspace/agent');
const oldHelper=path.join(agent,'publicCapture.ts');
const helper=path.join(agent,'capturePolicy.ts');
const component=path.join(agent,'PublicCapture.tsx');
const oldPaths=[...files.filter(p=>p!==helper && p!==oldHelper),oldHelper];
const evidence={typescript:ts.version,moduleResolution:'bundler',pre_fix:{case_sensitive:resolve('./PublicCapture',path.join(agent,'RunComposer.tsx'),oldPaths,false),case_insensitive:resolve('./PublicCapture',path.join(agent,'RunComposer.tsx'),oldPaths,true)}};
assert.equal(evidence.pre_fix.case_sensitive,component);
assert.equal(evidence.pre_fix.case_insensitive.toLowerCase(),oldHelper.toLowerCase());
assert.ok(fs.existsSync(helper),'renamed helper must exist');
assert.ok(!fs.existsSync(oldHelper),'old helper must be absent');
evidence.post_fix=[];
for(const [file,specifier,expected] of [['RunComposer.tsx','./PublicCapture',component],['RunPanel.tsx','./PublicCapture',component],['PublicCapture.tsx','./capturePolicy',helper],['SourcePreview.tsx','./capturePolicy',helper],['CaptureProvenance.tsx','./capturePolicy',helper],['usePublicCaptures.ts','./capturePolicy',helper]]) {
 const record={file,specifier,case_sensitive:resolve(specifier,path.join(agent,file),files,false),case_insensitive:resolve(specifier,path.join(agent,file),files,true)};
 assert.equal(record.case_sensitive,expected); assert.equal(record.case_insensitive,expected); evidence.post_fix.push(record);
}
console.log(JSON.stringify(evidence,null,2));
