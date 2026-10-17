#!/usr/bin/env python3
"""Read-only Magicka 2 provisional geometry preview: OBJ + JSON, no game changes."""
import argparse,datetime,json,pathlib,struct,uuid,math
IDS=("91e92dee4343fc7d","bd494ea7299b6750")
RECORDS=(1407033,4918276)
def export(blob,at,path,limit):
 size=struct.unpack_from("<I",blob,at+48)[0];vstart=at+52;tail=vstart+size
 count,stride=struct.unpack_from("<II",blob,tail+8)
 if stride!=88 or count*stride!=size:raise ValueError("Vertex framing invalid")
 vertices=[struct.unpack_from("<3f",blob,vstart+i*stride) for i in range(count)]
 if not all(all(math.isfinite(x) for x in v) for v in vertices):raise ValueError("Non-finite position")
 # Explicitly provisional: known 165-byte prefix is not a validated index section header.
 index_start=tail+165
 available=(len(blob)-index_start)//2
 num=min(limit,available);num-=num%3
 indices=struct.unpack_from("<"+str(num)+"H",blob,index_start)
 faces=[]
 for i in range(0,len(indices),3):
  tri=indices[i:i+3]
  if max(tri)>=count:break
  if len(set(tri))!=3:continue
  a,b,c=(vertices[j] for j in tri)
  ab=[b[k]-a[k] for k in range(3)];ac=[c[k]-a[k] for k in range(3)]
  cross=(ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0])
  if sum(x*x for x in cross)<1e-18:continue
  faces.append(tuple(j+1 for j in tri))
 with path.open("w",encoding="utf-8") as f:
  f.write("# SMELTER provisional Magicka2 geometry, NOT a verified complete mesh\n")
  for v in vertices:f.write("v %.9g %.9g %.9g\n"%v)
  f.write("o magicka2_provisional\n")
  for face in faces:f.write("f %d %d %d\n"%face)
 return {"vertex_count":count,"faces_written":len(faces),"indices_examined":num,"index_start":index_start,"obj":str(path),"index_section_verified":False,"geometry_verified":False}
def main():
 p=argparse.ArgumentParser();p.add_argument("--root",default=r"C:\SMELTER");p.add_argument("--max-indices",type=int,default=120);a=p.parse_args()
 if not 3<=a.max_indices<=120:p.error("--max-indices must be 3..120; deliberately bounded to verified sample region")
 root=pathlib.Path(a.root);base=root/"workspace"/"magicka2-reconstructed"
 dirs=sorted((d for d in base.iterdir() if d.is_dir() and all((d/(n+".decoded.bin")).is_file() for n in IDS)),reverse=True)
 if not dirs:p.error("Reconstructed resources missing")
 out=root/"workspace"/"magicka2-geometry-preview"/(datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S-")+uuid.uuid4().hex[:6]);out.mkdir(parents=True)
 report={"tool":"SMELTER Magicka2 provisional OBJ v1","read_only_source":True,"game_files_modified":False,"complete_mesh":False,"resources":[]}
 for name,at in zip(IDS,RECORDS):
  obj=out/(name+"-provisional.obj")
  report["resources"].append({"name":name,**export((dirs[0]/(name+".decoded.bin")).read_bytes(),at,obj,a.max_indices)})
 dest=out/"magicka2-geometry-preview.json";dest.write_text(json.dumps(report,indent=2),encoding="utf-8")
 print("Preview folder:",out)
 print("Report:",dest)
 for r in report["resources"]:print(r["name"],"faces:",r["faces_written"],"OBJ:",r["obj"])
 print("IMPORTANT: Partial, provisional geometry only. Not Skyrim-ready.")
if __name__=="__main__":main()
