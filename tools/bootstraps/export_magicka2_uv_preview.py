#!/usr/bin/env python3
"""SMELTER: read-only UV-enabled Magicka2 OBJ export and checker UV atlas."""
import argparse,datetime,json,math,pathlib,struct,uuid
RES=(("91e92dee4343fc7d",1407033),("bd494ea7299b6750",4918276))
def export(blob,at,obj,svg):
 vbytes=struct.unpack_from("<I",blob,at+48)[0];start=at+52;tail=start+vbytes
 n,stride=struct.unpack_from("<II",blob,tail+8)
 icount,ibytes=struct.unpack_from("<II",blob,tail+151)
 if stride!=88 or n*stride!=vbytes or icount%3 or ibytes!=icount*2:raise ValueError("Framing invalid")
 indices=struct.unpack_from("<"+str(icount)+"H",blob,tail+159)
 if max(indices)>=n:raise ValueError("Index out of bounds")
 xyz=[struct.unpack_from("<3f",blob,start+i*stride) for i in range(n)]
 uv=[struct.unpack_from("<2f",blob,start+i*stride+48) for i in range(n)]
 if not all(all(math.isfinite(x) for x in (*p,*t)) for p,t in zip(xyz,uv)):raise ValueError("Nonfinite vertex/UV")
 with obj.open("w",encoding="utf-8") as f:
  f.write("# SMELTER Magicka2 provisional UV offset 48, untextured/unrigged\n")
  for p in xyz:f.write("v %.9g %.9g %.9g\n"%p)
  for u,v in uv:f.write("vt %.9g %.9g\n"%(u,1-v))
  f.write("o magicka2_uv48\n")
  for i in range(0,icount,3):
   a,b,c=[j+1 for j in indices[i:i+3]]
   f.write(f"f {a}/{a} {b}/{b} {c}/{c}\n")
 with svg.open("w",encoding="utf-8") as f:
  f.write('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="1024" height="1024"><rect width="1024" height="1024" fill="#1b2531"/>')
  for y in range(8):
   for x in range(8):
    if (x+y)%2==0:f.write(f'<rect x="{x*128}" y="{y*128}" width="128" height="128" fill="#475a6e"/>')
  for i in range(0,icount,3):
   tri=[uv[j] for j in indices[i:i+3]]
   coords=" ".join("%.2f,%.2f"%(u*1024,v*1024) for u,v in tri)
   f.write(f'<polygon points="{coords}" fill="none" stroke="#f0c878" stroke-opacity=".48" stroke-width=".75"/>')
  f.write("</svg>")
 return {"vertex_count":n,"triangle_count":icount//3,"uv_offset":48,"obj":str(obj),"uv_atlas_svg":str(svg),"uv_semantics_verified":False,"material_mapping_verified":False}
def main():
 p=argparse.ArgumentParser();p.add_argument("--root",default=r"C:\SMELTER");a=p.parse_args()
 root=pathlib.Path(a.root);base=root/"workspace"/"magicka2-reconstructed"
 dirs=sorted((d for d in base.iterdir() if d.is_dir() and all((d/(name+".decoded.bin")).is_file() for name,_ in RES)),reverse=True)
 if not dirs:p.error("Missing reconstructed resource files")
 out=root/"workspace"/"magicka2-uv-preview"/(datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S-")+uuid.uuid4().hex[:6]);out.mkdir(parents=True)
 report={"tool":"SMELTER Magicka2 UV-enabled preview","read_only":True,"uv_mapping_verified":False,"resources":[]}
 for name,at in RES:
  report["resources"].append({"name":name,**export((dirs[0]/(name+".decoded.bin")).read_bytes(),at,out/(name+".obj"),out/(name+"-uv.svg"))})
 dest=out/"magicka2-uv-preview.json";dest.write_text(json.dumps(report,indent=2),encoding="utf-8")
 print("UV preview folder:",out);print("Report:",dest)
 for r in report["resources"]:print(r["name"],"OBJ:",r["obj"],"UV SVG:",r["uv_atlas_svg"])
 print("UV mapping and material associations are provisional; original game files unchanged.")
if __name__=="__main__":main()
