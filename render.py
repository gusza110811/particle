from vector import Vector2d
import pygame
import math
import struct
import sys
import io
import argparse
import colorsys

class Renderer:
    def __init__(self,source:io.BytesIO):
        self.running = True

        self.source = source
        self.screen = None
        self.scale = 1.0
        pygame.init()
        pygame.font.init()
        self.clock = pygame.time.Clock()
        self.dbgfont = pygame.font.Font(size=20)
        self.output = None
        self.Color = pygame.Color
        self.display = pygame.display
        self.draw = pygame.draw

        self.mouse = pygame.mouse
        self.key = pygame.key

        screen = pygame.display.set_mode((960,720))
        self.screen = screen
        self.screenHorLim = screen.get_width()
        self.screenVerLim = screen.get_height()
        self.centerPos = Vector2d(screen.get_width()//2,screen.get_height()//2)
        self.cam = Vector2d(0,0)

        self.paused = False
    
    def main(self):
        source = self.source

        # check magic
        magic = self.source.read(8)
        if magic != b"\xFFPARTSIM":
            raise Exception(f"Invalid file format")
        # read header
        version = int.from_bytes(source.read(1),byteorder="little")
        self.horizontalLim = int.from_bytes(source.read(4),byteorder="little")
        self.verticalLim = int.from_bytes(source.read(4),byteorder="little")
        self.radius = struct.unpack("<f",source.read(4))[0]
        self.borderType = int.from_bytes(source.read(1),byteorder="little")
        self.velLimit = struct.unpack("<f",source.read(4))[0]
        # camZoom is the power of 2 to scale the world by when rendering, so camZoom of 1 means 2x zoom, camZoom of -1 means 0.5x zoom
        self.camZoom = round(math.log2((self.screenVerLim/2)/self.verticalLim),1)
        #self.camZoom = 0
        if version != 2:
            print("Incompatible version, expected 2, got",version,file=sys.stderr)
            return
        self.frame = 0

        self.clock = pygame.time.Clock()
        self.particlespos = []
        self.particlesvel = []

        self.rendering = True
        
        while self.running:
            self.screen.fill((0,0,0))
            self.doFrame()
    
    def doFrame(self):
        dt = self.clock.get_time()/1000
        self.event(dt)
        if self.rendering and not self.paused:
            particlespos, particlesvel = self.read()
            if not self.rendering:return
            self.particlespos = particlespos
            self.particlesvel = particlesvel

        self.render(self.particlespos,self.particlesvel)
        self.clock.tick(30)

    def read(self):
        particlesposbuf = []
        particlevelbuf = []
        frameidb = source.read(4)
        frameId = int.from_bytes(frameidb,byteorder='little')
        if frameidb == b"":
            self.rendering = False
        if frameId != self.frame:
            print(f"File Corrupted: expected frame ID {self.frame}, got {frameId} (at position {source.tell():X})",file=sys.stderr)
            return None, None
        partCount = int.from_bytes(source.read(4),"little")
        for idx in range(partCount):
            x = struct.unpack("<f",source.read(4))[0]
            y = struct.unpack("<f",source.read(4))[0]
            vx = struct.unpack("<f",source.read(4))[0]
            vy = struct.unpack("<f",source.read(4))[0]
            position = Vector2d(x,y)
            velocity = Vector2d(vx,vy)
            particlesposbuf.append(position)
            particlevelbuf.append(velocity)
        self.frame += 1
        return particlesposbuf, particlevelbuf

    def render(self,positions:list[Vector2d],velocities:list[Vector2d]):
        horLim = self.screenHorLim
        verLim = self.screenVerLim
        r = math.ceil(max(self.radius * 2**self.camZoom,1)*1.1+1)
        d = r*2
        centerPos = self.centerPos
        velLim = self.velLimit
        for idx, particle in enumerate(positions):
            pos = (particle - self.cam).scale(2**self.camZoom).translate(centerPos)
            vel = velocities[idx]
            speednor = min(vel.magnitude()/velLim,0.9)

            color = [ int(c*255) for c in
                colorsys.hsv_to_rgb(
                    speednor,1,1
                )
            ]

            # culling
            if (abs(pos.x) > horLim+d) or (abs(pos.y) > verLim+d):
                continue
            self.draw.circle(self.screen, color, (pos.x,pos.y), r)
        self.infoOverlay(self.frame, self.clock.get_fps(), self.paused, not self.rendering)
        pygame.display.flip()
    
    def infoOverlay(self, frames, fps, paused, done):
        text = f"Frame: {frames}" + (" [done]" if done else "") + f" | FPS: {fps:.2f} | {'Paused' if paused else 'Running'}"
        overlay = self.dbgfont.render(text, True, (255, 255, 255))
        self.screen.blit(overlay, (10, 10))

    def event(self,dt):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    self.paused = not self.paused
                elif event.key == pygame.K_f:
                    self.paused = True
                    self.particlespos, self.particlesvel = self.read()
                    self.render(self.particlespos,self.particlesvel)
            elif event.type == pygame.MOUSEWHEEL:
                self.camZoom += event.y/10
        
        pressed = self.key.get_pressed()
        dir = Vector2d()
        if pressed[pygame.K_w] or pressed[pygame.K_UP]:
            dir.translate((0,-1))
        if pressed[pygame.K_s] or pressed[pygame.K_DOWN]:
            dir.translate((0,1))
        if pressed[pygame.K_a] or pressed[pygame.K_LEFT]:
            dir.translate((-1,0))
        if pressed[pygame.K_d] or pressed[pygame.K_RIGHT]:
            dir.translate((1,0))
        
        self.cam.translate(dir.scale(300*(2**-self.camZoom)*dt))

def test():
    with open("output.sim","rb") as source:
        renderer = Renderer(source)
        renderer.main()

def testpiped():
    import subprocess
    proc = subprocess.Popen([sys.executable,"sim.py","-o-","-f1000"],stdout=subprocess.PIPE)
    renderer = Renderer(proc.stdout)
    renderer.main()

if __name__ == "__main__":
    argparser = argparse.ArgumentParser(description="Render particle simulation")
    argparser.add_argument("--file", "-f", type=str, default="output.sim", help="Input file for simulation data", nargs="?")
    args = argparser.parse_args()

    if args.file == "-":
        source = sys.stdin.buffer
    else:
        source = open(args.file,"rb")
    renderer = Renderer(source)
    renderer.main()
