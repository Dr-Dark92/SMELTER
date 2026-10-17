#!/usr/bin/env python3
"""Read-only Magicka2 candidate-textured OBJ package. Materials are hypotheses."""
import argparse,datetime,json,pathlib,uuid,shutil
from PIL import Image
RES=(("91e92dee4343fc7d","91e92dee4343fc7d_1319497.dds"),
     ("bd494ea7299b6750","bd494ea7299b6750_4218716.dds"))
def main():
 p=argparse.ArgumentParser();p.add_argument("--root",default=r"C:\SMELTER");a=p.parse_args()
 root=pathlib.Path(a.root)
 uvroot=root/"workspace"/"magicka2-uv-preview";ddsroot=root/"workspace"/"magicka2-dds-corrected"
 uvdirs=sorted((x for x in uvroot.iterdir() if x.is_dir() and all((x/(r+".obj")).is_file() for r,_ in RES)),reverse=True)
 ddirs=sorted((x for x in ddsroot.iterdir() if x.is_dir() and all((x/tex).is_file() for _,tex in RES)),reverse=True)
 if not uvdirs or not ddirs:p.error("UV OBJ or DDS exports not found")
 out=root/"workspace"/"magicka2-texture-candidates"/(datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S-")+uuid.uuid4().hex[:6]);out.mkdir(parents=True)
 report={"tool":"SMELTER Magicka2 candidate material OBJ","read_only":True,"material_binding_verified":False,"visual_appearance_verified":False,"resources":[]}
 for name,tex in RES:
  png=out/(name+"-candidate.png")
  with Image.open(ddirs[0]/tex) as im:im.convert("RGBA").save(png)
  mtl=out/(name+".mtl");mtl.write_text("newmtl candidate_material\nKd 1 1 1\nKa 0 0 0\nKs 0 0 0\nmap_Kd "+png.name+"\n",encoding="utf-8")
  obj=out/(name+".obj")
  source=(uvdirs[0]/(name+".obj")).read_text(encoding="utf-8")
  source="mtllib "+mtl.name+"\n"+source.replace("o magicka2_uv48","o magicka2_uv48\nusemtl candidate_material")
  obj.write_text(source,encoding="utf-8")
  report["resources"].append({"name":name,"obj":str(obj),"mtl":str(mtl),"texture_png":str(png),"source_dds":str(ddirs[0]/tex),"material_status":"unverified candidate"})
 dest=out/"magicka2-texture-candidates.json";dest.write_text(json.dumps(report,indent=2),encoding="utf-8")
 print("Candidate textured OBJ folder:",out);print("Report:",dest)
 print("These are experimental material assignments, not recovered game bindings.")
if __name__=="__main__":main()
