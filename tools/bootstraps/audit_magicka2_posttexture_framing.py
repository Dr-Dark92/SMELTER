#!/usr/bin/env python3
"""Read-only framing audit for Magicka 2 post-texture records."""
import argparse,datetime,json,pathlib,struct,uuid
IDS=("91e92dee4343fc7d","bd494ea7299b6750")
OFFSETS=(1407033,4918276)
SIGNATURE=bytes.fromhex("98968b903f45a7e90b8da4e0")
def u32(buf,pos):
 return struct.unpack_from("<I",buf,pos)[0] if pos>=0 and pos+4<=len(buf) else None
def inspect(blob,at):
 size=u32(blob,at+32);nested=u32(blob,at+48)
 if size is None or nested is None:raise ValueError("Missing header")
 proposed=[{"label":"header_plus_stored_size","offset":at+40+size},{"label":"header_plus_size_minus_four","offset":at+36+size},{"label":"nested_buffer_end","offset":at+52+nested}]
 for entry in proposed:
  pos=entry["offset"]
  entry["within_file"]=0<=pos<=len(blob)
  entry["next_32_hex"]=blob[pos:pos+32].hex() if pos<=len(blob) else ""
  entry["signature_at_boundary"]=blob[pos:pos+12]==SIGNATURE
 matches=[];seek=at+40
 while len(matches)<100:
  hit=blob.find(SIGNATURE,seek)
  if hit<0:break
  matches.append({"offset":hit,"relative_to_start":hit-at,"size_field":u32(blob,hit+32),"first_payload_words":[u32(blob,hit+40+i*4) for i in range(4)]})
  seek=hit+12
 nested_end=at+52+nested
 return {"record_start":at,"file_length":len(blob),"stored_length":size,"nested_length":nested,"nested_end":nested_end,"bytes_after_nested":len(blob)-nested_end,"candidate_record_ends":proposed,"following_signature_records":matches,"post_nested_first_256_hex":blob[nested_end:nested_end+256].hex(),"post_nested_last_256_hex":blob[-256:].hex(),"caveat":"Signature occurrences and length fields are hypotheses until record boundaries are verified."}
def main():
 p=argparse.ArgumentParser();p.add_argument("--root",default=r"C:\SMELTER");a=p.parse_args()
 root=pathlib.Path(a.root);base=root/"workspace"/"magicka2-reconstructed"
 folders=sorted((d for d in base.iterdir() if d.is_dir() and all((d/(n+".decoded.bin")).is_file() for n in IDS)),reverse=True)
 if not folders:p.error("Missing reconstructed files")
 report={"read_only":True,"mesh_verified":False,"source":str(folders[0]),"resources":[]}
 for name,offset in zip(IDS,OFFSETS):
  blob=(folders[0]/(name+".decoded.bin")).read_bytes()
  report["resources"].append({"name":name,"framing":inspect(blob,offset)})
 out=root/"workspace"/"magicka2-framing-audit"/(datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S-")+uuid.uuid4().hex[:6]);out.mkdir(parents=True)
 path=out/"magicka2-posttexture-framing.json";path.write_text(json.dumps(report,indent=2),encoding="utf-8")
 print("Framing audit:",path)
 for r in report["resources"]:print(r["name"],"following signatures:",len(r["framing"]["following_signature_records"]))
if __name__=="__main__":main()
