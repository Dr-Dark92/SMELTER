#!/usr/bin/env python3
"""Read-only Magicka 2 zlib reconnaissance. Does not export copyrighted assets."""
import argparse, hashlib, json, pathlib, struct, zlib, datetime, uuid, sys

def decode_bounded(data, cap):
    obj=zlib.decompressobj(wbits=zlib.MAX_WBITS)
    out=bytearray()
    pos=16
    while pos<len(data) and not obj.eof:
        block=data[pos:pos+32768]
        pos+=len(block)
        remaining=cap-len(out)
        if remaining<=0: raise ValueError("decoded data exceeds cap")
        part=obj.decompress(block, remaining+1)
        out.extend(part)
        if len(out)>cap: raise ValueError("decoded data exceeds cap")
        while obj.unconsumed_tail:
            remaining=cap-len(out)
            if remaining<=0: raise ValueError("decoded data exceeds cap")
            part=obj.decompress(obj.unconsumed_tail,remaining+1)
            out.extend(part)
            if len(out)>cap: raise ValueError("decoded data exceeds cap")
    if not obj.eof: raise ValueError("zlib end-of-stream not found within input")
    return bytes(out), len(obj.unused_data), pos

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--game",default=r"D:\Games\Magicka 2")
    p.add_argument("--root",default=r"C:\SMELTER")
    p.add_argument("--max-output-mib",type=int,default=16)
    a=p.parse_args()
    if not 1<=a.max_output_mib<=64: p.error("max output must be 1..64 MiB")
    data=pathlib.Path(a.game)/"data"
    if not data.is_dir(): p.error(f"Game data not found: {data}")
    folder=pathlib.Path(a.root)/"workspace"/"magicka2-zlib"/(datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S-")+uuid.uuid4().hex[:8])
    folder.mkdir(parents=True,exist_ok=False)
    report={"source":str(data),"read_only_source":True,"game_modified":False,"status":"failed","sample":None,"error":None,"interpretation":"header fields at offsets 4,8,12 are recorded but not presumed to be decoded length"}
    try:
        candidates=sorted((f for f in data.iterdir() if f.is_file() and len(f.name)==16 and all(c in "0123456789abcdef" for c in f.name.lower()) and 22<=f.stat().st_size<=4*1024*1024),key=lambda f:f.stat().st_size)
        found=False
        for f in candidates:
            with f.open("rb") as h: header=h.read(18)
            if header[:4]!=bytes.fromhex("040000f0") or header[16:18] not in (b"\x78\x9c",b"\x78\x01",b"\x78\xda"): continue
            found=True
            raw=f.read_bytes()
            fields=[struct.unpack_from("<I",raw,offset)[0] for offset in (4,8,12)]
            sample={"file":f.name,"input_bytes":len(raw),"wrapper_header16_hex":raw[:16].hex(),"wrapper_fields_u32_le":fields,"zlib_header_hex":raw[16:18].hex()}
            try:
                decoded, unused, consumed=decode_bounded(raw,a.max_output_mib*1024*1024)
                sample.update({"decoded_bytes":len(decoded),"decoded_sha256":hashlib.sha256(decoded).hexdigest(),"first96_hex":decoded[:96].hex(),"first96_ascii":"".join(chr(c) if 32<=c<=126 else "." for c in decoded[:96]),"zlib_integrity":"verified","trailing_bytes_within_last_chunk":unused,"input_bytes_read":consumed})
                report["status"]="passed";report["sample"]=sample
                break
            except (zlib.error,ValueError) as e:
                sample["error"]=str(e)
                report["sample"]=sample
                continue
        if not found: raise ValueError("No zlib-wrapped candidate found")
        if report["status"]!="passed": raise ValueError("No candidate decoded successfully within the configured limit")
    except Exception as e: report["error"]=str(e)
    path=folder/"magicka2-zlib-python-result.json"
    path.write_text(json.dumps(report,indent=2),encoding="utf-8")
    print("Status:",report["status"])
    print("Report:",path)
    if report["sample"]: print("Sample:",report["sample"]["file"])
    if report["error"]: print("Error:",report["error"])
    return 0 if report["status"]=="passed" else 2

if __name__=="__main__": sys.exit(main())
