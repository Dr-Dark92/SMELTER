#!/usr/bin/env python3
"""Read-only, bounded inspection of two Magicka 2 wizard robe containers."""
import argparse,datetime,hashlib,json,pathlib,re,struct,sys,uuid,zlib
TARGETS=("91e92dee4343fc7d","bd494ea7299b6750")
TERMS=re.compile(rb"rp_robe_wizard|Hood[123]|LeftHandCloth|RightHandCloth|g_body|skirt|material|texture|mesh|skeleton",re.I)
def inspect(path,max_output):
 raw=path.read_bytes()
 rec={"file":path.name,"compressed_bytes":len(raw),"wrapper16":raw[:16].hex(),"wrapper_fields_le":[struct.unpack_from("<I",raw,i)[0] for i in (4,8,12)]}
 if raw[:4]!=bytes.fromhex("040000f0"):raise ValueError("Unexpected wrapper")
 obj=zlib.decompressobj()
 decoded=obj.decompress(raw[16:],max_output+1)
 if len(decoded)>max_output:raise ValueError("Decompressed output exceeds limit")
 if not obj.eof:raise ValueError("Zlib stream incomplete or output limit reached")
 decoded+=obj.flush()
 if len(decoded)>max_output:raise ValueError("Decompressed output exceeds limit")
 rec.update(decoded_bytes=len(decoded),sha256=hashlib.sha256(decoded).hexdigest(),first128_hex=decoded[:128].hex(),zlib_verified=True)
 matches=[]
 for m in TERMS.finditer(decoded):
  start=max(0,m.start()-48);end=min(len(decoded),m.end()+64)
  matches.append({"term":m.group().decode("ascii",errors="replace"),"offset":m.start(),"context_ascii":"".join(chr(c) if 32<=c<=126 else "." for c in decoded[start:end]),"context_hex":decoded[start:end].hex()})
  if len(matches)>=150:break
 rec["matches"]=matches
 rec["unique_terms"]=sorted(set(m["term"] for m in matches))
 rec["signatures"]=[{"format":name,"offset":decoded.find(sig)} for sig,name in ((b"DDS ","DDS"),(b"OggS","Ogg"),(b"BKM3v2","BKM3v2")) if decoded.find(sig)>=0]
 return rec
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--game",default=r"D:\Games\Magicka 2")
 p.add_argument("--root",default=r"C:\SMELTER")
 p.add_argument("--max-output-mib",type=int,default=32)
 a=p.parse_args()
 if not 1<=a.max_output_mib<=128:p.error("max-output-mib must be 1..128")
 folder=pathlib.Path(a.game)/"data"
 out=pathlib.Path(a.root)/"workspace"/"magicka2-robe"/(datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S-")+uuid.uuid4().hex[:8])
 out.mkdir(parents=True,exist_ok=False)
 report={"source":str(folder),"read_only_source":True,"game_modified":False,"targets":[],"note":"Keyword offsets and context are diagnostic; geometry is not yet proven or exported."}
 for name in TARGETS:
  try:report["targets"].append(inspect(folder/name,a.max_output_mib*1024*1024))
  except Exception as e:report["targets"].append({"file":name,"error":str(e)})
 dest=out/"magicka2-robe-structure.json"
 dest.write_text(json.dumps(report,indent=2),encoding="utf-8")
 print("Report:",dest)
 for item in report["targets"]:print(item["file"],"decoded_bytes:",item.get("decoded_bytes"),"matches:",len(item.get("matches",[])),"error:",item.get("error"))
 return 0 if all("error" not in item for item in report["targets"]) else 2
if __name__=="__main__":sys.exit(main())
