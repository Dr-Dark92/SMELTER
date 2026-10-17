#!/usr/bin/env python3
"""Read-only UV-interpolated textured rasterizer with z-buffer for SMELTER."""
import argparse,datetime,json,math,pathlib,uuid
from PIL import Image,ImageDraw
IDS=("91e92dee4343fc7d","bd494ea7299b6750")
def load(path):
 vs=[];ts=[];fs=[]
 for line in path.open(encoding="utf-8"):
  s=line.split()
  if not s:continue
  if s[0]=="v":vs.append(tuple(map(float,s[1:4])))
  elif s[0]=="vt":ts.append(tuple(map(float,s[1:3])))
  elif s[0]=="f":fs.append([tuple(map(int,x.split("/")[:2])) for x in s[1:4]])
 return vs,ts,fs
def raster(vs,ts,fs,texture,output,axes,reverse=False,size=900):
 projected=[(v[axes[0]],v[axes[1]],v[axes[2]]) for v in vs]
 xx=[p[0] for p in projected];yy=[p[1] for p in projected]
 scale=min((size-80)/max(max(xx)-min(xx),1e-9),(size-80)/max(max(yy)-min(yy),1e-9))
 xy=[(40+(p[0]-min(xx))*scale,size-40-(p[1]-min(yy))*scale,p[2]) for p in projected]
 pix=Image.new("RGB",(size,size),(20,26,35));dst=pix.load()
 tex=texture.convert("RGB");tp=tex.load();tw,th=tex.size
 zbuf=[float("-inf")]*size*size
 drawn=0
 for face in fs:
  if len(face)!=3:continue
  try:
   a,b,c=[xy[i-1] for i,t in face]
   uv=[ts[t-1] for i,t in face]
  except IndexError:continue
  denom=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
  if abs(denom)<1e-8:continue
  x0=max(0,int(math.floor(min(a[0],b[0],c[0]))));x1=min(size-1,int(math.ceil(max(a[0],b[0],c[0]))))
  y0=max(0,int(math.floor(min(a[1],b[1],c[1]))));y1=min(size-1,int(math.ceil(max(a[1],b[1],c[1]))))
  for y in range(y0,y1+1):
   for x in range(x0,x1+1):
    px=x+.5;py=y+.5
    w0=((b[1]-c[1])*(px-c[0])+(c[0]-b[0])*(py-c[1]))/denom
    w1=((c[1]-a[1])*(px-c[0])+(a[0]-c[0])*(py-c[1]))/denom
    w2=1-w0-w1
    if min(w0,w1,w2)<-1e-6:continue
    z=w0*a[2]+w1*b[2]+w2*c[2]
    if reverse:z=-z
    ix=y*size+x
    if z<=zbuf[ix]:continue
    zbuf[ix]=z
    u=w0*uv[0][0]+w1*uv[1][0]+w2*uv[2][0]
    v=w0*uv[0][1]+w1*uv[1][1]+w2*uv[2][1]
    tx=max(0,min(tw-1,int(u*(tw-1))))
    ty=max(0,min(th-1,int((1-v)*(th-1))))
    dst[x,y]=tp[tx,ty]
  drawn+=1
 pix.save(output)
 return drawn
def main():
 p=argparse.ArgumentParser();p.add_argument("--root",default=r"C:\SMELTER");a=p.parse_args()
 root=pathlib.Path(a.root);base=root/"workspace"/"magicka2-texture-candidates"
 dirs=sorted((d for d in base.iterdir() if d.is_dir() and all((d/(n+".obj")).is_file() and (d/(n+"-candidate.png")).is_file() for n in IDS)),reverse=True)
 if not dirs:p.error("Candidate textured assets missing")
 src=dirs[0];out=root/"workspace"/"magicka2-uv-raster"/(datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S-")+uuid.uuid4().hex[:6]);out.mkdir(parents=True)
 report={"tool":"SMELTER interpolated textured UV raster v1","read_only":True,"material_binding_verified":False,"uv_semantics_verified":False,"renderer":"orthographic barycentric UV interpolation with z-buffer; unlit diffuse, no transparency","resources":[]}
 for name in IDS:
  vs,ts,fs=load(src/(name+".obj"));entry={"name":name,"views":[]}
  with Image.open(src/(name+"-candidate.png")) as im:
   for label,axes,reverse in (("front",(0,2,1),False),("back",(0,2,1),True),("side",(1,2,0),False)):
    dest=out/(name+"-"+label+".png")
    n=raster(vs,ts,fs,im,dest,axes,reverse)
    entry["views"].append({"view":label,"png":str(dest),"processed_triangles":n})
  report["resources"].append(entry)
 dest=out/"magicka2-uv-raster.json";dest.write_text(json.dumps(report,indent=2),encoding="utf-8")
 print("Output:",out);print("Report:",dest)
 print("UV interpolation and z-buffer enabled; candidate material bindings still unverified.")
if __name__=="__main__":main()
