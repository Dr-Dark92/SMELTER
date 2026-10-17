#!/usr/bin/env python3
"""Read-only audit of Magicka 2 embedded DDS record framing and lengths."""
import argparse,datetime,json,pathlib,struct,uuid
NAMES=("91e92dee4343fc7d","bd494ea7299b6750")
def main():
 p=argparse.ArgumentParser();p.add_argument("--root",default=r"C:\SMELTER");a=p.parse_args()
 base=pathlib.Path(a.root)/"workspace"/"magicka2-reconstructed"
 folders=sorted((d for d in base.iterdir() if d.is_dir() and all((d/(n+".decoded.bin")).is_file() for n in NAMES)),reverse=True)
 if not folders:p.error("Reconstructed binaries missing")
 src=folders[0];out=pathlib.Path(a.root)/"workspace"/"magicka2-record-audit"/(datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S-")+uuid.uuid4().hex[:8]);out.mkdir(parents=True)
 report={"source":str(src),"read_only":True,"files":[]}
 for name in NAMES:
  data=(src/(name+".decoded.bin")).read_bytes();offsets=[];pos=0
  while True:
   pos=data.find(b"DDS ",pos)
   if pos<0:break
   offsets.append(pos);pos+=4
  records=[]
  for idx,at in enumerate(offsets):
   if at<40 or at+128>len(data):continue
   hdr=data[at-40:at];fields=struct.unpack("<10I",hdr)
   length=fields[8];end=at+length-4
   nxt=offsets[idx+1] if idx+1<len(offsets) else None
   width=struct.unpack_from("<I",data,at+16)[0];height=struct.unpack_from("<I",data,at+12)[0]
   mip=struct.unpack_from("<I",data,at+28)[0]
   depth=struct.unpack_from("<I",data,at+24)[0]
   caps2=struct.unpack_from("<I",data,at+112)[0]
   fmt=data[at+84:at+88].hex()
   rec={"dds_offset":at,"metadata_offset":at-40,"metadata_u32":list(fields),"stored_length":length,"dds_length_from_metadata":length-4,"calculated_end":end,"within_resource":end<=len(data),"next_dds_offset":nxt,"next_metadata_offset":nxt-40 if nxt is not None else None,"distance_to_next_metadata":(nxt-40-end) if nxt is not None else None,"width":width,"height":height,"mips":mip,"depth":depth,"caps2":caps2,"fourcc_hex":fmt,"dds_header128_hex":data[at:at+128].hex()}
   if end<=len(data):rec["post_payload32_hex"]=data[end:end+32].hex()
   records.append(rec)
  report["files"].append({"name":name,"records":records})
 path=out/"magicka2-texture-record-audit.json";path.write_text(json.dumps(report,indent=2),encoding="utf-8")
 print("Report:",path)
 for f in report["files"]:
  print(f["name"],"records:",len(f["records"]),"gaps:",[r["distance_to_next_metadata"] for r in f["records"] if r["distance_to_next_metadata"] is not None])
if __name__=="__main__":main()
