const fs = require('fs');
const path = require('path');
const sharp = require('/Users/tantalum/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
const tracer = require('./vendor/imagetracer_v1.2.6.js');
const asset = path.resolve('output/brand/2026-09-17-senplate-selected-a');
const qa = __dirname;
const source = path.join(asset, 'source-selected-a.png');
const color = [22, 63, 53];
const opts = {ltres:0.01,qtres:4,pathomit:8,rightangleenhance:false,colorsampling:0,numberofcolors:2,mincolorratio:0,colorquantcycles:1,strokewidth:0,linefilter:false,scale:1,roundcoords:2,viewbox:true,desc:false,blurradius:0,pal:[{r:0,g:0,b:0,a:0},{r:22,g:63,b:53,a:255}]};
function svg(w,h,body,title){return `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" fill="none"><title>${title}</title>${body}</svg>`;}
async function traceRegion(name, roi) {
  const {data,info}=await sharp(source).extract(roi).ensureAlpha().raw().toBuffer({resolveWithObject:true});
  const mask=new Uint8Array(info.width*info.height); let xmin=info.width,ymin=info.height,xmax=-1,ymax=-1;
  for(let y=0;y<info.height;y++)for(let x=0;x<info.width;x++){
    const i=(y*info.width+x)*info.channels,r=data[i],g=data[i+1],b=data[i+2];
    if(g-r>12 && g-b>3 && r<145){mask[y*info.width+x]=1;xmin=Math.min(xmin,x);ymin=Math.min(ymin,y);xmax=Math.max(xmax,x);ymax=Math.max(ymax,y);}
  }
  if(xmax<0)throw new Error('No foreground');
  const pad=2,w=xmax-xmin+1+pad*2,h=ymax-ymin+1+pad*2;
  const rgba=new Uint8ClampedArray(w*h*4),target=new Uint8Array(w*h);
  for(let y=ymin;y<=ymax;y++)for(let x=xmin;x<=xmax;x++)if(mask[y*info.width+x]){
    const j=((y-ymin+pad)*w+x-xmin+pad);target[j]=1;rgba[j*4]=color[0];rgba[j*4+1]=color[1];rgba[j*4+2]=color[2];rgba[j*4+3]=255;
  }
  const raw=tracer.imagedataToSVG({width:w,height:h,data:rgba},opts);
  const paths=(raw.match(/<path\b[^>]*\/>/g)||[]).filter(p=>!p.includes('opacity="0"')).map(p=>p.replaceAll('rgb(22,63,53)','#163F35'));
  if(!paths.length)throw new Error('No paths');
  const output=svg(w,h,paths.join(''),'Senplate '+name);
  fs.writeFileSync(path.join(asset,`senplate-${name}-green.svg`),output+'\n');
  const raster=await sharp(Buffer.from(output)).ensureAlpha().raw().toBuffer({resolveWithObject:true});
  let intersection=0,union=0;for(let i=0;i<target.length;i++){const a=target[i],b=raster.data[i*raster.info.channels+raster.info.channels-1]>=128?1:0;intersection+=a&&b?1:0;union+=a||b?1:0;}
  return {name,roi,box:{x:roi.left+xmin,y:roi.top+ymin,width:xmax-xmin+1,height:ymax-ymin+1},canvas:{width:w,height:h,padding:pad},path_count:paths.length,silhouette_iou:intersection/union,body:paths.join('')};
}
(async()=>{
  const mark=await traceRegion('mark',{left:240,top:232,width:360,height:190});
  const word=await traceRegion('wordmark',{left:610,top:232,width:700,height:190});
  const x=Math.min(mark.box.x,word.box.x),y=Math.min(mark.box.y,word.box.y);
  const w=Math.max(mark.box.x+mark.box.width,word.box.x+word.box.width)-x+4,h=Math.max(mark.box.y+mark.box.height,word.box.y+word.box.height)-y+4;
  const body=`<g transform="translate(${mark.box.x-x} ${mark.box.y-y})">${mark.body}</g><g transform="translate(${word.box.x-x} ${word.box.y-y})">${word.body}</g>`;
  fs.writeFileSync(path.join(asset,'senplate-logo-green.svg'),svg(w,h,body,'senplate')+'\n');
  const report={source:'source-selected-a.png',method:'Source-pixel foreground analysis, contour vectorization, flat approved color; source PNG untouched. No font substitution.',foreground_rule:'g-r>12, g-b>3, r<145; primary upper logo only',options:opts,mark:{...mark,body:undefined},wordmark:{...word,body:undefined},lockup:{width:w,height:h,source_origin:[x,y],wordmark_offset:[word.box.x-x,word.box.y-y]},note:'IoU is agreement with the classified source silhouette, not a trademark metric or overall perceptual quality score.'};
  fs.writeFileSync(path.join(qa,'vectorization-report.json'),JSON.stringify(report,null,2)+'\n');
  process.stdout.write(JSON.stringify(report,null,2)+'\n');
})();
