#!/usr/bin/env python3
"""Bounded read-only decoder for Magicka 2 length-prefixed zlib blocks."""
import argparse,datetime,hashlib,json,pathlib,struct,uuid,zlib
TARGETS=("91e92dee4343fc7d","bd494ea7299b6750")
def decode(raw,offset,length,cap):
 if length<6 or offset+length>len(raw):raise ValueError("Invalid compressed block length")
 obj=zlib.decompressobj()
 out=obj.decompress(raw[offset:offset+length],cap+1)
 if len(out)>cap:raise ValueError("Block output limit exceeded")
 if not obj.eof or obj.unused_data or obj.unconsumed_tail:raise ValueError("Block is not exactly one complete zlib stream")
 out+=obj.flush()
 if len(out)>cap:raise ValueError("Block output limit exceeded")
 return out
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--game",default=r"D:\Games\Magicka 2");p.add_argument("--root",default=r"C:\SMELTER")
 p.add_argument("--max-blocks",type=int,default=512);p.add_argument("--max-block-output-mib",type=int,default=2);p.add_argument("--max-total-output-mib",type=int,default=128)
 a=p.parse_args()
 if not 1<=a.max_blocks<=4096 or not 1<=a.max_block_output_mib<=32 or not 1<=a.max_total_output_mib<=1024:p.error("Invalid limits")
 folder=pathlib.Path(a.root)/"workspace"/"magicka2-chain"/(datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S-")+uuid.uuid4().hex[:8]);folder.mkdir(parents=True,exist_ok=False)
 report={"source":str(pathlib.Path(a.game)/"data"),"read_only_source":True,"game_modified":False,"targets":[],"note":"Block decoding only; no payload files exported. Length prefix interpretation is tested against full zlib integrity."}
 for name in TARGETS:
  r={"file":name,"blocks":[],"status":"incomplete"}
  try:
   raw=(pathlib.Path(a.game)/"data"/name).read_bytes()
   if len(raw)<20 or raw[:4]!=bytes.fromhex("040000f0"):raise ValueError("Unexpected container header")
   r["input_bytes"]=len(raw);r["header_fields_le"]=[struct.unpack_from("<I",raw,i)[0] for i in (4,8,12)]
   offset=16;total=0;dig=hashlib.sha256()
   for i in range(a.max_blocks):
    if offset==len(raw):r["status"]="complete";break
    if i==0:length=struct.unpack_from("<I",raw,12)[0];payload=offset;prefix_offset=12
    else:
     if offset+4>len(raw):raise ValueError(f"Truncated length prefix at {offset}")
     length=struct.unpack_from("<I",raw,offset)[0];prefix_offset=offset;payload=offset+4
    if length>len(raw)-payload:raise ValueError(f"Block {i}: compressed length {length} exceeds remaining input")
    chunk=decode(raw,payload,length,a.max_block_output_mib*1024*1024)
    total+=len(chunk)
    if total>a.max_total_output_mib*1024*1024:raise ValueError("Total output limit exceeded")
    dig.update(chunk)
    r["blocks"].append({"index":i,"prefix_offset":prefix_offset,"payload_offset":payload,"compressed_bytes":length,"decoded_bytes":len(chunk),"decoded_sha256":hashlib.sha256(chunk).hexdigest(),"robe_mentions":chunk.count(b"rp_robe_wizard"),"first16_hex":chunk[:16].hex()})
    offset=payload+length
   else:
    if offset==len(raw):r["status"]="complete"
   r.update(decoded_bytes=total,decoded_sha256=dig.hexdigest(),consumed_bytes=offset,remaining_bytes=len(raw)-offset,block_count=len(r["blocks"]))
  except Exception as e:r.update(status="error",error=str(e))
  report["targets"].append(r)
 dest=folder/"magicka2-block-chain.json";dest.write_text(json.dumps(report,indent=2),encoding="utf-8")
 print("Report:",dest)
 for r in report["targets"]:print(r["file"],r["status"],"blocks:",r.get("block_count",len(r["blocks"])),"decoded:",r.get("decoded_bytes"),"error:",r.get("error"))
if __name__=="__main__":main()
