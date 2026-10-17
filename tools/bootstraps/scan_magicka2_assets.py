#!/usr/bin/env python3
"""Bounded, read-only Magicka 2 zlib asset classification."""
import argparse, datetime, hashlib, json, pathlib, re, sys, uuid, zlib
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--game",default=r"D:\Games\Magicka 2")
 p.add_argument("--root",default=r"C:\SMELTER")
 p.add_argument("--max-files",type=int,default=126)
 p.add_argument("--max-input-mib",type=int,default=8)
 p.add_argument("--max-output-mib",type=int,default=32)
 a=p.parse_args()
 if not 1<=a.max_files<=256 or not 1<=a.max_input_mib<=64 or not 1<=a.max_output_mib<=128:p.error("invalid limits")
 data=pathlib.Path(a.game)/"data"
 if not data.is_dir():p.error(f"Missing: {data}")
 out=pathlib.Path(a.root)/"workspace"/"magicka2-assets"/(datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S-")+uuid.uuid4().hex[:8])
 out.mkdir(parents=True,exist_ok=False)
 records=[]
 patterns=re.compile(rb"[\x20-\x7e]{5,}")
 keywords=re.compile(r"wizard|robe|hood|outfit|character|mesh|material|texture|skeleton|player|costume|hat|cloth|skin",re.I)
 signatures=[(b"DDS ","DDS"),(b"\x89PNG\r\n\x1a\n","PNG"),(b"OggS","Ogg"),(b"RIFF","RIFF"),(b"glTF","glTF"),(b"FSB5","FSB5"),(b"<?xml","XML"),(b"{","JSON-like"),(b"PK\x03\x04","ZIP")]
 files=sorted((f for f in data.iterdir() if f.is_file() and re.fullmatch(r"[0-9a-fA-F]{16}",f.name)),key=lambda x:x.name)[:a.max_files]
 for f in files:
  rec={"file":f.name,"input_bytes":f.stat().st_size,"status":"skipped"}
  try:
   if f.stat().st_size>a.max_input_mib*1024*1024:rec["reason"]="input_limit";records.append(rec);continue
   raw=f.read_bytes()
   if len(raw)<22 or raw[:4]!=bytes.fromhex("040000f0") or raw[16:18] not in (b"\x78\x9c",b"\x78\x01",b"\x78\xda"):
    rec["reason"]="unknown_wrapper";records.append(rec);continue
   d=zlib.decompressobj()
   decoded=d.decompress(raw[16:],a.max_output_mib*1024*1024+1)
   if len(decoded)>a.max_output_mib*1024*1024:raise ValueError("output_limit")
   if not d.eof:raise ValueError("incomplete zlib stream or output limit")
   decoded+=d.flush()
   if len(decoded)>a.max_output_mib*1024*1024:raise ValueError("output_limit")
   texts=[m.group().decode("ascii") for m in patterns.finditer(decoded) if len(m.group())<=300]
   hits=[t for t in texts if keywords.search(t)][:30]
   found=[{"format":label,"offset":decoded.find(magic)} for magic,label in signatures if decoded.find(magic)>=0]
   rec.update(status="decoded",decoded_bytes=len(decoded),sha256=hashlib.sha256(decoded).hexdigest(),header32_hex=decoded[:32].hex(),header32_ascii="".join(chr(b) if 32<=b<=126 else "." for b in decoded[:32]),keyword_hits=hits,signatures=found,printable_strings_sample=texts[:12])
  except Exception as e:rec.update(status="failed",error=str(e))
  records.append(rec)
 report={"source":str(data),"read_only_source":True,"game_modified":False,"limits":{"max_files":a.max_files,"max_input_mib":a.max_input_mib,"max_output_mib":a.max_output_mib},"counts":{k:sum(r["status"]==k for r in records) for k in ("decoded","skipped","failed")},"files":records,"note":"Decoded only in memory; no asset payloads exported. String and magic-byte matches are clues, not proof of format."}
 path=out/"magicka2-assets.json"
 path.write_text(json.dumps(report,indent=2),encoding="utf-8")
 print("Counts:",report["counts"]);print("Report:",path)
 return 0
if __name__=="__main__":sys.exit(main())
