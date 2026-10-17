#!/usr/bin/env python3
"""Focused, read-only Magicka 2 geometry framing investigation."""
import argparse,datetime,json,pathlib,struct,uuid,math
NAMES=("91e92dee4343fc7d","bd494ea7299b6750")
def ints(data,start,length):
 b=data[start:start+length];return [struct.unpack_from("<I",b,i)[0] for i in range(0,len(b)-3,4)]
def examine(data,start,end):
 result=[]
 for offset in range(start,min(end-127,len(data)-127),128):
  block=data[offset:offset+128]
  u16=struct.unpack("<64H",block)
  f32=struct.unpack("<32f",block)
  finite=sum(math.isfinite(v) for v in f32)
  plausible=sum(math.isfinite(v) and abs(v)<100 for v in f32)
  result.append({"offset":offset,"zero_bytes":block.count(0),"u16_min":min(u16),"u16_max":max(u16),"u16_unique":len(set(u16)),"u16_under_2048":sum(v<2048 for v in u16),"finite_f32":finite,"plausible_f32":plausible})
 return result
def main():
 p=argparse.ArgumentParser();p.add_argument("--root",default=r"C:\SMELTER");a=p.parse_args()
 base=pathlib.Path(a.root)/"workspace"/"magicka2-reconstructed"
 dirs=sorted((d for d in base.iterdir() if d.is_dir() and all((d/(n+".decoded.bin")).is_file() for n in NAMES)),reverse=True)
 if not dirs:p.error("Reconstructed binary pair missing")
 src=dirs[0];out=pathlib.Path(a.root)/"workspace"/"magicka2-geometry-framing"/(datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S-")+uuid.uuid4().hex[:8]);out.mkdir(parents=True)
 report={"source":str(src),"read_only":True,"interpretation":"Exploratory only; no mesh format confirmed","resources":[]}
 for name in NAMES:
  data=(src/(name+".decoded.bin")).read_bytes()
  robe=[];pos=0
  while True:
   pos=data.find(b"rp_robe_wizard",pos)
   if pos<0:break
   end=data.find(b"RightAttach\x00",pos)
   if end<0 or end-pos>2048:end=pos+512
   else:end+=len(b"RightAttach\x00")
   robe.append({"name_offset":pos,"names_end":end,"following_128_u32":ints(data,end,128),"following_256_hex":data[end:end+256].hex(),"following_4096_window_stats":examine(data,end,min(end+4096,len(data)))})
   pos+=len(b"rp_robe_wizard")
  dds=[];pos=0
  while True:
   pos=data.find(b"DDS ",pos)
   if pos<0:break
   if pos>=40 and pos+128<=len(data):
    length=struct.unpack_from("<I",data,pos-8)[0]-4
    if 128<=length<=len(data)-pos:dds.append((pos-40,pos+length))
   pos+=4
  tail=dds[-1][1] if dds else 0
  tail_starts=[tail,tail+4096,tail+16384,max(tail,len(data)-65536)]
  tail_samples=[]
  for at in tail_starts:
   if at>=len(data):continue
   tail_samples.append({"offset":at,"header_u32":ints(data,at,128),"header128_hex":data[at:at+128].hex(),"windows":examine(data,at,min(at+8192,len(data)))})
  report["resources"].append({"file":name,"size":len(data),"robe_records":robe,"dds_count":len(dds),"post_texture_start":tail,"tail_samples":tail_samples})
 target=out/"magicka2-geometry-framing.json";target.write_text(json.dumps(report,indent=2),encoding="utf-8")
 print("Report:",target)
 for r in report["resources"]:print(r["file"],"robe records:",len(r["robe_records"]),"post-texture:",r["post_texture_start"])
if __name__=="__main__":main()
