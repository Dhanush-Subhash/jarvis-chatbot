# F.R.I.D.A.Y. — BY DHANUSH SUBHASH
# Female Replacement Intelligent Digital Assistant Youth

import math, os, sys, threading, time, textwrap, io, tempfile, queue, random, json, re

def require(pkg, imp=None):
    try: __import__(imp or pkg)
    except ImportError:
        print(f"Missing: pip install {pkg}"); sys.exit(1)

for p,i in [("pygame","pygame"),("ollama","ollama"),("edge_tts","edge_tts"),
            ("speech_recognition","speech_recognition"),("pyaudio","pyaudio")]:
    require(p, i)

import pygame, ollama, asyncio, edge_tts
import speech_recognition as sr

# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════
W, H        = 1200, 750
FPS         = 60
MODEL       = "llama3.2"
MAX_HISTORY = 40
MEMORY_FILE = os.path.expanduser("~/.friday_memory.json")

# ── Bloody red palette ────────────────────────────────────────────────────────
RED         = (220,  20,  20)   # primary accent
RED2        = (160,  10,  10)   # dimmer red
RED3        = (255,  60,  60)   # bright highlight
REDGLOW     = (180,   0,   0)   # glow base
CRIMSON     = (140,   0,   0)   # deep crimson
BLOOD       = ( 80,   0,   0)   # very dark red
DARK        = (  8,   2,   2)   # near-black with red tint
PANEL       = ( 20,   4,   4)   # panel background
PANELB      = ( 28,   6,   6)   # slightly lighter panel
PANEL2      = ( 22,   5,   5)   # alternating row
MUTED       = (110,  50,  50)   # muted red-grey
WHITE       = (240, 210, 210)   # warm white
DIM_WHITE   = (180, 140, 140)
YELLOW      = (255, 180,  50)   # warning amber
GREEN       = (180, 255, 100)   # status green (kept for online dot)
BLACK       = (  0,   0,   0)

# Hotkeys (all use Ctrl or Shift — never bare letters)
# Ctrl+L  = listen (voice)
# Ctrl+M  = mute toggle
# Ctrl+N  = add memory
# Ctrl+Up/Down = scroll

SYSTEM_PROMPT = (
    "You are F.R.I.D.A.Y. (Female Replacement Intelligent Digital Assistant Youth), "
    "Tony Stark's AI assistant. You are sharp, confident, occasionally sarcastic, "
    "and fiercely loyal. Keep answers concise — 1-3 sentences unless asked for detail. "
    "Occasionally call the user 'boss' in the style of the character."
)

# ══════════════════════════════════════════════════════════════════════════════
# MEMORY SYSTEM
# ══════════════════════════════════════════════════════════════════════════════
class MemoryStore:
    DEFAULT_MEMORIES = [
        {"key": "user_name",  "value": "Dhanush",          "note": "User's first name",     "added": "2025-01-01"},
        {"key": "created_by", "value": "Dhanush Subhash",  "note": "FRIDAY creator",        "added": "2025-01-01"},
        {"key": "assistant",  "value": "F.R.I.D.A.Y.",     "note": "AI assistant identity", "added": "2025-01-01"},
        {"key": "model",      "value": MODEL,               "note": "Active LLM",            "added": "2025-01-01"},
        {"key": "voice",      "value": "Aria Neural (en-US)","note": "TTS voice",            "added": "2025-01-01"},
    ]

    def __init__(self):
        self.entries: list[dict] = []
        self.load()

    def load(self):
        if os.path.exists(MEMORY_FILE):
            try:
                with open(MEMORY_FILE) as f:
                    self.entries = json.load(f); return
            except: pass
        self.entries = [dict(e) for e in self.DEFAULT_MEMORIES]
        self.save()

    def save(self):
        try:
            with open(MEMORY_FILE,"w") as f: json.dump(self.entries,f,indent=2)
        except Exception as e: print(f"[memory] {e}")

    def add(self,key,value,note=""):
        key=key.strip().lower().replace(" ","_")
        for e in self.entries:
            if e["key"]==key:
                e["value"]=value; e["note"]=note or e.get("note","")
                e["added"]=time.strftime("%Y-%m-%d"); self.save()
                return f"Updated: {key} = {value}"
        self.entries.append({"key":key,"value":value,"note":note,"added":time.strftime("%Y-%m-%d")})
        self.save(); return f"Remembered: {key} = {value}"

    def delete(self,key):
        key=key.strip().lower().replace(" ","_")
        before=len(self.entries)
        self.entries=[e for e in self.entries if e["key"]!=key]
        self.save()
        return f"Deleted '{key}'." if len(self.entries)<before else f"Key '{key}' not found."

    def get(self,key):
        key=key.strip().lower().replace(" ","_")
        for e in self.entries:
            if e["key"]==key: return e["value"]
        return None

    def as_context(self):
        if not self.entries: return ""
        lines=["Persistent memory:"]
        for e in self.entries:
            lines.append(f"  • {e['key']}: {e['value']}"+(f"  ({e['note']})" if e.get("note") else ""))
        return "\n".join(lines)

    def parse_command(self,text):
        t=text.strip().lower()
        for sep in [" is "," as ","="]:
            if t.startswith("remember ") and sep in t:
                rest=t[len("remember "):]
                parts=rest.split(sep,1)
                if len(parts)==2:
                    return ("add", self.add(parts[0].strip(),parts[1].strip()))
        if t.startswith("forget "):
            return ("del", self.delete(t[len("forget "):].strip()))
        return None

# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def draw_text(surf,text,font,color,x,y,max_w=None,align="left"):
    if max_w:
        words=text.split(); lines,cur=[],""
        for w in words:
            test=(cur+" "+w).strip()
            if font.size(test)[0]<=max_w: cur=test
            else:
                if cur: lines.append(cur)
                cur=w
        if cur: lines.append(cur)
    else: lines=[text]
    y0=y
    for line in lines:
        s=font.render(line,True,color)
        if   align=="center": surf.blit(s,(x-s.get_width()//2,y0))
        elif align=="right":  surf.blit(s,(x-s.get_width(),y0))
        else:                 surf.blit(s,(x,y0))
        y0+=font.get_linesize()
    return y0-y

def glow_circle(surf,color,cx,cy,r,width=1,alpha=80):
    s=pygame.Surface((r*2+20,r*2+20),pygame.SRCALPHA)
    for i in range(3,0,-1):
        pygame.draw.circle(s,(*color,alpha//(i*2)),(r+10,r+10),r+i*2,width+i)
    pygame.draw.circle(s,(*color,alpha),(r+10,r+10),r,width)
    surf.blit(s,(cx-r-10,cy-r-10))

def draw_corners(surf,rect,color,size=14,width=2):
    x,y,w,h=rect
    segs=[[(x,y+size),(x,y),(x+size,y)],[(x+w-size,y),(x+w,y),(x+w,y+size)],
          [(x,y+h-size),(x,y+h),(x+size,y+h)],[(x+w-size,y+h),(x+w,y+h),(x+w,y+h-size)]]
    for seg in segs: pygame.draw.lines(surf,color,False,seg,width)

def make_scanlines(w,h):
    s=pygame.Surface((w,h),pygame.SRCALPHA)
    for y in range(0,h,4): pygame.draw.line(s,(180,0,0,10),(0,y),(w,y))
    return s

def clean_tts(text):
    t=re.sub(r'\*{1,3}(.*?)\*{1,3}',r'\1',text)
    t=re.sub(r'_{1,2}(.*?)_{1,2}',r'\1',t)
    t=re.sub(r'`{1,3}.*?`{1,3}','',t,flags=re.DOTALL)
    t=re.sub(r'^[\-\•\*]\s+','',t,flags=re.MULTILINE)
    t=re.sub(r'https?://\S+','',t)
    t=re.sub(r'\s+',' ',t).strip()
    if len(t)>420:
        cut=t[:420].rfind('.')
        t=t[:cut+1] if cut>100 else t[:420]
    return t

# ══════════════════════════════════════════════════════════════════════════════
# ARC REACTOR  (red version)
# ══════════════════════════════════════════════════════════════════════════════
class ArcReactor:
    def __init__(self,cx,cy,r=32):
        self.cx,self.cy,self.r=cx,cy,r
        self.a1=self.a2=self.pulse=0.0
    def update(self,dt):
        self.a1=(self.a1+55*dt)%360
        self.a2=(self.a2-80*dt)%360
        self.pulse=(self.pulse+2.2*dt)%(2*math.pi)
    def draw(self,surf):
        cx,cy,r=self.cx,self.cy,self.r
        glow_circle(surf,RED,cx,cy,r+8,1,45)
        for i in range(12):
            a=math.radians(self.a1+i*30)
            x1,y1=cx+r*math.cos(a),cy+r*math.sin(a)
            x2,y2=cx+r*math.cos(a+math.radians(14)),cy+r*math.sin(a+math.radians(14))
            pygame.draw.line(surf,RED,(int(x1),int(y1)),(int(x2),int(y2)),2)
        for i in range(8):
            a=math.radians(self.a2+i*45)
            x1,y1=cx+r*.62*math.cos(a),cy+r*.62*math.sin(a)
            x2,y2=cx+r*.62*math.cos(a+math.radians(17)),cy+r*.62*math.sin(a+math.radians(17))
            pygame.draw.line(surf,(*RED2,170),(int(x1),int(y1)),(int(x2),int(y2)),1)
        cr=int(r*.26+math.sin(self.pulse)*3)
        glow_circle(surf,RED3,cx,cy,cr,0,200)
        pygame.draw.circle(surf,RED3,(cx,cy),cr)

# ══════════════════════════════════════════════════════════════════════════════
# WAVEFORM
# ══════════════════════════════════════════════════════════════════════════════
class Waveform:
    BARS=40
    def __init__(self,x,y,w,h):
        self.rect=(x,y,w,h)
        self.heights=[0.]*self.BARS; self.target=[0.]*self.BARS
        self.active=False; self.t=0.
    def set_active(self,on): self.active=on
    def update(self,dt):
        self.t+=dt
        for i in range(self.BARS):
            self.target[i]=(random.uniform(.15,1.) if self.active
                            else abs(math.sin(self.t*1.4+i*.32))*.11)
            self.heights[i]+=(self.target[i]-self.heights[i])*min(1,dt*14)
    def draw(self,surf):
        x,y,w,h=self.rect; bw=w/self.BARS; mid=y+h//2
        for i,ht in enumerate(self.heights):
            bh=max(3,int(ht*h*.9)); bx=int(x+i*bw+bw*.15); bw2=max(2,int(bw*.65))
            al=int(160+95*ht); col=RED3 if self.active else RED2
            s=pygame.Surface((bw2,bh*2),pygame.SRCALPHA)
            for dy in range(bh):
                a=int(al*(1-dy/bh*.5))
                pygame.draw.rect(s,(*col,a),(0,bh-dy-1,bw2,2))
                pygame.draw.rect(s,(*col,a),(0,bh+dy,bw2,2))
            surf.blit(s,(bx,mid-bh))

# ══════════════════════════════════════════════════════════════════════════════
# CHAT MESSAGE
# ══════════════════════════════════════════════════════════════════════════════
class ChatMessage:
    def __init__(self,role,text):
        self.role=role; self.text=text
        self.alpha=0; self.y_off=18.; self._streaming=False
    def update(self,dt):
        self.alpha=min(255,self.alpha+int(620*dt))
        self.y_off=max(0.,self.y_off-85*dt)

# ══════════════════════════════════════════════════════════════════════════════
# STT RESULT
# ══════════════════════════════════════════════════════════════════════════════
class STTResult:
    def __init__(self):
        self.text=""; self.state="idle"; self.show_ttl=0.; self.pulse=0.
    def set_listening(self): self.state="listening"; self.text=""; self.show_ttl=0.; self.pulse=0.
    def set_processing(self): self.state="processing"
    def set_result(self,t): self.text=t.strip().capitalize(); self.state="done"; self.show_ttl=4.
    def set_error(self,m): self.text=m; self.state="error"; self.show_ttl=3.
    def set_idle(self): self.state="idle"
    def update(self,dt):
        self.pulse=(self.pulse+dt*3)%(2*math.pi)
        if self.show_ttl>0: self.show_ttl=max(0,self.show_ttl-dt)

# ══════════════════════════════════════════════════════════════════════════════
# MAIN APP
# ══════════════════════════════════════════════════════════════════════════════
class FridayApp:
    SB     = 232    # sidebar width
    MW     = 258    # memory panel width
    CP     = 12     # chat padding
    IH     = 48     # input height
    HH     = 68     # header height
    VH     = 52     # viz height
    FH     = None   # footer height (computed)

    def __init__(self):
        pygame.init()
        pygame.display.set_caption("F.R.I.D.A.Y. — DHANUSH SUBHASH")
        self.screen=pygame.display.set_mode((W,H),pygame.RESIZABLE)
        self.clock=pygame.time.Clock()
        pygame.mixer.init()

        self.FH = self.VH + self.IH + 28

        # Fonts
        self.f_title = pygame.font.SysFont("monospace",20,bold=True)
        self.f_body  = pygame.font.SysFont("monospace",13)
        self.f_sm    = pygame.font.SysFont("monospace",11)
        self.f_inp   = pygame.font.SysFont("monospace",14)
        self.f_lbl   = pygame.font.SysFont("monospace",9,bold=True)
        self.f_mem   = pygame.font.SysFont("monospace",11)
        self.f_memk  = pygame.font.SysFont("monospace",10,bold=True)

        # Subsystems
        self.memory  = MemoryStore()
        self.stt_res = STTResult()
        self.reactor = ArcReactor(self.SB//2, self.HH//2+14, 30)
        self.viz     = Waveform(0,0,1,1)

        # Surfaces
        self.scanlines = make_scanlines(W,H)
        self.grid_surf = self._make_grid(W,H)

        # State
        self.messages:list[ChatMessage]=[]
        self.history=[]; self.scroll=0
        self.inp_text=""; self.cur_vis=True; self.cur_t=0.
        self.status="ONLINE"; self.status_col=GREEN
        self.muted=False; self.recording=False; self.waiting=False
        self.stream_buf=""; self.mem_scroll=0
        self.mem_edit=False; self.mem_inp=""

        self.token_q=queue.Queue(); self.speak_q=queue.Queue()
        self.rec=sr.Recognizer(); self.rec.dynamic_energy_threshold=True

        threading.Thread(target=self._tts_worker,daemon=True).start()
        self._layout()

        user=self.memory.get("user_name") or "boss"
        self._add_msg("ai",f"F.R.I.D.A.Y. online. All systems operational. What do you need, {user}?")

    # ── Layout ─────────────────────────────────────────────────────────────────
    def _layout(self):
        w,h=self.screen.get_size()
        vx=self.SB+self.CP; vy=h-self.FH+4
        vw=w-self.SB-self.MW-self.CP*2
        self.viz=Waveform(vx,vy,vw,self.VH)

    def _make_grid(self,w,h):
        s=pygame.Surface((w,h),pygame.SRCALPHA)
        for x in range(0,w,55): pygame.draw.line(s,(140,0,0,14),(x,0),(x,h))
        for y in range(0,h,55): pygame.draw.line(s,(140,0,0,14),(0,y),(w,y))
        return s

    def _add_msg(self,role,text):
        self.messages.append(ChatMessage(role,text)); self.scroll=0

    # ── TTS ────────────────────────────────────────────────────────────────────
    def _tts_worker(self):
        while True:
            text=self.speak_q.get()
            if text is None: break
            if self.muted: continue
            try:
                c=clean_tts(text)
                if not c: continue
                async def _go(t):
                    com=edge_tts.Communicate(t,voice="en-US-AriaNeural",
                                             rate="+10%",pitch="+2Hz",volume="+10%")
                    buf=io.BytesIO()
                    async for chunk in com.stream():
                        if chunk["type"]=="audio": buf.write(chunk["data"])
                    buf.seek(0); return buf
                buf=asyncio.run(_go(c))
                if buf.getbuffer().nbytes<100: continue
                with tempfile.NamedTemporaryFile(suffix=".mp3",delete=False) as f:
                    f.write(buf.read()); fn=f.name
                pygame.mixer.music.load(fn); pygame.mixer.music.play()
                self.viz.set_active(True)
                while pygame.mixer.music.get_busy(): time.sleep(0.05)
                os.unlink(fn)
            except Exception as e: print(f"[tts] {e}")
            finally: self.viz.set_active(False)

    # ── Ollama ─────────────────────────────────────────────────────────────────
    def _build_prompt(self):
        base=SYSTEM_PROMPT
        ctx=self.memory.as_context()
        return base+("\n\n"+ctx if ctx else "")

    def _chat_thread(self,text):
        self.history.append({"role":"user","content":text})
        msgs=[{"role":"system","content":self._build_prompt()}]+self.history[-MAX_HISTORY:]
        full=""
        try:
            for chunk in ollama.chat(model=MODEL,messages=msgs,stream=True,options={"num_predict":300}):
                tok=chunk["message"]["content"]; full+=tok
                self.token_q.put(("tok",tok))
        except Exception as e:
            self.token_q.put(("err",str(e)))
            if self.history and self.history[-1]["role"]=="user": self.history.pop()
            return
        self.history.append({"role":"assistant","content":full})
        self.token_q.put(("done",full))

    # ── STT ────────────────────────────────────────────────────────────────────
    def _record_thread(self):
        try:
            with sr.Microphone() as src:
                self.rec.adjust_for_ambient_noise(src,duration=0.4)
                self.stt_res.set_listening()
                self.status="LISTENING..."; self.status_col=RED3
                audio=self.rec.listen(src,timeout=8,phrase_time_limit=15)
            self.stt_res.set_processing()
            self.status="PROCESSING..."; self.status_col=YELLOW
            text=self.rec.recognize_google(audio)
            self.stt_res.set_result(text)
            self.token_q.put(("voice",text))
        except sr.UnknownValueError:
            self.stt_res.set_error("Could not understand")
            self.token_q.put(("voice_err","Could not understand"))
        except Exception as e:
            self.stt_res.set_error(str(e))
            self.token_q.put(("voice_err",str(e)))
        finally:
            self.recording=False; self.viz.set_active(False)

    # ── Send ───────────────────────────────────────────────────────────────────
    def _send(self,text):
        text=text.strip()
        if not text or self.waiting: return
        mem=self.memory.parse_command(text)
        if mem:
            self._add_msg("user",text); self._add_msg("ai",mem[1])
            if not self.muted: self.speak_q.put(mem[1]); return
        self._add_msg("user",text)
        self.waiting=True; self.stream_buf=""
        self.status="THINKING..."; self.status_col=RED3
        self.viz.set_active(True)
        threading.Thread(target=self._chat_thread,args=(text,),daemon=True).start()

    # ── Drain queue ─────────────────────────────────────────────────────────────
    def _drain(self):
        try:
            while True:
                kind,data=self.token_q.get_nowait()
                if kind=="tok":
                    self.stream_buf+=data
                    if self.messages and self.messages[-1].role=="ai" and \
                       getattr(self.messages[-1],"_streaming",False):
                        self.messages[-1].text=self.stream_buf
                    else:
                        m=ChatMessage("ai",self.stream_buf); m._streaming=True
                        self.messages.append(m); self.scroll=0
                elif kind=="done":
                    if self.messages and getattr(self.messages[-1],"_streaming",False):
                        self.messages[-1].text=data; self.messages[-1]._streaming=False
                    self.waiting=False; self.status="ONLINE"; self.status_col=GREEN
                    self.viz.set_active(False)
                    if not self.muted: self.viz.set_active(True); self.speak_q.put(data)
                    # auto-save last session date
                    self.memory.add("last_session",time.strftime("%Y-%m-%d"),"Last active")
                elif kind=="err":
                    self._add_msg("ai",f"⚠ {data}")
                    self.waiting=False; self.status="ERROR"; self.status_col=RED3
                elif kind=="voice":
                    self.inp_text=data; self.status="ONLINE"; self.status_col=GREEN
                    self._send(data); self.inp_text=""
                elif kind=="voice_err":
                    self.status="ONLINE"; self.status_col=GREEN
                    self._add_msg("ai",f"⚠ STT: {data}")
        except queue.Empty: pass

    # ══════════════════════════════════════════════════════════════════════════
    # DRAW: SIDEBAR
    # ══════════════════════════════════════════════════════════════════════════
    def _draw_sidebar(self,surf):
        sw=self.SB; h=surf.get_height()
        pygame.draw.rect(surf,PANEL,(0,0,sw,h))
        pygame.draw.line(surf,(*RED,90),(sw,0),(sw,h),1)
        self.reactor.draw(surf)

        ty=self.HH+6
        draw_text(surf,"F.R.I.D.A.Y.",self.f_title,RED3,sw//2,ty,align="center"); ty+=24
        draw_text(surf,"FEMALE REPLACEMENT INTELLIGENT",self.f_lbl,MUTED,sw//2,ty,align="center"); ty+=12
        draw_text(surf,"DIGITAL ASSISTANT YOUTH",self.f_lbl,MUTED,sw//2,ty,align="center"); ty+=16

        user=self.memory.get("user_name") or "UNKNOWN"
        draw_text(surf,f"OPERATOR: {user.upper()}",self.f_lbl,(*YELLOW,210),sw//2,ty,align="center"); ty+=14
        pygame.draw.line(surf,(*RED,50),(12,ty),(sw-12,ty),1); ty+=10

        # Status
        draw_text(surf,"SYSTEM STATUS",self.f_lbl,MUTED,16,ty); ty+=14
        pygame.draw.circle(surf,self.status_col,(19,ty+5),4)
        glow_circle(surf,self.status_col,19,ty+5,4,0,55)
        draw_text(surf,self.status,self.f_sm,self.status_col,30,ty); ty+=22

        rows=[("MODEL",MODEL[:18]),
              ("VOICE","MUTED" if self.muted else "ARIA NEURAL"),
              ("INPUT","RECORDING" if self.recording else "STANDBY"),
              ("MEMORY",f"{len(self.memory.entries)} entries"),
              ("MSGS",str(len(self.messages)))]
        for lbl,val in rows:
            draw_text(surf,lbl,self.f_lbl,MUTED,16,ty); ty+=13
            draw_text(surf,val,self.f_sm,WHITE,16,ty); ty+=18

        pygame.draw.line(surf,(*RED,40),(12,ty+2),(sw-12,ty+2),1); ty+=12

        # Hotkeys  (all Ctrl or Shift combos)
        draw_text(surf,"HOTKEYS",self.f_lbl,MUTED,16,ty); ty+=13
        for k,d in [("CTRL+L","Listen (voice)"),("CTRL+M","Mute toggle"),
                    ("CTRL+N","Add memory"),("CTRL+↑↓","Scroll"),("ESC","Quit")]:
            draw_text(surf,k,self.f_sm,RED2,16,ty)
            draw_text(surf,d,self.f_sm,MUTED,90,ty); ty+=15

        pygame.draw.line(surf,(*RED,35),(12,ty+2),(sw-12,ty+2),1); ty+=10
        draw_text(surf,'SAY: "remember X is Y"',self.f_lbl,(*RED,140),sw//2,ty,align="center"); ty+=13
        draw_text(surf,'SAY: "forget X"',self.f_lbl,(*RED,140),sw//2,ty,align="center")

        draw_corners(surf,(4,4,sw-8,h-8),(*RED,60),12,1)

    # ══════════════════════════════════════════════════════════════════════════
    # DRAW: MEMORY PANEL
    # ══════════════════════════════════════════════════════════════════════════
    def _draw_memory(self,surf):
        w=surf.get_width(); h=surf.get_height()
        mx=w-self.MW; mw=self.MW
        pygame.draw.rect(surf,PANEL,(mx,0,mw,h))
        pygame.draw.line(surf,(*RED,75),(mx,0),(mx,h),1)

        draw_text(surf,"MEMORY CORE",self.f_title,RED3,mx+mw//2,10,align="center")
        draw_text(surf,f"{len(self.memory.entries)} RECORDS",self.f_lbl,MUTED,mx+mw//2,30,align="center")
        pygame.draw.line(surf,(*RED,45),(mx+10,46),(mx+mw-10,46),1)

        row_h=42; vis_top=50; vis_h=h-vis_top-62
        entries=self.memory.entries
        max_sc=max(0,len(entries)*row_h-vis_h)
        self.mem_scroll=max(0,min(self.mem_scroll,max_sc))

        clip=pygame.Rect(mx,vis_top,mw,vis_h)
        surf.set_clip(clip)
        for idx,e in enumerate(entries):
            ey=vis_top+idx*row_h-self.mem_scroll
            if ey+row_h<vis_top or ey>vis_top+vis_h: continue
            bg=PANELB if idx%2==0 else PANEL2
            rs=pygame.Surface((mw-4,row_h-3),pygame.SRCALPHA)
            pygame.draw.rect(rs,(*bg,210),(0,0,mw-4,row_h-3))
            pygame.draw.rect(rs,(*RED,50),(0,0,2,row_h-3))
            kc=RED3 if e["key"] in ("user_name","created_by","model") else RED2
            draw_text(rs,e["key"].upper()[:26],self.f_memk,kc,6,4)
            draw_text(rs,e["value"][:28],self.f_mem,WHITE,6,16)
            if e.get("note"): draw_text(rs,e["note"][:30],self.f_lbl,MUTED,6,28)
            surf.blit(rs,(mx+2,ey))
        surf.set_clip(None)

        if max_sc>0:
            pct=self.mem_scroll/max_sc
            bh=max(20,int(vis_h*.15))
            by=int(vis_top+(vis_h-bh)*pct)
            pygame.draw.rect(surf,(*RED,90),(w-6,by,3,bh),border_radius=2)

        boty=h-54
        pygame.draw.line(surf,(*RED,40),(mx+10,boty-4),(mx+mw-10,boty-4),1)
        if self.mem_edit:
            pygame.draw.rect(surf,PANELB,(mx+6,boty,mw-12,34),border_radius=2)
            pygame.draw.rect(surf,(*YELLOW,160),(mx+6,boty,mw-12,34),1,border_radius=2)
            draw_text(surf,"▸ "+self.mem_inp+"█",self.f_sm,YELLOW,mx+10,boty+10)
            draw_text(surf,"key=value  ENTER to save",self.f_lbl,(*YELLOW,130),mx+mw//2,boty+38,align="center")
        else:
            draw_text(surf,"[CTRL+N] ADD MEMORY",self.f_lbl,(*RED,130),mx+mw//2,boty+10,align="center")
            draw_text(surf,"or: remember X is Y",self.f_lbl,(*MUTED,150),mx+mw//2,boty+24,align="center")

        draw_corners(surf,(mx+3,3,mw-6,h-6),(*RED,55),10,1)

    # ══════════════════════════════════════════════════════════════════════════
    # DRAW: STT OVERLAY
    # ══════════════════════════════════════════════════════════════════════════
    def _draw_stt(self,surf):
        state=self.stt_res.state
        if state=="idle" and self.stt_res.show_ttl<=0: return
        w=surf.get_width(); h=surf.get_height()
        cx=(self.SB + w-self.MW)//2

        if state in ("listening","processing"):
            r=int(26+5*abs(math.sin(self.stt_res.pulse)))
            col=RED3 if state=="listening" else YELLOW
            glow_circle(surf,col,cx,h-self.FH-62,r,2,100)
            pygame.draw.circle(surf,col,(cx,h-self.FH-62),8)
            lbl="LISTENING — SPEAK NOW" if state=="listening" else "PROCESSING AUDIO..."
            draw_text(surf,lbl,self.f_lbl,col,cx,h-self.FH-36,align="center")
            dots="●"*((int(self.stt_res.pulse*2)%3)+1)
            draw_text(surf,dots,self.f_sm,(*col,180),cx,h-self.FH-22,align="center")

        elif state in ("done","error") and self.stt_res.show_ttl>0:
            al=min(255,int(self.stt_res.show_ttl*120))
            col=GREEN if state=="done" else RED3
            txt=f'"{self.stt_res.text}"' if state=="done" else f"⚠ {self.stt_res.text}"
            tw=self.f_sm.size(txt)[0]
            bx=cx-tw//2-14; by=h-self.FH-54; bw=tw+28; bh=26
            bg=pygame.Surface((bw,bh),pygame.SRCALPHA)
            pygame.draw.rect(bg,(*DARK,min(200,al)),(0,0,bw,bh),border_radius=13)
            pygame.draw.rect(bg,(*col,al),(0,0,bw,bh),1,border_radius=13)
            surf.blit(bg,(bx,by))
            surf.blit(self.f_sm.render(txt,True,(*col,al)),(bx+14,by+5))
            tick="✓ CAPTURED" if state=="done" else "✗ FAILED"
            draw_text(surf,tick,self.f_lbl,(*col,al),cx,by-16,align="center")

    # ══════════════════════════════════════════════════════════════════════════
    # DRAW: CHAT
    # ══════════════════════════════════════════════════════════════════════════
    def _draw_chat(self,surf):
        w=surf.get_width(); h=surf.get_height()
        cx=self.SB+self.CP
        chat_w=w-self.SB-self.MW-self.CP*2
        top=self.HH; bot=h-self.FH
        surf.set_clip(pygame.Rect(cx,top,chat_w,bot-top))

        lh=self.f_body.get_linesize(); pad=10; gap=9
        cpl=max(10,int((chat_w-pad*2-4)/self.f_body.size("A")[0]))

        renders=[]
        for msg in self.messages:
            wrapped=textwrap.wrap(msg.text,cpl) or [""]
            mh=pad*2+len(wrapped)*lh+14
            renders.append((msg,wrapped,mh))

        total=sum(r[2]+gap for r in renders)
        max_sc=max(0,total-(bot-top))
        self.scroll=max(0,min(self.scroll,max_sc))

        dy=bot-self.scroll
        for msg,lines,mh in reversed(renders):
            dy-=mh+gap
            is_user=msg.role=="user"
            accent=RED2 if is_user else RED3
            bcolor=(28,6,6) if is_user else PANELB
            al=min(255,msg.alpha); yo=int(msg.y_off)

            bub=pygame.Surface((chat_w,mh),pygame.SRCALPHA)
            pygame.draw.rect(bub,(*bcolor,min(200,al)),(0,0,chat_w,mh))
            pygame.draw.rect(bub,(*accent,min(200,al)),(0,0,3,mh))
            draw_corners(bub,(0,0,chat_w,mh),(*accent,min(110,al)),8,1)
            lbl="OPERATOR" if is_user else "F.R.I.D.A.Y."
            bub.blit(self.f_lbl.render(lbl,True,(*accent,min(175,al))),(pad,pad-1))
            ty=pad+14
            for line in lines:
                bub.blit(self.f_body.render(line,True,(*WHITE,min(255,al))),(pad,ty)); ty+=lh
            if getattr(msg,"_streaming",False) and int(time.time()*2)%2:
                bub.blit(self.f_body.render("█",True,(*RED3,200)),
                         (pad+self.f_body.size(lines[-1] if lines else "")[0],ty-lh))
            surf.blit(bub,(cx,dy+yo))

        surf.set_clip(None)
        if max_sc>0:
            pct=self.scroll/max_sc
            bh=int((bot-top)*.14)
            by=int(top+(bot-top-bh)*(1-pct))
            pygame.draw.rect(surf,(*RED,80),(cx+chat_w,by,3,bh),border_radius=2)

    # ══════════════════════════════════════════════════════════════════════════
    # DRAW: FOOTER
    # ══════════════════════════════════════════════════════════════════════════
    def _draw_footer(self,surf):
        w=surf.get_width(); h=surf.get_height()
        cx=self.SB+self.CP; fw=w-self.SB-self.MW-self.CP*2
        fy=h-self.FH
        pygame.draw.line(surf,(*RED,55),(cx,fy),(cx+fw,fy),1)
        self.viz.draw(surf)

        iy=h-self.IH-8; ir=pygame.Rect(cx,iy,fw,self.IH)
        pygame.draw.rect(surf,PANELB,ir,border_radius=2)
        pygame.draw.rect(surf,(*RED,80),ir,1,border_radius=2)
        draw_corners(surf,(cx,iy,fw,self.IH),(*RED,120),8)
        draw_text(surf,"▸",self.f_inp,RED3,cx+8,iy+15)

        mc=max(10,int((fw-50)/self.f_inp.size("A")[0]))
        disp=self.inp_text[-mc:] if len(self.inp_text)>mc else self.inp_text
        surf.blit(self.f_inp.render(disp,True,WHITE),(cx+24,iy+15))
        if self.cur_vis:
            cx2=cx+24+self.f_inp.size(disp)[0]
            pygame.draw.rect(surf,RED3,(cx2,iy+14,2,self.f_inp.get_height()))

        if self.recording:
            rx=cx+fw-20; ry=iy+self.IH//2
            rr=int(8+3*abs(math.sin(time.time()*4)))
            glow_circle(surf,RED3,rx,ry,rr,0,80)
            pygame.draw.circle(surf,RED3,(rx,ry),7)
        if self.muted:
            draw_text(surf,"[MUTED]",self.f_lbl,MUTED,cx+fw-70,iy-14)

    # ══════════════════════════════════════════════════════════════════════════
    # DRAW: HEADER
    # ══════════════════════════════════════════════════════════════════════════
    def _draw_header(self,surf):
        w=surf.get_width(); mw=self.MW
        pygame.draw.line(surf,(*RED,60),(self.SB,0),(w-mw,0),1)
        draw_text(surf,time.strftime("%Y.%m.%d  %H:%M:%S"),self.f_sm,MUTED,w-mw-12,8,align="right")
        draw_text(surf,"F.R.I.D.A.Y. · SECURE LINK · CHANNEL 9",self.f_lbl,(*RED,100),self.SB+12,8)
        draw_text(surf,"BY DHANUSH SUBHASH",self.f_lbl,(*MUTED,120),self.SB+12,20)

    # ══════════════════════════════════════════════════════════════════════════
    # MAIN LOOP
    # ══════════════════════════════════════════════════════════════════════════
    def run(self):
        running=True
        while running:
            dt=self.clock.tick(FPS)/1000.
            ctrl=pygame.key.get_mods() & pygame.KMOD_CTRL

            for ev in pygame.event.get():
                if ev.type==pygame.QUIT: running=False
                elif ev.type==pygame.VIDEORESIZE:
                    self.scanlines=make_scanlines(ev.w,ev.h)
                    self.grid_surf=self._make_grid(ev.w,ev.h)
                    self._layout()

                elif ev.type==pygame.KEYDOWN:

                    # ── Memory edit mode ──────────────────────────────────────
                    if self.mem_edit:
                        if ev.key==pygame.K_ESCAPE:
                            self.mem_edit=False; self.mem_inp=""
                        elif ev.key==pygame.K_RETURN:
                            if "=" in self.mem_inp:
                                k,v=self.mem_inp.split("=",1)
                                msg=self.memory.add(k.strip(),v.strip())
                                self._add_msg("ai",msg)
                                if not self.muted: self.speak_q.put(msg)
                            self.mem_edit=False; self.mem_inp=""
                        elif ev.key==pygame.K_BACKSPACE: self.mem_inp=self.mem_inp[:-1]
                        elif ev.unicode and ev.unicode.isprintable(): self.mem_inp+=ev.unicode
                        continue

                    # ── Global hotkeys (Ctrl combos — never block typing) ─────
                    mods=pygame.key.get_mods()
                    is_ctrl =bool(mods & pygame.KMOD_CTRL)
                    is_shift=bool(mods & pygame.KMOD_SHIFT)

                    if ev.key==pygame.K_ESCAPE:
                        running=False

                    elif ev.key==pygame.K_RETURN:
                        self._send(self.inp_text); self.inp_text=""

                    elif ev.key==pygame.K_BACKSPACE:
                        self.inp_text=self.inp_text[:-1]

                    elif is_ctrl and ev.key==pygame.K_l:
                        # Ctrl+L  → start voice listening
                        if not self.recording and not self.waiting:
                            self.recording=True; self.viz.set_active(True)
                            self.stt_res.set_listening()
                            threading.Thread(target=self._record_thread,daemon=True).start()

                    elif is_ctrl and ev.key==pygame.K_m:
                        # Ctrl+M  → mute toggle
                        self.muted=not self.muted

                    elif is_ctrl and ev.key==pygame.K_n:
                        # Ctrl+N  → open memory editor
                        self.mem_edit=True; self.mem_inp=""

                    elif is_ctrl and ev.key==pygame.K_UP:
                        self.scroll+=50
                    elif is_ctrl and ev.key==pygame.K_DOWN:
                        self.scroll=max(0,self.scroll-50)

                    else:
                        # Normal typing — only if no Ctrl/Alt held
                        if not is_ctrl and ev.unicode and ev.unicode.isprintable():
                            self.inp_text+=ev.unicode

                elif ev.type==pygame.MOUSEWHEEL:
                    pos=pygame.mouse.get_pos()
                    if pos[0]>self.screen.get_width()-self.MW:
                        self.mem_scroll=max(0,self.mem_scroll+ev.y*-25)
                    else:
                        self.scroll=max(0,self.scroll+ev.y*-30)

            self._drain()

            # Update
            self.reactor.update(dt); self.viz.update(dt); self.stt_res.update(dt)
            for m in self.messages: m.update(dt)
            self.cur_t+=dt
            if self.cur_t>=0.5: self.cur_vis=not self.cur_vis; self.cur_t=0.

            # Draw
            surf=self.screen; surf.fill(DARK)
            surf.blit(self.grid_surf,(0,0))
            self._draw_sidebar(surf)
            self._draw_memory(surf)
            self._draw_header(surf)
            self._draw_chat(surf)
            self._draw_footer(surf)
            self._draw_stt(surf)
            surf.blit(self.scanlines,(0,0))
            pygame.display.flip()

        self.speak_q.put(None)
        pygame.quit(); sys.exit(0)

# ══════════════════════════════════════════════════════════════════════════════
if __name__=="__main__":
    print("\n"+"="*54)
    print("  F.R.I.D.A.Y. — BY DHANUSH SUBHASH")
    print("  Make sure 'ollama serve' is running!")
    print("="*54+"\n")
    FridayApp().run()
