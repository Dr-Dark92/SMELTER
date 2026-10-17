#!/usr/bin/env python3
"""Inspect 40-byte DDS separators and adjacent Magicka 2 binary records."""
import argparse,datetime,json,pathlib,struct,uuid
NAMES=("91e92dee4343fc7d","bd494ea7299b6750")
def main():
 p=argparse.ArgumentParser();p.add_argument("--root",default=r"C:\SMELTER");a=p.parse_args()
 root=pathlib.Path(a.root)/"workspace"/"magicka2-reconstructed"
 folders=sorted((x for x in root.iterdir() if x.is_dir() and all((x/(n+".decoded.bin")).is_file() for n in NAMES)),reverse=True)
 if not folders:p.error("Missing reconstructed resources")
 folder=folders[0];dest=pathlib.Path(a.root)/"workspace"/"magicka2-records"/(datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S-")+uuid.uuid4().hex[:8]);dest.mkdir(parents=True,exist_ok=False)
 report={"source":str(folder),"read_only_source":True,"game_modified":False,"files":[]}
 for name in NAMES:
  data=(folder/(name+".decoded.bin")).read_bytes();offsets=[];at=0
  while True:
   at=data.find(b"DDS ",at)
   if at<0:break
   offsets.append(at);at+=4
  r={"file":name,"size":len(data),"dds_offsets":offsets,"records":[],"prefix":data[:256].hex()}
  for j,at in enumerate(offsets):
   height,width=struct.unpack_from("<II",data,at+12)
   mips=struct.unpack_from("<I",data,at+28)[0] or 1
   fourcc=data[at+84:at+88]
   pf_flags=struct.unpack_from("<I",data,at+80)[0]
   rgb_bits=struct.unpack_from("<I",data,at+88)[0]
   if pf_flags&4 and fourcc in (b"DXT1",b"DXT3",b"DXT5"):
    block=8 if fourcc==b"DXT1" else 16
    payload=sum(max(1,(max(1,width>>m)+3)//4)*max(1,(max(1,height>>m)+3)//4)*block for m in range(mips))
   elif pf_flags&0x40 and rgb_bits in (8,16,24,32):
    payload=sum(max(1,width>>m)*max(1,height>>m)*(rgb_bits//8) for m in range(mips))
   else:payload=None
   end=at+128+payload if payload is not None else None
   nxt=offsets[j+1] if j+1<len(offsets) else None
   r["records"].append({"offset":at,"width":width,"height":height,"mips":mips,"format":fourcc.hex(),"pixel_flags":pf_flags,"rgb_bits":rgb_bits,"expected_end":end,"next_dds":nxt,"gap":nxt-end if nxt is not None and end is not None else None,"preceding64_hex":data[max(0,at-64):at].hex(),"following64_hex":data[end:end+64].hex() if end is not None and end<len(data) else None,"u32_preceding40":[struct.unpack_from("<I",data,k)[0] for k in range(at-40,at,4)] if at>=40 else []})
  report["files"].append(r)
 path=dest/"magicka2-record-layout.json";path.write_text(json.dumps(report,indent=2),encoding="utf-8")
 print("Report:",path)
 for r in report["files"]:print(r["file"],"DDS:",len(r["dds_offsets"]),"gaps:",[x["gap"] for x in r["records"] if x["gap"] is not None])
if __name__=="__main__":main()
