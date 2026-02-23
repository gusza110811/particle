from vector import Vector2d
import pygame
import math
import struct
import sys
import io

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
        # camZoom is the power of 2 to scale the world by when rendering, so camZoom of 1 means 2x zoom, camZoom of -1 means 0.5x zoom
        self.camZoom = round(math.log2((self.screenVerLim/2)/self.verticalLim),1)
        #self.camZoom = 0
        if version >= 2:
            print("Incompatible version, expected 1, got",version,file=sys.stderr)
            return
        frame = 0

        clock = pygame.time.Clock()

        rendering = True

        particles = []
        
        while self.running:
            self.screen.fill((0,0,0))
            dt = clock.get_time()/1000
            self.event(dt)
            if rendering and not self.paused:
                particlesbuf = []
                frameidb = source.read(4)
                frameId = int.from_bytes(frameidb,byteorder='little')
                if frameidb == b"":
                    rendering = False
                    continue
                if frameId != frame:
                    print(f"File Corrupted: expected frame ID {frame}, got {frameId} (at position {source.tell():X})",file=sys.stderr)
                    return
                partCount = int.from_bytes(source.read(4),"little")
                for idx in range(partCount):
                    x = struct.unpack("<f",source.read(4))[0]
                    y = struct.unpack("<f",source.read(4))[0]
                    position = Vector2d(x,y)
                    particlesbuf.append(position)
                frame += 1
                particles = particlesbuf
            self.infoOverlay(frame, clock.get_fps(), self.paused, not rendering)
            self.render(particles)
            clock.tick(30)

    def render(self,particles:list[Vector2d]):
        horLim = self.screenHorLim
        verLim = self.screenVerLim
        r = math.ceil(max(self.radius * 2**self.camZoom,1))
        d = r*2
        centerPos = self.centerPos
        for particle in particles:
            pos = (particle - self.cam).scale(2**self.camZoom).translate(centerPos)
            # culling
            if (abs(pos.x) > horLim+d) or (abs(pos.y) > verLim+d):
                continue
            self.draw.circle(self.screen, (255,255,255), (pos.x,pos.y), r)
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
                    self.physic()
            elif event.type == pygame.MOUSEWHEEL:
                self.camZoom += event.y/10
        
        pressed = self.key.get_pressed()
        dir = Vector2d()
        if pressed[pygame.K_w]:
            dir.translate((0,-1))
        if pressed[pygame.K_s]:
            dir.translate((0,1))
        if pressed[pygame.K_a]:
            dir.translate((-1,0))
        if pressed[pygame.K_d]:
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
    DOPIPEDTEST = False

    if DOPIPEDTEST:
        testpiped()
    else:
        test()