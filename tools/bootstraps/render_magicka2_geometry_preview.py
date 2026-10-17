#!/usr/bin/env python3
"""Read-only automated Magicka2 OBJ preview: Blender headless renders or offline SVG."""
import argparse,datetime,json,pathlib,uuid,shutil,subprocess,math,xml.sax.saxutils
IDS=("91e92dee4343fc7d","bd494ea7299b6750")
def svg_preview(obj,dest):
 vertices=[];faces=[]
 for line in obj.open(encoding="utf-8"):
  parts=line.split()
  if not parts:continue
  if parts[0]=="v":vertices.append(tuple(float(x) for x in parts[1:4]))
  if parts[0]=="f":faces.append(tuple(int(x.split("/")[0])-1 for x in parts[1:4]))
 # Simple orthographic projection (X,Z) and depth ordering; no Blender required.
 pts=[(x,z,y) for x,y,z in vertices]
 minx=min(p[0] for p in pts);maxx=max(p[0] for p in pts)
 minz=min(p[1] for p in pts);maxz=max(p[1] for p in pts)
 scale=min(880/max(maxx-minx,1e-9),880/max(maxz-minz,1e-9))
 project=lambda p:(60+(p[0]-minx)*scale,940-(p[1]-minz)*scale)
 polygons=[]
 for a,b,c in faces:
  tri=(pts[a],pts[b],pts[c])
  xy=[project(p) for p in tri]
  polygons.append((sum(p[2] for p in tri)/3,xy))
 polygons.sort(reverse=True)
 with dest.open("w",encoding="utf-8") as f:
  f.write('<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="1000" viewBox="0 0 1000 1000"><rect width="1000" height="1000" fill="#121923"/>')
  for depth,xy in polygons:
   s=" ".join("%.2f,%.2f"%p for p in xy)
   f.write('<polygon points="%s" fill="#7bb5c8" fill-opacity=".68" stroke="#dceef4" stroke-width=".35"/>'%s)
  f.write('</svg>')
 return {"projection":"X/Z orthographic, depth-sort by Y","svg":str(dest),"faces":len(faces)}
def main():
 p=argparse.ArgumentParser();p.add_argument("--root",default=r"C:\SMELTER");a=p.parse_args()
 root=pathlib.Path(a.root);base=root/"workspace"/"magicka2-full-geometry"
 dirs=sorted((d for d in base.iterdir() if d.is_dir() and all((d/(name+".obj")).is_file() for name in IDS)),reverse=True)
 if not dirs:p.error("Complete OBJ exports not found")
 out=root/"workspace"/"magicka2-visual-preview"/(datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S-")+uuid.uuid4().hex[:6]);out.mkdir(parents=True)
 report={"tool":"SMELTER Magicka2 headless visual preview","read_only":True,"visually_verified_by_human":False,"resources":[]}
 for name in IDS:
  report["resources"].append({"name":name,**svg_preview(dirs[0]/(name+".obj"),out/(name+".svg"))})
 path=out/"magicka2-visual-preview.json";path.write_text(json.dumps(report,indent=2),encoding="utf-8")
 print("Preview folder:",out)
 print("Open the SVG images with your browser; no manual Blender editing required.")
 print("Report:",path)
if __name__=="__main__":main()
