const fs=require('fs'),path=require('path');
const sharp=require('/Users/tantalum/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
const {Potrace}=require('./potrace-runtime/node_modules/potrace');
const a=path.resolve('output/brand/2026-09-17-senplate-selected-a');
function svg(w,h,b,t){return `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}"><title>${t}</title>${b}</svg>`;}
async function region(name,roi){
 const {data,info}=await sharp(path.join(a,'source-selected-a.png')).extract(roi).ensureAlpha().raw().toBuffer({resolveWithObject:true});
 const mask=new Uint8Array(info.width*info.height);let x0=info.width,y0=info.height,x1=-1,y1=-1;
 for(let y=0;y<info.height;y++)for(let x=0;x<info.width;x++){const i=(y*info.width+x)*info.channels,r=data[i],g=data[i+1],b=data[i+2];if(g-r>12&&g-b>3&&r<145){mask[y*info.width+x]=1;x0=Math.min(x0,x);y0=Math.min(y0,y);x1=Math.max(x1,x);y1=Math.max(y1,y);}}
 const w=x1-x0+5,h=y1-y0+5,pix=Buffer.alloc(w*h*4,255),target=new Uint8Array(w*h);
 for(let y=y0;y<=y1;y++)for(let x=x0;x<=x1;x++)if(mask[y*info.width+x]){const j=(y-y0+2)*w+x-x0+2;target[j]=1;pix[j*4]=pix[j*4+1]=pix[j*4+2]=0;}
 const buffer=await sharp(pix,{raw:{width:w,height:h,channels:4}}).png().toBuffer();
 const p=new Potrace({threshold:128,color:'#163F35',background:'transparent',turdSize:8,alphaMax:1,optCurve:true,optTolerance:0.2});
 await new Promise((resolve,reject)=>p.loadImage(buffer,e=>e?reject(e):resolve()));
 const body=p.getPathTag(),text=svg(w,h,body,'Senplate '+name);fs.writeFileSync(path.join(a,`senplate-${name}-green.svg`),text+'\n');
 const rendered=await sharp(Buffer.from(text)).ensureAlpha().raw().toBuffer({resolveWithObject:true});let u=0,i=0;for(let k=0;k<target.length;k++){const v=rendered.data[k*rendered.info.channels+rendered.info.channels-1]>=128?1:0;u+=v||target[k]?1:0;i+=v&&target[k]?1:0;}
 return {name,roi,box:{x:roi.left+x0,y:roi.top+y0,width:x1-x0+1,height:y1-y0+1},canvas:{width:w,height:h,padding:2},silhouette_iou:i/u,body};
}
(async()=>{const m=await region('mark',{left:240,top:232,width:360,height:190}),w=await region('wordmark',{left:610,top:232,width:700,height:190});const x=Math.min(m.box.x,w.box.x),y=Math.min(m.box.y,w.box.y),width=Math.max(m.box.x+m.box.width,w.box.x+w.box.width)-x+4,height=Math.max(m.box.y+m.box.height,w.box.y+w.box.height)-y+4;const body=`<g transform="translate(${m.box.x-x} ${m.box.y-y})">${m.body}</g><g transform="translate(${w.box.x-x} ${w.box.y-y})">${w.body}</g>`;fs.writeFileSync(path.join(a,'senplate-logo-green.svg'),svg(width,height,body,'senplate')+'\n');const report={method:'Source-pixel contour analysis followed by Potrace cubic-curve fitting; no font substitution; original PNG unchanged',tool:'potrace 2.1.8',options:{threshold:128,turdSize:8,alphaMax:1,optCurve:true,optTolerance:0.2},mark:{...m,body:undefined},wordmark:{...w,body:undefined},lockup:{width,height,wordmark_offset:[w.box.x-x,w.box.y-y]},note:'Silhouette IoU is a diagnostic against the classified source, not a trademark or legal score.'};fs.writeFileSync(path.join(__dirname,'vectorization-final.json'),JSON.stringify(report,null,2)+'\n');process.stdout.write(JSON.stringify(report,null,2)+'\n');})();
