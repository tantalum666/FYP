import fs from 'node:fs/promises';
import path from 'node:path';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';

const root='/Users/tantalum/Documents/ChatGPT/FYP';
const qa=path.join(root,'output/qa/hardware-procurement-2026-09-15');
const outDir=path.join(root,'outputs/01a07aeb-a256-7572-a42e-bd7e4668674f');
const data=JSON.parse(await fs.readFile(path.join(root,'planning/2026-09-15/procurement-data.json'),'utf8'));
await fs.mkdir(outDir,{recursive:true});
const wb=Workbook.create();
const bom=wb.worksheets.add('采购清单');
const cam=wb.worksheets.add('相机对比');
const wire=wb.worksheets.add('接线与装配');
const colors={ink:'#243247',navy:'#254569',blue:'#EAF1F7',amber:'#FFF1CC',grey:'#F4F6F8',muted:'#66758A'};

function base(sh,lastRow,lastCol){
 sh.showGridLines=false;
 const area=sh.getRange(`A1:${lastCol}${lastRow}`);
 area.format.font={name:'Arial',size:11,color:colors.ink};
 area.format.verticalAlignment='center';
 area.format.rowHeight=24;
 sh.getRange(`A1:A${lastRow}`).format.columnWidthPx=22;
}
function widths(sh,map,lastRow){for(const [c,w] of Object.entries(map))sh.getRange(`${c}1:${c}${lastRow}`).format.columnWidthPx=w;}
function header(sh,range){const r=sh.getRange(range);r.format.fill=colors.navy;r.format.font={bold:true,color:'#FFFFFF'};r.format.wrapText=true;r.format.horizontalAlignment='center';r.format.rowHeight=36;}
function note(sh,cell,body){wb.notes.add({id:`${sh.name}:${cell}`,target:{cell:{sheetName:sh.name,sheetId:sh.sheetId,address:cell}},authorId:'',createdAt:'',body:{plainText:body}});}
function title(sh,text){sh.getRange('B2').values=[[text]];sh.getRange('B2').format.font={size:16,bold:true,color:colors.navy};sh.getRange('B2').format.rowHeight=30;}
function number(sh,r,fmt='#,##0'){sh.getRange(r).setNumberFormat(fmt);sh.getRange(r).format.horizontalAlignment='right';}

const start=11,end=start+data.rows.length-1;
base(bom,end+2,'M');
widths(bom,{B:60,C:230,D:390,E:60,F:100,G:100,H:105,I:110,J:110,K:90,L:270,M:410},end+2);
title(bom,'Group 2 硬件采购清单');
bom.getRange('B3').values=[['日期']];bom.getRange('C3').values=[[new Date('2026-09-15T00:00:00Z')]];bom.getRange('C3').setNumberFormat('yyyy-mm-dd');
bom.getRange('I3:J3').values=[['预留下限 ¥','预留上限 ¥']];
bom.getRange('B4').values=[['已选物料预留（人民币，不含运费）']];
bom.getRange('I4').formulas=[[`=IF(COUNTIFS(I${start}:I${end},"待填数量")>0,"待填数量",SUM(I${start}:I${end}))`]];
bom.getRange('J4').formulas=[[`=IF(COUNTIFS(J${start}:J${end},"待填数量")>0,"待填数量",SUM(J${start}:J${end}))`]];
number(bom,'I4:J4');bom.getRange('I4:J4').format.font={size:16,bold:true,color:colors.navy};
bom.getRange('B6').values=[['人民币区间均为采购预留，不是淘宝／京东实时报价。官方美元参考价见“相机对比”。']];
bom.getRange('B7').values=[['黄色数量／实际单价可改。数量0表示不计入本次采购；已包含或可复用的物品避免重复购买。']];
bom.getRange('B8').values=[['实际单价空白时用预算区间；填写后，该行上下限都按实际单价计算。参数来源保存在物品单元格注释中。']];
bom.getRange('B6:B8').format.font={size:11,color:colors.muted};
const headers=['编号','采购项／型号','必须选对的规格','数量','预算单价低 ¥','预算单价高 ¥','实际单价 ¥','核算金额低 ¥','核算金额高 ¥','采购阶段','淘宝搜索词','装配与验收要点'];
bom.getRange('B10:M10').values=[headers];
bom.getRange(`B${start}:M${end}`).values=data.rows.map(r=>[r.id,r.item,r.spec,r.qty,r.low,r.high,r.actual,null,null,r.phase,r.search,r.assembly]);
const table=bom.tables.add(`B10:M${end}`,true,'HardwareBOM');table.style='TableStyleMedium2';
header(bom,'B10:M10');
bom.getRange(`B${start}:M${end}`).format.wrapText=true;
bom.getRange(`B${start}:M${end}`).format.rowHeight=52;
bom.getRange(`B${start}:M${end}`).format.fill='#FFFFFF';
for(let i=0;i<data.rows.length;i+=2)bom.getRange(`B${start+i}:M${start+i}`).format.fill=colors.grey;
bom.getRange(`D${start}:D${end}`).format.verticalAlignment='top';
bom.getRange(`L${start}:M${end}`).format.verticalAlignment='top';
bom.getRange(`E${start}:E${end}`).format.fill=colors.amber;
bom.getRange(`H${start}:H${end}`).format.fill=colors.amber;
number(bom,`E${start}:J${end}`,'#,##0.00');number(bom,`E${start}:E${end}`,'#,##0');
bom.getRange(`I${start}:I${end}`).formulas=data.rows.map((r,i)=>{const n=start+i;return [`=IF(ISBLANK(E${n}),"待填数量",IF(ISBLANK(H${n}),E${n}*F${n},E${n}*H${n}))`];});
bom.getRange(`J${start}:J${end}`).formulas=data.rows.map((r,i)=>{const n=start+i;return [`=IF(ISBLANK(E${n}),"待填数量",IF(ISBLANK(H${n}),E${n}*G${n},E${n}*H${n}))`];});
bom.getRange(`E${start}:E${end}`).dataValidation={rule:{type:'whole',operator:'between',formula1:0,formula2:100}};
bom.getRange(`E${start}:E${end}`).conditionalFormats.add('cellIs',{operator:'equal',formula:0,format:{font:{color:'#8993A3'}}});
bom.freezePanes.freezeRows(10);bom.freezePanes.freezeColumns(3);bom.tabColor=colors.navy;
for(let i=0;i<data.rows.length;i++){const r=data.rows[i];note(bom,`C${start+i}`,`参数依据：${r.source??'工程设计建议，通用件需按所选商品规格复核'}\n访问／整理：2026-09-15。人民币价格是工程采购预留，国内店铺及成交价未核实。\n${r.assembly}`);}

base(cam,20,'K');widths(cam,{B:190,C:200,D:105,E:245,F:230,G:240,H:260,I:375,J:300,K:420},20);title(cam,'3D 相机比较');
cam.getRange('B4').values=[['首购候选：Gemini 2。Gemini 335作为有现货、同条件验证后的备选，国内价格和库存均未核实。']];
cam.getRange('B5').values=[['官方国际价格不含国内溢价、运输或税费；相机宣称的2m精度不能当作近距菜盘体积／识别准确率。']];
cam.getRange('B6').values=[['只需要购买一款相机。当前Gemini 2国际套装列C-C线，Pi5另需A-C USB3数据线。']];
cam.getRange('B4:B6').format.font={color:colors.muted};
cam.getRange('B8:K8').values=[['型号','建议与库存','官方参考 USD','工作距离','深度输出／视野','彩色输出／视野','接口／供电','SDK与主机适配','套装线材','取舍与证据边界']];
cam.getRange('B9:K13').values=data.cameras.map(c=>[c.model,`${c.choice}\n${c.stock}`,c.priceUSD,c.range,c.depth,c.rgb,c.power,c.sdk,c.bundle,c.note]);
const ct=cam.tables.add('B8:K13',true,'CameraComparison');ct.style='TableStyleMedium2';header(cam,'B8:K8');
cam.getRange('B9:K13').format.wrapText=true;cam.getRange('B9:K13').format.rowHeight=80;cam.getRange('B9:K13').format.verticalAlignment='top';number(cam,'D9:D13','"$"#,##0"  "');
cam.getRange('B9:K13').format.fill='#FFFFFF';for(let r=9;r<=13;r+=2)cam.getRange(`B${r}:K${r}`).format.fill=colors.grey;
cam.getRange('B15').values=[['本表是产品与公开规格比较，没有对这些相机做同场景实测。Orbbec SDK的ARM64官方测试清单主要为Jetson，M2 macOS在支持清单中。']];
cam.getRange('B16').values=[['每款相机需在选定Pi5系统、固件与USB线下确认连续RGB-D采集；厂家支持某架构不等于整套FYP已验证。']];
cam.getRange('B15:B16').format.font={color:colors.muted};cam.freezePanes.freezeRows(8);cam.freezePanes.freezeColumns(2);
data.cameras.forEach((c,i)=>note(cam,`B${9+i}`,`来源：${c.source}\n公开价格/库存核对：2026-09-15。Gemini2与335使用Chrome读取国际店的实际页面；RealSense为官方比较页标价；SEN0583不使用页尾0.00占位价。\nOrbbec SDK：${data.sources.orbbec}\nRealSense参考价：${data.sources.rsprice}`));

base(wire,28,'G');widths(wire,{B:150,C:255,D:400,E:270,F:155,G:460},28);title(wire,'接线与装配');
wire.getRange('B4').values=[['按Pi物理脚号接线，先断电核对。所有自制工作限定低压侧、接头和机械结构。']];
wire.getRange('B5').values=[['红黑绿白线序仅为所列参考传感器示例；不同淘宝商品必须以自己的接线图为准。']];
wire.getRange('B4:B5').format.font={color:colors.muted};
wire.getRange('B7:G7').values=[['部分','起点／器件','终点／针脚','线材或固定件','动手工作','必须核对']];
wire.getRange(`B8:G${7+data.wiring.length}`).values=data.wiring.map(r=>[r.part,r.from,r.to,r.cable,r.work,r.note]);
const wt=wire.tables.add(`B7:G${7+data.wiring.length}`,true,'WiringAssembly');wt.style='TableStyleMedium2';header(wire,'B7:G7');
wire.getRange(`B8:G${7+data.wiring.length}`).format.wrapText=true;wire.getRange(`B8:G${7+data.wiring.length}`).format.rowHeight=46;wire.getRange(`B8:G${7+data.wiring.length}`).format.verticalAlignment='top';
wire.getRange(`B8:G${7+data.wiring.length}`).format.fill='#FFFFFF';for(let r=8;r<=7+data.wiring.length;r+=2)wire.getRange(`B${r}:G${r}`).format.fill=colors.grey;
wire.freezePanes.freezeRows(7);wire.freezePanes.freezeColumns(2);
data.wiring.forEach((r,i)=>note(wire,`B${8+i}`,`参考：${r.source}\n本表为Group 2拟议接线/装配，不表示已完成台架验证；以到货PCB丝印与厂家图核对。`));

const expectedLow=data.rows.reduce((s,r)=>s+r.qty*r.low,0),expectedHigh=data.rows.reduce((s,r)=>s+r.qty*r.high,0);
wb.recalculate();
const initial=bom.getRange('I4:J4').values;
const readNumbers=()=>bom.getRange('I4:J4').values[0];
function requirePair(pair,a,b,label){if(!pair.every(v=>typeof v==='number'&&Number.isFinite(v))||Math.abs(pair[0]-a)>0.001||Math.abs(pair[1]-b)>0.001)throw new Error(`${label}: ${JSON.stringify(pair)} != ${a},${b}`);}
requirePair(readNumbers(),expectedLow,expectedHigh,'initial totals');
const cameraRow=start+data.rows.findIndex(r=>r.id==='C01');
bom.getRange(`H${cameraRow}`).values=[[1800]];wb.recalculate();requirePair(readNumbers(),expectedLow-1650+1800,expectedHigh-2100+1800,'actual camera quote');
bom.getRange(`H${cameraRow}`).values=[[0]];wb.recalculate();requirePair(readNumbers(),expectedLow-1650,expectedHigh-2100,'zero quote preserved');
bom.getRange(`H${cameraRow}`).values=[[null]];
bom.getRange(`E${start}`).values=[[0]];wb.recalculate();requirePair(readNumbers(),expectedLow-1100,expectedHigh-1450,'owned Pi exclusion');
bom.getRange(`E${start}`).values=[[null]];wb.recalculate();if(readNumbers()[0]!=='待填数量')throw new Error('Blank quantity was silently omitted');
bom.getRange(`E${start}`).values=[[1]];
wb.recalculate();requirePair(readNumbers(),expectedLow,expectedHigh,'restored totals');
const inspect=await wb.inspect({kind:'table',range:'采购清单!B3:J14',include:'values,formulas',tableMaxRows:12,tableMaxCols:10,maxChars:6000});
await fs.writeFile(path.join(qa,'final-inspect.ndjson'),inspect.ndjson);
const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:100},summary:'final formula error scan',maxChars:3000});
await fs.writeFile(path.join(qa,'formula-errors.ndjson'),errors.ndjson);
const checks={items:data.rows.length,cameras:data.cameras.length,wiringRows:data.wiring.length,expectedLow,expectedHigh,initial,final:readNumbers(),inputTests:['actual quote','zero quote','exclude owned item','blank quantity','restore inputs'],formulaScan:errors.ndjson};
await fs.writeFile(path.join(qa,'workbook-checks.json'),JSON.stringify(checks,null,2));
const views=[['采购清单','B1:J22','bom-top'],['采购清单','B23:J42','bom-middle'],['采购清单',`B43:J${end}`,'bom-bottom'],['采购清单','K10:M27','bom-instructions-1'],['采购清单','K28:M45','bom-instructions-2'],['采购清单',`K46:M${end}`,'bom-instructions-3'],['相机对比','B1:G16','camera-main'],['相机对比','H8:K13','camera-details'],['接线与装配','B1:G15','wiring-1'],['接线与装配',`B16:G${7+data.wiring.length}`,'wiring-2']];
const renderViews=process.argv.includes('--bom-only')?views.filter(v=>['bom-top','bom-middle','bom-bottom'].includes(v[2])):process.argv.includes('--camera-only')?views.filter(v=>v[2].startsWith('camera-')):views;
for(const [sheetName,range,name]of renderViews){const pic=await wb.render({sheetName,range,scale:1.25,format:'png'});await fs.writeFile(path.join(qa,`${name}.png`),new Uint8Array(await pic.arrayBuffer()));}
const output=await SpreadsheetFile.exportXlsx(wb);const outputPath=path.join(outDir,'Group 2_Hardware Procurement_20260915.xlsx');await output.save(outputPath);
console.log(JSON.stringify({outputPath,items:data.rows.length,budget:[expectedLow,expectedHigh],previews:views.length,formulaScan:errors.ndjson}));
