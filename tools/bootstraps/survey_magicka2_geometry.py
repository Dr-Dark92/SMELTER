#!/usr/bin/env python3
"""Read-only structural survey of Magicka 2 reconstructed robe resources."""
import argparse,collections,datetime,json,math,pathlib,re,struct,uuid
NAMES=("91e92dee4343fc7d","bd494ea7299b6750")
TOKENS=("rp_robe_wizard","g_body","Hips","Spine","Head","Hood1","Hood2","Hood3","LeftHandCloth","RightHandCloth")
def main():
 p=argparse.ArgumentParser();p.add_argument("--root",default=r"C:\SMELTER");a=p.parse_args()
 base=pathlib.Path(a.root)/"workspace"/"magicka2-reconstructed"
 dirs=sorted((x for x in base.iterdir() if x.is_dir() and all((x/(n+".decoded.bin")).is_file() for n in NAMES)),reverse=True)
 if not dirs:p.error("Missing reconstructed resource pair")
 src=dirs[0];out=pathlib.Path(a.root)/"workspace"/"magicka2-geometry-survey"/(datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S-")+uuid.uuid4().hex[:8]);out.mkdir(parents=True)
 result={"source":str(src),"read_only":True,"notes":"Candidate regions only. No vertex format or mesh verified.","resources":[]}
 for name in NAMES:
  data=(src/(name+".decoded.bin")).read_bytes()
  refs={t:[m.start() for m in re.finditer(re.escape(t.encode()),data)][:100] for t in TOKENS}
  dds=[];start=0
  while True:
   at=data.find(b"DDS ",start)
   if at<0:break
   start=at+4
   if at>=40:
    length=struct.unpack_from("<I",data,at-8)[0]-4
    if 128<=length<=len(data)-at:dds.append((at-40,at+length))
  regions=[];cursor=0
  for left,right in dds:
   if left>cursor:regions.append((cursor,left))
   cursor=max(cursor,right)
  if cursor<len(data):regions.append((cursor,len(data)))
  candidates=[]
  for left,right in regions:
   if right-left<256:continue
   chunks=[]
   for pos in range(left,right-255,256):
    block=data[pos:pos+256]
    zeros=block.count(0)
    if zeros>240:continue
    values=struct.unpack("<64f",block)
    finite=sum(math.isfinite(v) for v in values)
    plausible=sum(math.isfinite(v) and abs(v)<=10000 for v in values)
    near=sum(math.isfinite(v) and abs(v)<=10 for v in values)
    u16=struct.unpack("<128H",block)
    chunks.append({"offset":pos,"zero_bytes":zeros,"finite_f32":finite,"plausible_f32":plausible,"near10_f32":near,"u16_max":max(u16),"u16_unique":len(set(u16))})
   candidates.append({"start":left,"end":right,"length":right-left,"sampled_windows":len(chunks),"float_candidate_windows":[x for x in chunks if x["finite_f32"]==64 and x["plausible_f32"]>=60 and x["near10_f32"]>=40][:12],"index_candidate_windows":[x for x in chunks if x["u16_max"]<20000 and x["u16_unique"]>40][:12],"first128_hex":data[left:left+128].hex()})
  contexts=[]
  for pos in refs["rp_robe_wizard"][:10]:
   contexts.append({"offset":pos,"before96_hex":data[max(0,pos-96):pos].hex(),"after1024_hex":data[pos:pos+1024].hex()})
  result["resources"].append({"file":name,"size":len(data),"first_u32":struct.unpack_from("<I",data)[0],"strings":refs,"non_texture_regions":candidates,"robe_context":contexts})
 dest=out/"magicka2-geometry-survey.json";dest.write_text(json.dumps(result,indent=2),encoding="utf-8")
 print("Report:",dest)
 for r in result["resources"]:print(r["file"],"regions:",len(r["non_texture_regions"]),"robe:",len(r["strings"]["rp_robe_wizard"]))
if __name__=="__main__":main()
