#!/usr/bin/env python3
"""SMELTER: software-render provisional textured OBJ previews; read-only."""
import argparse,datetime,json,math,pathlib,uuid
from PIL import Image,ImageDraw
IDS=("91e92dee4343fc7d","bd494ea7299b6750")
def load_obj(path):
 vs=[];uv=[];fs=[]
 for line in path.open(encoding="utf-8"):
  s=line.split()
  if not s:continue
  if s[0]=="v":vs.append(tuple(map(float,s[1:4])))
  elif s[0]=="vt":uv.append(tuple(map(float,s[1:3])))
  elif s[0]=="f":
   face=[tuple(map(int,x.split("/")[:2])) for x in s[1:4]]
   fs.append(face)
 return vs,uv,fs
def render(vs,uv,faces,tex,out,axis,flip=False):
 w=h=1100
 # XZ front, YZ side, and XZ reverse.
 projected=[(v[axis[0]],v[axis[1]],v[axis[2]]) for v in vs]
 xs=[p[0] for p in projected];ys=[p[1] for p in projected]
 scale=min(980/max(max(xs)-min(xs),1e-8),980/max(max(ys)-min(ys),1e-8))
 def screen(p):return (60+(p[0]-min(xs))*scale,1040-(p[1]-min(ys))*scale)
 image=Image.new("RGB",(w,h),(22,27,36));draw=ImageDraw.Draw(image)
 pixels=tex.load();tw,th=tex.size
 tris=[]
 for face in faces:
  xyz=[projected[a-1] for a,b in face]
  if len({a for a,b in face})!=3:continue
  coords=[screen(p) for p in xyz]
  area=(coords[1][0]-coords[0][0])*(coords[2][1]-coords[0][1])-(coords[1][1]-coords[0][1])*(coords[2][0]-coords[0][0])
  if abs(area)<.01:continue
  u=sum(uv[b-1][0] for a,b in face)/3
  v=sum(uv[b-1][1] for a,b in face)/3
  color=pixels[min(tw-1,max(0,int(u*(tw-1)))),min(th-1,max(0,int((1-v)*(th-1))))]
  depth=sum(p[2] for p in xyz)/3
  tris.append((depth,coords,color))
 tris.sort(key=lambda t:t[0],reverse=not flip)
 for depth,coords,color in tris:
  draw.polygon(coords,fill=color)
  draw.line(coords+[coords[0]],fill=(30,36,45),width=1)
 image.save(out)
 return len(tris)
def main():
 p=argparse.ArgumentParser();p.add_argument("--root",default=r"C:\SMELTER");a=p.parse_args()
 root=pathlib.Path(a.root);base=root/"workspace"/"magicka2-texture-candidates"
 dirs=sorted((d for d in base.iterdir() if d.is_dir() and all((d/(name+".obj")).exists() and (d/(name+"-candidate.png")).exists() for name in IDS)),reverse=True)
 if not dirs:p.error("Missing candidate textured OBJ package")
 src=dirs[0];out=root/"workspace"/"magicka2-textured-preview"/(datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S-")+uuid.uuid4().hex[:6]);out.mkdir(parents=True)
 report={"tool":"SMELTER provisional textured software previews","read_only":True,"render_type":"centroid texture sampling with triangle painter sorting (not UV interpolation or physically correct occlusion)","material_binding_verified":False,"resources":[]}
 for name in IDS:
  vs,uv,faces=load_obj(src/(name+".obj"))
  with Image.open(src/(name+"-candidate.png")) as im:
   tex=im.convert("RGB")
   results=[]
   for label,axis,flip in (("front",(0,2,1),False),("back",(0,2,1),True),("side",(1,2,0),False)):
    path=out/(name+"-"+label+".png")
    count=render(vs,uv,faces,tex,path,axis,flip)
    results.append({"view":label,"png":str(path),"drawn_triangles":count})
  report["resources"].append({"name":name,"views":results})
 dest=out/"magicka2-textured-preview.json";dest.write_text(json.dumps(report,indent=2),encoding="utf-8")
 print("Preview folder:",out);print("Report:",dest)
 print("Caveat: approximate triangle-flat sampling; visual material matches remain unverified.")
if __name__=="__main__":main()
