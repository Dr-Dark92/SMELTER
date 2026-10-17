#!/usr/bin/env python3
"""Read-only inspection of Magicka 2 container block boundaries."""
import argparse,datetime,json,pathlib,struct,uuid,zlib
TARGETS=("91e92dee4343fc7d","bd494ea7299b6750")
def hexdump(b,origin):
 return [{"offset":origin+i,"hex":b[i:i+16].hex(),"ascii":"".join(chr(c) if 32<=c<=126 else "." for c in b[i:i+16])} for i in range(0,len(b),16)]
def main():
 p=argparse.ArgumentParser();p.add_argument("--game",default=r"D:\Games\Magicka 2");p.add_argument("--root",default=r"C:\SMELTER");a=p.parse_args()
 out=pathlib.Path(a.root)/"workspace"/"magicka2-boundaries"/(datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S-")+uuid.uuid4().hex[:8]);out.mkdir(parents=True,exist_ok=False)
 report={"read_only_source":True,"game_modified":False,"files":[],"note":"Only records bytes and plausible header positions; no automatic carving or unverified decompression."}
 for name in TARGETS:
  r={"file":name}
  try:
   raw=(pathlib.Path(a.game)/"data"/name).read_bytes()
   first_len=struct.unpack_from("<I",raw,12)[0]
   boundary=16+first_len
   r.update(file_size=len(raw),first_compressed_length=first_len,boundary_offset=boundary,header16_hex=raw[:16].hex(),boundary_before=hexdump(raw[max(0,boundary-64):boundary],max(0,boundary-64)),boundary_after=hexdump(raw[boundary:boundary+256],boundary))
   candidates=[]
   for i in range(boundary,min(len(raw)-2,boundary+4096)):
    cmf,flg=raw[i],raw[i+1]
    if cmf==0x78 and (cmf*256+flg)%31==0 and flg in (0x01,0x5e,0x9c,0xda):
     candidates.append({"offset":i,"relative_to_boundary":i-boundary,"header":raw[i:i+2].hex(),"previous16_hex":raw[max(0,i-16):i].hex()})
     if len(candidates)>=32:break
   r["nearby_zlib_candidates"]=candidates
   r["u32_le_at_boundary_offsets"]=[{"relative":i,"value":struct.unpack_from("<I",raw,boundary+i)[0]} for i in range(0,min(64,len(raw)-boundary-3),4)]
  except Exception as e:r["error"]=str(e)
  report["files"].append(r)
 dest=out/"magicka2-boundaries.json";dest.write_text(json.dumps(report,indent=2),encoding="utf-8")
 print("Report:",dest)
 for f in report["files"]:print(f["file"],"boundary:",f.get("boundary_offset"),"candidate zlib headers:",len(f.get("nearby_zlib_candidates",[])),"error:",f.get("error"))
if __name__=="__main__":main()
