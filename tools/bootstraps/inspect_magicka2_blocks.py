#!/usr/bin/env python3
"""Inspect Magicka 2 wizard robe zlib blocks and surrounding records, read-only."""
import argparse,datetime,json,pathlib,struct,uuid,zlib,hashlib
TARGETS=("91e92dee4343fc7d","bd494ea7299b6750")
def main():
 p=argparse.ArgumentParser();p.add_argument("--game",default=r"D:\Games\Magicka 2");p.add_argument("--root",default=r"C:\SMELTER");p.add_argument("--max-blocks",type=int,default=128);a=p.parse_args()
 if not 1<=a.max_blocks<=512:p.error("max-blocks out of range")
 out=pathlib.Path(a.root)/"workspace"/"magicka2-blocks"/(datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S-")+uuid.uuid4().hex[:8]);out.mkdir(parents=True)
 report={"read_only_source":True,"game_modified":False,"files":[],"note":"Block layout hypotheses only; no asset geometry exported."}
 for name in TARGETS:
  path=pathlib.Path(a.game)/"data"/name
  record={"file":name,"blocks":[]}
  try:
   raw=path.read_bytes();record["size"]=len(raw);record["header16"]=raw[:16].hex()
   if raw[:4]!=bytes.fromhex("040000f0"):raise ValueError("Unexpected wrapper")
   # The first zlib stream begins at byte 16. Identify consecutive streams, if any.
   offset=16
   for i in range(a.max_blocks):
    if offset>=len(raw):break
    obj=zlib.decompressobj();piece=obj.decompress(raw[offset:],65537)
    if not obj.eof:
     record["stopped_reason"]="Next block not complete within 65536-byte output cap or not zlib";break
    consumed=len(raw[offset:])-len(obj.unused_data)
    if consumed<=0:break
    item={"index":i,"input_offset":offset,"compressed_bytes":consumed,"decoded_bytes":len(piece),"decoded_sha256":hashlib.sha256(piece).hexdigest(),"header32_hex":piece[:32].hex(),"robe_reference_count":piece.count(b"rp_robe_wizard"),"robe_reference_offsets":[m for m in range(len(piece)) if piece.startswith(b"rp_robe_wizard",m)][:16]}
    record["blocks"].append(item);offset+=consumed
   record["next_offset"]=offset;record["remaining_bytes"]=len(raw)-offset;record["remaining_prefix_hex"]=raw[offset:offset+64].hex()
  except Exception as e:record["error"]=str(e)
  report["files"].append(record)
 dest=out/"magicka2-block-layout.json";dest.write_text(json.dumps(report,indent=2),encoding="utf-8")
 print("Report:",dest)
 for f in report["files"]:print(f["file"],"blocks:",len(f["blocks"]),"remaining:",f.get("remaining_bytes"),"error:",f.get("error"))
if __name__=="__main__":main()
