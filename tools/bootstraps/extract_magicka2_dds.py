#!/usr/bin/env python3
"""Carve validated DDS textures from reconstructed Magicka 2 binaries, read-only."""
import argparse,datetime,hashlib,json,pathlib,struct,uuid
NAMES=("91e92dee4343fc7d","bd494ea7299b6750")
def main():
 p=argparse.ArgumentParser();p.add_argument("--root",default=r"C:\SMELTER");a=p.parse_args()
 root=pathlib.Path(a.root)/"workspace"/"magicka2-reconstructed"
 folders=sorted((x for x in root.iterdir() if x.is_dir() and all((x/(n+".decoded.bin")).exists() for n in NAMES)),reverse=True)
 if not folders:p.error("Reconstructed resources not found")
 src=folders[0]
 dest=pathlib.Path(a.root)/"workspace"/"magicka2-dds"/(datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S-")+uuid.uuid4().hex[:8]);dest.mkdir(parents=True)
 report={"source":str(src),"read_only_source":True,"files":[]}
 for name in NAMES:
  data=(src/(name+".decoded.bin")).read_bytes()
  start=0
  while True:
   i=data.find(b"DDS ",start)
   if i<0:break
   start=i+4
   item={"source":name,"offset":i,"status":"skipped"}
   try:
    if i+128>len(data) or struct.unpack_from("<I",data,i+4)[0]!=124:raise ValueError("Invalid DDS header")
    height,width=struct.unpack_from("<II",data,i+12)
    mip=struct.unpack_from("<I",data,i+28)[0] or 1
    flags=struct.unpack_from("<I",data,i+80)[0]
    fourcc=data[i+84:i+88]
    if not (1<=width<=16384 and 1<=height<=16384 and 1<=mip<=16):raise ValueError("Invalid dimensions or mip count")
    if flags&4 and fourcc in (b"DXT1",b"DXT3",b"DXT5"):
     blocksize=8 if fourcc==b"DXT1" else 16
     size=sum(max(1,(max(1,width>>level)+3)//4)*max(1,(max(1,height>>level)+3)//4)*blocksize for level in range(mip))
    elif flags&0x40:
     bpp=struct.unpack_from("<I",data,i+88)[0]
     if bpp not in (8,16,24,32):raise ValueError("Unsupported RGB pixel size")
     size=sum(max(1,width>>level)*max(1,height>>level)*(bpp//8) for level in range(mip))
    else:raise ValueError("Unsupported DDS pixel format")
    end=i+128+size
    if end>len(data):raise ValueError("Truncated DDS")
    blob=data[i:end]
    path=dest/(name+"_"+str(i)+".dds");path.write_bytes(blob)
    item.update(status="extracted",width=width,height=height,mipmaps=mip,format=fourcc.decode("ascii","replace"),bytes=len(blob),sha256=hashlib.sha256(blob).hexdigest(),output=str(path))
   except Exception as e:item["reason"]=str(e)
   report["files"].append(item)
 target=dest/"magicka2-dds-extraction.json";target.write_text(json.dumps(report,indent=2),encoding="utf-8")
 print("Report:",target)
 print("DDS extracted:",sum(x["status"]=="extracted" for x in report["files"]),"candidates:",len(report["files"]))
if __name__=="__main__":main()
