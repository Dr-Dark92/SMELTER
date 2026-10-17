#!/usr/bin/env python3
"""Read-only audit of Magicka 2 vertex UV candidates in 88-byte records."""
import argparse,datetime,json,math,pathlib,statistics,struct,uuid
RES=(("91e92dee4343fc7d",1407033),("bd494ea7299b6750",4918276))
def audit(blob,at):
 size=struct.unpack_from("<I",blob,at+48)[0];start=at+52;tail=start+size
 n,stride=struct.unpack_from("<II",blob,tail+8)
 if stride!=88 or size!=n*stride:raise ValueError("Vertex framing mismatch")
 result=[]
 for off in range(0,81,4):
  uv=[struct.unpack_from("<2f",blob,start+i*stride+off) for i in range(n)]
  if not all(math.isfinite(v) for pair in uv for v in pair):continue
  u=[p[0] for p in uv];v=[p[1] for p in uv]
  inside=sum(-.01<=x<=1.01 and -.01<=y<=1.01 for x,y in uv)
  unique=len(set(uv))
  # UVs often have exact duplicates at seams and occupy approximately [0,1].
  result.append({"offset":off,"min_u":min(u),"max_u":max(u),"min_v":min(v),"max_v":max(v),"fraction_unit_square":round(inside/n,5),"unique_pairs":unique,"first_five":uv[:5]})
 result.sort(key=lambda x:(-x["fraction_unit_square"],-x["unique_pairs"]))
 return {"vertices":n,"stride":stride,"uv_candidates":result,"uv_verified":False}
def main():
 p=argparse.ArgumentParser();p.add_argument("--root",default=r"C:\SMELTER");a=p.parse_args()
 root=pathlib.Path(a.root);base=root/"workspace"/"magicka2-reconstructed"
 dirs=sorted((d for d in base.iterdir() if d.is_dir() and all((d/(name+".decoded.bin")).is_file() for name,_ in RES)),reverse=True)
 if not dirs:p.error("Reconstructed resource files missing")
 report={"tool":"SMELTER Magicka2 UV candidate audit","read_only":True,"uv_verified":False,"resources":[]}
 for name,at in RES:report["resources"].append({"name":name,**audit((dirs[0]/(name+".decoded.bin")).read_bytes(),at)})
 out=root/"workspace"/"magicka2-uv-audit"/(datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S-")+uuid.uuid4().hex[:6]);out.mkdir(parents=True)
 dest=out/"magicka2-uv-audit.json";dest.write_text(json.dumps(report,indent=2),encoding="utf-8")
 print("UV audit:",dest)
 for r in report["resources"]:print(r["name"],"candidate offsets:",[(c["offset"],c["fraction_unit_square"]) for c in r["uv_candidates"][:5]])
if __name__=="__main__":main()
