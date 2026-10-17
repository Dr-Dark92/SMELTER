#!/usr/bin/env python3
"""Read-only Magicka2 index section length and framing discovery."""
import argparse,datetime,json,pathlib,struct,uuid,collections
IDS=("91e92dee4343fc7d","bd494ea7299b6750")
OFFSETS=(1407033,4918276)
def analyze(blob,at):
 size=struct.unpack_from("<I",blob,at+48)[0];tail=at+52+size
 count,stride=struct.unpack_from("<II",blob,tail+8)
 if stride!=88 or count*stride!=size:raise ValueError("Vertex record mismatch")
 # The +165 offset is a known sample start, not proven beginning of the index array.
 begin=tail+165;available=min(len(blob)-begin,65536)
 values=struct.unpack_from("<"+str(available//2)+"H",blob,begin)
 # Sliding 3-index triangle windows from known aligned start. Track first out-of-range,
 # while reporting that a run may cross submesh/metadata boundaries.
 first_invalid=next((i for i,v in enumerate(values) if v>=count),None)
 run=values[:first_invalid] if first_invalid is not None else values
 triangles=[run[i:i+3] for i in range(0,len(run)-2,3)]
 good=[t for t in triangles if len(set(t))==3]
 edges=collections.Counter(tuple(sorted((t[a],t[b]))) for t in good for a,b in ((0,1),(1,2),(2,0)))
 # Capture plausible section header bytes before the known index sample start.
 return {"vertex_count":count,"index_sample_absolute_start":begin,"bytes_between_tail_and_sample":165,
         "pre_sample_hex":blob[tail:begin].hex(),"first_128_indices":list(values[:128]),
         "first_out_of_range_index_position":first_invalid,
         "consecutive_in_range_values":len(run),"complete_triangles_in_run":len(triangles),
         "nondegenerate_triangles":len(good),"unique_indices_in_run":len(set(run)),
         "shared_edges":sum(n>1 for n in edges.values()),
         "first_out_of_range_values":list(values[first_invalid:first_invalid+16]) if first_invalid is not None else [],
         "last_24_in_range":list(run[-24:]),
         "caveat":"Consecutive in-range values do not prove one continuous index buffer; offsets may cross sections."}
def main():
 p=argparse.ArgumentParser();p.add_argument("--root",default=r"C:\SMELTER");a=p.parse_args()
 root=pathlib.Path(a.root);base=root/"workspace"/"magicka2-reconstructed"
 dirs=sorted((d for d in base.iterdir() if d.is_dir() and all((d/(n+".decoded.bin")).is_file() for n in IDS)),reverse=True)
 if not dirs:p.error("Reconstructed resources missing")
 report={"tool":"SMELTER Magicka2 index framing v1","read_only":True,"complete_mesh_verified":False,"source":str(dirs[0]),"resources":[]}
 for name,at in zip(IDS,OFFSETS):report["resources"].append({"name":name,"audit":analyze((dirs[0]/(name+".decoded.bin")).read_bytes(),at)})
 out=root/"workspace"/"magicka2-index-framing"/(datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S-")+uuid.uuid4().hex[:6]);out.mkdir(parents=True)
 dest=out/"magicka2-index-framing.json";dest.write_text(json.dumps(report,indent=2),encoding="utf-8")
 print("Index framing report:",dest)
 for r in report["resources"]:print(r["name"],"in-range:",r["audit"]["consecutive_in_range_values"],"first invalid:",r["audit"]["first_out_of_range_index_position"])
if __name__=="__main__":main()
