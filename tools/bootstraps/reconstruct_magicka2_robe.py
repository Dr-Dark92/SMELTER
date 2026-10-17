#!/usr/bin/env python3
"""Reconstruct two Magicka 2 resources into private workspace; never modify game data."""
import argparse,datetime,hashlib,json,pathlib,struct,uuid,zlib,re
TARGETS=("91e92dee4343fc7d","bd494ea7299b6750")
def main():
 p=argparse.ArgumentParser();p.add_argument("--game",default=r"D:\Games\Magicka 2");p.add_argument("--root",default=r"C:\SMELTER");a=p.parse_args()
 dest=pathlib.Path(a.root)/"workspace"/"magicka2-reconstructed"/(datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S-")+uuid.uuid4().hex[:8]);dest.mkdir(parents=True,exist_ok=False)
 report={"source":str(pathlib.Path(a.game)/"data"),"read_only_source":True,"game_modified":False,"outputs":[],"note":"Decoded resource binaries for local private inspection only; no redistribution."}
 for name in TARGETS:
  entry={"file":name,"status":"error"}
  try:
   raw=(pathlib.Path(a.game)/"data"/name).read_bytes()
   if raw[:4]!=bytes.fromhex("040000f0"):raise ValueError("Unknown container signature")
   declared=struct.unpack_from("<I",raw,4)[0]
   if declared<1 or declared>128*1024*1024:raise ValueError("Declared length out of range")
   offset=16;out=bytearray();blocks=0
   while offset<len(raw):
    if blocks>=4096:raise ValueError("Block limit reached")
    if blocks==0:count=struct.unpack_from("<I",raw,12)[0];payload=offset
    else:
     if offset+4>len(raw):raise ValueError("Truncated block prefix")
     count=struct.unpack_from("<I",raw,offset)[0];payload=offset+4
    if count<6 or count>len(raw)-payload:raise ValueError("Invalid block length")
    obj=zlib.decompressobj()
    decoded=obj.decompress(raw[payload:payload+count],65537)
    if not obj.eof or obj.unused_data or obj.unconsumed_tail or len(decoded)!=65536:raise ValueError("Unexpected block framing or size")
    out.extend(decoded);offset=payload+count;blocks+=1
    if len(out)>128*1024*1024:raise ValueError("Total output limit")
   if not (len(out)-65536<declared<=len(out)):raise ValueError("Declared length inconsistent with padded block output")
   padding=bytes(out[declared:])
   trimmed=bytes(out[:declared])
   binary=dest/(name+".decoded.bin")
   binary.write_bytes(trimmed)
   terms=["rp_robe_wizard","Hood1","Hood2","Hood3","LeftHandCloth","RightHandCloth"]
   entry.update(status="complete",declared_bytes=declared,padded_bytes=len(out),padding_bytes=len(padding),padding_zero_bytes=padding.count(0),padding_first64_hex=padding[:64].hex(),block_count=blocks,decoded_sha256=hashlib.sha256(trimmed).hexdigest(),output_path=str(binary),first128_hex=trimmed[:128].hex(),string_offsets={t:[m.start() for m in re.finditer(re.escape(t.encode()),trimmed)][:30] for t in terms})
  except Exception as e:entry["error"]=str(e)
  report["outputs"].append(entry)
 path=dest/"magicka2-reconstructed.json";path.write_text(json.dumps(report,indent=2),encoding="utf-8")
 print("Report:",path)
 for r in report["outputs"]:print(r["file"],r["status"],"bytes:",r.get("declared_bytes"),"padding:",r.get("padding_bytes"),"error:",r.get("error"))
if __name__=="__main__":main()
