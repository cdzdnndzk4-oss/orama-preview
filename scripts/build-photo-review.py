import json
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
from PIL import Image, ImageChops
root=Path(__file__).resolve().parents[1]
out=root.parent/'output/pdf/ORAMA-5-products-photo-review.pdf'
out.parent.mkdir(parents=True,exist_ok=True)
font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
pdfmetrics.registerFont(TTFont('DejaVu',font))
W,H=A4
# Display rule for every current and future product image.
TARGET_FRAME_WIDTH_PT=400
MAX_FRAME_HEIGHT_PT=152
FOREGROUND_DIFFERENCE=32

def content_box(path):
    image=Image.open(path).convert("RGB")
    difference=ImageChops.difference(image, Image.new("RGB",image.size,"white"))
    mask=difference.convert("L").point(lambda value:255 if value>FOREGROUND_DIFFERENCE else 0)
    return image.size, mask.getbbox() or (0,0,*image.size)
c=canvas.Canvas(str(out),pagesize=A4)
items=['yalea-chen-vya001','ceo-94','yalea-elisabeth-vya040','furla-vfu773','furla-535']
labels=['Μπροστά','Τρία τέταρτα','Πλάι']
notes={
'yalea-chen-vya001':'Οι φωτογραφίες και η ετικέτα έχουν επιβεβαιωθεί.',
'furla-vfu773':'Η εμφάνιση των τριών φωτογραφιών εγκρίθηκε.',
'furla-535':'Η εμφάνιση των τριών φωτογραφιών εγκρίθηκε.',
}
for n,slug in enumerate(items,1):
 d=json.loads((root/'catalog-drafts'/f'{slug}.json').read_text())
 photos=d.get('photos') or d.get('processed_photos')
 c.setFillColor(HexColor('#073F72')); c.rect(0,H-80,W,80,fill=1,stroke=0)
 c.setFillColor(HexColor('#FFFFFF')); c.setFont('DejaVu',22); c.drawString(30,H-44,'ORAMA')
 c.setFont('DejaVu',10); c.drawRightString(W-30,H-44,f'ΕΛΕΓΧΟΣ ΠΡΟΪΟΝΤΟΣ {n}/5')
 c.setFillColor(HexColor('#123F5D')); c.setFont('DejaVu',17); c.drawString(30,H-109,f"{d['brand']} {d['model']}")
 c.setFont('DejaVu',11); c.drawString(30,H-130,f"{d['price_eur']} €  |  {d['lens_mm']}-{d['bridge_mm']}-{d['temple_mm']}  |  Χρώμα: {d.get('color_code') or '—'}")
 c.drawString(30,H-148,f"Διαθεσιμότητα: {d['inventory']['quantity']} τεμάχιο  |  Κατάστημα: {d['inventory']['store']}")
 for i,p in enumerate(photos):
  y_top=H-175-i*184
  path=(root/'catalog-drafts'/p['file']).resolve()
  (iw,ih),box=content_box(path)
  bw,bh=W-60,157
  object_width=box[2]-box[0]
  object_height=box[3]-box[1]
  scale=min(TARGET_FRAME_WIDTH_PT/object_width,MAX_FRAME_HEIGHT_PT/object_height)
  center_x=(box[0]+box[2])/2
  center_y_from_bottom=ih-(box[1]+box[3])/2
  x=W/2-center_x*scale
  y=y_top-bh/2-center_y_from_bottom*scale
  c.saveState()
  clip=c.beginPath(); clip.rect(30,y_top-bh,bw,bh)
  c.clipPath(clip,stroke=0,fill=0)
  c.drawImage(str(path),x,y,width=iw*scale,height=ih*scale,mask='auto')
  c.restoreState()
  c.setFillColor(HexColor('#123F5D')); c.setFont('DejaVu',9); c.drawString(34,y_top-169,labels[i])
 c.setFillColor(HexColor('#4A6576')); c.setFont('DejaVu',9)
 c.drawString(30,75,notes.get(slug,'Οι φωτογραφίες έχουν ελεγχθεί σε προηγούμενο δείγμα.'))
 c.drawString(30,60,'Εσωτερικό προσχέδιο. Δεν πραγματοποιούνται αγορές από αυτό το αρχείο.')
 c.showPage()
c.save()
print(out, out.stat().st_size)
