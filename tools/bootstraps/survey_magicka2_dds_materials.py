#!/usr/bin/env python3
"""Read-only Magicka2 DDS inventory and contact sheet; no guessed material binding."""
import argparse,datetime,json,pathlib,uuid,hashlib,struct
def main():
 p=argparse.ArgumentParser();p.add_argument("--root",default=r"C:\SMELTER");a=p.parse_args()
 root=pathlib.Path(a.root);base=root/"workspace"/"magicka2-dds-corrected"
 if not base.exists():p.error("Verified DDS export directory missing")
 dirs=sorted((d for d in base.iterdir() if d.is_dir() and list(d.rglob("*.dds"))),reverse=True)
 if not dirs:p.error("No DDS exports found")
 src=dirs[0];files=sorted(src.rglob("*.dds"))
 out=root/"workspace"/"magicka2-material-survey"/(datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S-")+uuid.uuid4().hex[:6]);out.mkdir(parents=True)
 rows=[];thumbs=[]
 try:
  from PIL import Image,ImageOps,ImageDraw
  pillow=True
 except ImportError:pillow=False
 for f in files:
  data=f.read_bytes();item={"file":str(f),"name":f.name,"sha256":hashlib.sha256(data).hexdigest(),"bytes":len(data),"dds_magic":data[:4]==b"DDS ","preview_success":False}
  if item["dds_magic"] and len(data)>=128:
   item["height"]=struct.unpack_from("<I",data,12)[0];item["width"]=struct.unpack_from("<I",data,16)[0]
   item["fourcc"]=data[84:88].decode("ascii","replace")
  if pillow:
   try:
    with Image.open(f) as img:
     rgb=img.convert("RGBA");rgb.thumbnail((220,220))
     thumbs.append((f.name,rgb.copy()));item["preview_success"]=True
   except Exception as e:item["preview_error"]=str(e)[:250]
  rows.append(item)
 sheet=None
 if pillow and thumbs:
  cols=4;cw=270;ch=275
  canvas=Image.new("RGB",(cols*cw,((len(thumbs)+cols-1)//cols)*ch),"#202630")
  draw=ImageDraw.Draw(canvas)
  for i,(name,img) in enumerate(thumbs):
   x=(i%cols)*cw;y=(i//cols)*ch
   canvas.paste(img,(x+(cw-img.width)//2,y+10),img)
   draw.text((x+8,y+235),name[:37],fill="white")
  sheet=out/"magicka2-dds-contact-sheet.png";canvas.save(sheet)
 report={"tool":"SMELTER Magicka2 DDS material survey","source":str(src),"read_only":True,"dds_files":len(rows),"pillow_available":pillow,"contact_sheet":str(sheet) if sheet else None,"material_binding_verified":False,"textures":rows}
 dest=out/"magicka2-material-survey.json";dest.write_text(json.dumps(report,indent=2),encoding="utf-8")
 print("Report:",dest);print("DDS files:",len(rows))
 print("Contact sheet:",sheet or "unavailable (install Pillow to enable decoding)")
 print("No DDS files or game installations modified.")
if __name__=="__main__":main()
