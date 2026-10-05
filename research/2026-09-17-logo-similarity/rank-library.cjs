const fs = require('fs');
const path = require('path');
const sharp = require('/Users/tantalum/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
const dir = __dirname;
const N = 96;
async function mask(svg) {
  const { data, info } = await sharp(Buffer.from(svg)).resize(N, N, { fit: 'contain', background: '#00000000' }).ensureAlpha().raw().toBuffer({ resolveWithObject: true });
  return Uint8Array.from({length: N*N}, (_, i) => data[i*info.channels+info.channels-1] >= 128 ? 1 : 0);
}
function score(a,b,rot){let intersection=0,union=0;for(let y=0;y<N;y++)for(let x=0;x<N;x++){let bx=x,by=y;if(rot===90){bx=y;by=N-1-x;}if(rot===180){bx=N-1-x;by=N-1-y;}if(rot===270){bx=N-1-y;by=x;}const v=a[y*N+x],w=b[by*N+bx];intersection+=v&&w?1:0;union+=v||w?1:0;}return intersection/union;}
(async()=>{
  const target = await mask(fs.readFileSync(path.join(dir,'../../output/brand/2026-09-17-senplate-vector/interval-mark.svg'),'utf8'));
  const names=fs.readdirSync(path.join(dir,'library-svg')).filter(n=>n.endsWith('.svg'));
  const results=[],errors=[];let index=0;
  async function worker(){while(index<names.length){const name=names[index++];try{const b=await mask(fs.readFileSync(path.join(dir,'library-svg',name),'utf8'));const scores=[0,90,180,270].map(rotation=>({rotation,iou:score(target,b,rotation)}));const best=scores.reduce((a,b)=>a.iou>b.iou?a:b);results.push({slug:path.basename(name,'.svg'),original_iou:scores[0].iou,best_iou:best.iou,best_rotation:best.rotation});}catch(e){errors.push({name,error:String(e)})}}}
  await Promise.all(Array.from({length:4},worker));
  results.sort((a,b)=>b.best_iou-a.best_iou);
  const out={method:'Binary alpha-mask Jaccard overlap at 96x96, preserving aspect ratio, tested 0/90/180/270 rotations. Candidate retrieval only; scores are not trademark similarity, legal risk or clearance.',library:'Simple Icons 16.31.0',count:names.length,rendered:results.length,errors,results};
  fs.writeFileSync(path.join(dir,'library-shape-ranking.json'),JSON.stringify(out,null,2)+'\n');
  process.stdout.write(JSON.stringify({count:out.count,rendered:out.rendered,errors:errors.length,top:results.slice(0,35)},null,2)+'\n');
})();
