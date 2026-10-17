#!/usr/bin/env python3
"""Export Magicka 2 embedded DDS using verified 40-byte record lengths."""
import argparse,datetime,hashlib,json,pathlib,struct,uuid
NAMES=("91e92dee4343fc7d","bd494ea7299b6750")
def main():
 p=argparse.ArgumentParser();p.add_argument("--root",default=r"C:\SMELTER");a=p.parse_args()
 base=pathlib.Path(a.root)/"workspace"/"magicka2-reconstructed"
 folders=sorted((d for d in base.iterdir() if d.is_dir() and all((d/(n+".decoded.bin")).is_file() for n in NAMES)),reverse=True)
 if not folders:p.error("Reconstructed binaries not found")
 src=folders[0];out=pathlib.Path(a.root)/"workspace"/"magicka2-dds-corrected"/(datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S-")+uuid.uuid4().hex[:8]);out.mkdir(parents=True)
 report={"source":str(src),"source_read_only":True,"files":[]}
 for name in NAMES:
  raw=(src/(name+".decoded.bin")).read_bytes()
  offsets=[];pos=0
  while True:
   pos=raw.find(b"DDS ",pos)
   if pos<0:break
   offsets.append(pos);pos+=4
  for index,at in enumerate(offsets):
   rec={"source":name,"offset":at,"status":"rejected"}
   try:
    if at<40 or at+128>len(raw):raise ValueError("Invalid header location")
    if struct.unpack_from("<I",raw,at+4)[0]!=124:raise ValueError("Invalid DDS header")
    length=struct.unpack_from("<I",raw,at-8)[0]-4
    if length<128 or length>128*1024*1024 or at+length>len(raw):raise ValueError("Invalid record length")
    if index+1<len(offsets) and at+length!=offsets[index+1]-40:raise ValueError("Record boundary mismatch")
    width,height=struct.unpack_from("<II",raw,at+16)[0],struct.unpack_from("<I",raw,at+12)[0]
    if not 1<=width<=16384 or not 1<=height<=16384:raise ValueError("Invalid dimensions")
    blob=raw[at:at+length];dest=out/(name+"_"+str(at)+".dds");dest.write_bytes(blob)
    rec.update(status="exported",length=length,width=width,height=height,sha256=hashlib.sha256(blob).hexdigest(),path=str(dest),fourcc=raw[at+84:at+88].hex())
   except Exception as e:rec["reason"]=str(e)
   report["files"].append(rec)
 path=out/"magicka2-dds-corrected.json";path.write_text(json.dumps(report,indent=2),encoding="utf-8")
 print("Report:",path)
 print("Exported:",sum(r["status"]=="exported" for r in report["files"]),"of",len(report["files"]))
if __name__=="__main__":main()
