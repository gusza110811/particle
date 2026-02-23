import struct
import sys
import particle as Particle
from vector import Vector2d
import random
import math
import colorsys

class Simulation:
    def __init__(self):
        self.running = True

        self.horizontalLim = 512
        self.verticalLim = 512

        self.borderTopLeft = Vector2d(self.horizontalLim*-1,self.verticalLim*-1)
        self.borderBottomRight = Vector2d(self.horizontalLim,self.verticalLim)

        self.gravityRate = Vector2d(0,0.2)
        self.radius = 4
        self.velConserve = 1
        self.elasticity = 0.95

        self.particles:list[Particle.Particle] = []
        self.cell_size = self.radius*2
        self.substep = 8

        self.paused = False
        self.video = False
        self.output = None

        self.debug = True

        self.borderType = 1 # 0 for circle, 1 for square

    def main(self):

        self.buffer = []

        for idx in range(400):
            for idk in range(1,5):
                part = Particle.Particle((0,-self.verticalLim+idk*self.radius*1.5))
                part.vel.x -= 100
                self.buffer.append(part)
        
        buffer = self.buffer

        doVideo = self.video

        if doVideo:
            clock = self.clock
        else:
            # write header for video output
            # format: [magic] [version u8] [horizontalLim u16] [verticalLim u16] [radius f32] [borderType u8]
            self.output.write(b"\xFFPARTSIM")
            self.output.write((1).to_bytes(1,'little'))
            self.output.write(self.horizontalLim.to_bytes(4,'little'))
            self.output.write(self.verticalLim.to_bytes(4,'little'))
            self.output.write(bytearray(struct.pack("<f",self.radius)))
            self.output.write(self.borderType.to_bytes(1,'little'))
        while self.running:
            if not self.paused:
                if buffer:
                    self.particles.append(buffer.pop())
                    self.particles.append(buffer.pop())
                    self.particles.append(buffer.pop())
                    self.particles.append(buffer.pop())
                self.physic()

            if doVideo:
                dt = clock.get_time()/1000
                self.render()
                self.event(dt)
                clock.tick(30)
            else:
                self.saveFrame()
                if self.frame >= self.targetFrames:
                    self.running = False
                print(f"frame {self.frame}/{self.targetFrames}",end="\r",file=sys.stderr)
        if not doVideo:
            print("\ndone",file=sys.stderr)
    
    def initHeadless(self,output,targetFrames):
        self.output = output
        self.frame = 0
        self.targetFrames = targetFrames
    
    def initGraphics(self):
        import pygame
        pygame.init()
        pygame.font.init()
        self.clock = pygame.time.Clock()
        self.dbgfont = pygame.font.Font(size=20)
        self.output = None
        self.Color = pygame.Color
        self.display = pygame.display
        self.draw = pygame.draw

        self.pygame = pygame
        self.mouse = pygame.mouse
        self.key = pygame.key

        screen = pygame.display.set_mode((960,720))
        self.screen = screen
        self.screenHorLim = screen.get_width()
        self.screenVerLim = screen.get_height()
        self.centerPos = Vector2d(screen.get_width()//2,screen.get_height()//2)
        self.cam = Vector2d(0,0)

        # camZoom is the power of 2 to scale the world by when rendering, so camZoom of 1 means 2x zoom, camZoom of -1 means 0.5x zoom
        self.camZoom = round(math.log2((self.screenVerLim/2)/self.verticalLim),1)
        #self.camZoom = 0
        self.video = True
        return screen
    
    def saveFrame(self):
        output = self.output
        particles = self.particles
        # output format: [frame id u32] [particle count u32]
        # [particle x f32] [particle y f32]
        output.write(self.frame.to_bytes(4,'little'))
        output.write(len(particles).to_bytes(4,'little'))
        for part in particles:
            output.write(bytearray(struct.pack("f",part.pos.x)))
            output.write(bytearray(struct.pack("f",part.pos.y)))
        self.frame += 1

    def render(self):
        screen = self.screen

        screen.fill(self.Color(0,0,0))
        radius = self.radius

        centerPos = self.centerPos
        horLim = self.screenHorLim
        verLim = self.screenVerLim
        r = math.ceil(max(radius * 2**self.camZoom,1)*1.1)
        d = r*2
        max_vel = radius*self.substep

        for particle in self.particles:
            pos = (particle.pos - self.cam).scale(2**self.camZoom).translate(centerPos)
            # culling
            if (abs(pos.x) > horLim+d) or (abs(pos.y) > verLim+d):
                continue
            
            # by direction
            #color = [int(color*255) for color in
            #        colorsys.hsv_to_rgb(
            #            (math.atan2(*particle.vel.normalize().tuple())+math.pi)/math.tau,
            #            1,1
            #        )
            #]

            # by speed
            color = [int(color*255) for color in
                colorsys.hsv_to_rgb(
                    min(particle.vel.magnitude()/max_vel,0.9), # dont circle back to red please
                    1,1
                )
            ]

            self.draw.circle(screen, color, (pos.x,pos.y), r)
        
        if self.debug:
            self.dbgOverlay()

        self.display.flip()
    
    def physic(self):
        gravity = self.gravityRate
        radius = self.radius
        velConserve = self.velConserve
        elasticity = self.elasticity
        particles = self.particles
        cs = self.cell_size
        rs = radius*2
        rssq = rs*rs

        substep = self.substep
        substepsize = 1/substep
        max_vel = radius*substep

        grid, sx, sy = self.buildGrid(particles,cs)

        for _ in range(substep):
            self.doGravity(gravity,substepsize)
            self.boundCheck(elasticity,substepsize)
            self.overlapCheck(grid,sx,sy,elasticity,rs,rssq)
            self.doPhysicMethod(max_vel,velConserve,substepsize)
    def buildGrid(self, particles, cs):
        sizex = self.horizontalLim//self.radius
        sizey = self.verticalLim//self.radius
        grid = [[[] for _ in range(sizex)] for _ in range(sizey)]

        for p in particles:
            cx = int(p.pos.x // cs)
            cy = int(p.pos.y // cs)
            if cx >= sizex or cy >= sizey:
                continue

            grid[cx][cy].append(p)

        return grid, sizex, sizey
    
    def doPhysicMethod(self,max_vel,velConserve,subStepSize):
        particles = self.particles
        applyPhysic = self.applyPhysic
        for id in range(len(particles)):
            applyPhysic(particles[id],max_vel,velConserve,subStepSize)

    def doGravity(self,gravityr,substepsize):
        particles = self.particles
        gravity = self.gravity
        gravityrs = gravityr*substepsize
        for id in range(len(particles)):
            gravity(particles[id],gravityrs)
    
    def gravity(self,part,gravity):
        part.vel.translate(gravity)
    
    def overlapCheck(self, grid, sx, sy, elasticity, rs, rssq):
        applyOverlap = self.applyOverlap

        for cx, row in enumerate(grid):
            for cy, cell_particles in enumerate(row):
                for p1 in cell_particles:
                    p1x = p1.pos.x
                    p1y = p1.pos.y
                    # Check this cell and neighbors
                    for ox in (-1,0,1):
                        for oy in (-1,0,1):
                            x = cx+ox
                            y = cy+oy

                            if x >= sx or y >= sy:
                                continue

                            neighbor_particles = grid[x][y]

                            if not neighbor_particles:
                                continue

                            for p2 in neighbor_particles:

                                p2pos = p2.pos

                                dx = p2pos.x - p1x
                                dy = p2pos.y - p1y
                                dist_sq = dx*dx + dy*dy

                                if dist_sq < rssq:
                                    applyOverlap(p1, p2, dx, dy, dist_sq, rs, elasticity)
    
    def boundCheck(self, elasticity, substepsize):
        if self.borderType == 0:
            self.circleBound(elasticity, substepsize)
        elif self.borderType == 1:
            self.squareBound(elasticity, substepsize)
    
    def circleBound(self, elasticity, substepsize):
        particles = self.particles
        # circle boundary
        radius = self.verticalLim
        radiussq = radius*radius
        for id in range(len(particles)):
            particle = particles[id]
            distsq = particle.pos.x*particle.pos.x + particle.pos.y*particle.pos.y

            if radiussq < distsq:
                dist = math.sqrt(distsq)
                correctionx = particle.pos.x / dist * (radius - dist)
                correctiony = particle.pos.y / dist * (radius - dist)
                correctionx *= substepsize
                correctiony *= substepsize
                #print(dist,radius,correction)
                particle.pos.x += correctionx
                particle.pos.y += correctiony
                particle.vel.x *= elasticity
                particle.vel.y *= elasticity
                particle.vel.x += correctionx
                particle.vel.y += correctiony
    
    def squareBound(self, elasticity, substepsize):
        particles = self.particles
        # square boundary
        for id in range(len(particles)):
            if particles[id].pos.x < self.borderTopLeft.x:
                particles[id].vel.x = abs(particles[id].vel.x) * elasticity * substepsize
                particles[id].pos.x = self.borderTopLeft.x
            elif particles[id].pos.x > self.borderBottomRight.x:
                particles[id].vel.x = -abs(particles[id].vel.x) * elasticity * substepsize
                particles[id].pos.x = self.borderBottomRight.x
            if particles[id].pos.y < self.borderTopLeft.y:
                particles[id].vel.y = abs(particles[id].vel.y) * elasticity * substepsize
                particles[id].pos.y = self.borderTopLeft.y
            elif particles[id].pos.y > self.borderBottomRight.y:
                particles[id].vel.y = -abs(particles[id].vel.y) * elasticity * substepsize
                particles[id].pos.y = self.borderBottomRight.y
    # assume all particle have equal mass
    def applyCollide(self,pri:Particle.Particle,other:Particle.Particle,
                     nx,ny,elasticity):

        # relative velocity
        rvx = pri.vel.x - other.vel.x
        rvy = pri.vel.y - other.vel.y

        vel_along_normal = rvx * nx + rvy * ny

        if vel_along_normal < 0:
            return  # moving apart

        impulse = vel_along_normal * elasticity

        imx = impulse * nx
        imy = impulse *ny

        pri.vel.x -= imx
        pri.vel.y -= imy
        other.vel.x += imx
        other.vel.y += imy
    def applyOverlap(self,pri:Particle.Particle,other:Particle.Particle,
                     dx, dy, dist_sq, rs, elasticity):
        dist = math.sqrt(dist_sq)
        if dist > 0:
            normalx = dx/dist
            normaly = dy/dist
        else:
            normalx = 0
            normaly = 0
        self.applyCollide(pri,other,normalx,normaly,elasticity)
        expectdist = rs-dist

        correctionx = normalx*expectdist/2
        correctiony = normaly*expectdist/2

        pri.pos.x -= correctionx
        pri.pos.y -= correctiony

        other.pos.x += correctionx
        other.pos.y += correctiony

    def applyPhysic(self,part:Particle.Particle,max_vel,velConserve,subStepSize):
        vel = part.vel
        pos = part.pos

        # cap velocity to reduce tunneling
        if vel.x*vel.x + vel.y*vel.y > max_vel*max_vel:
            vel = vel.normalize().scale(max_vel)

        pos.x += vel.x * subStepSize
        pos.y += vel.y * subStepSize
        lossx = (1-velConserve) * vel.x * subStepSize
        lossy = (1-velConserve) * vel.y * subStepSize
        vel.x -= lossx
        vel.y -= lossy

    def event(self,dt):
        for event in self.pygame.event.get():
            if event.type == self.pygame.QUIT:
                self.running = False
            elif event.type == self.pygame.KEYDOWN:
                if event.key == self.pygame.K_SPACE:
                    self.paused = not self.paused
                elif event.key == self.pygame.K_f:
                    self.paused = True
                    self.physic()
            elif event.type == self.pygame.MOUSEWHEEL:
                self.camZoom += event.y/10
        if self.mouse.get_pressed()[0]:
            self.particles.append(Particle.Particle(
                    Vector2d(self.mouse.get_pos()).translate(-self.centerPos).scale(1/2**self.camZoom).translate(self.cam).translate((random.random(),random.random()))
            ))
        if self.mouse.get_pressed()[2]:
            mouse_pos = Vector2d(self.mouse.get_pos()).translate(-self.centerPos).scale(1/2**self.camZoom).translate(self.cam)
            closest = None
            closestdist = math.inf
            for idx, part in enumerate(self.particles):
                dist = (part.pos-mouse_pos).magnitude()
                if dist < closestdist:
                    closest = idx
                    closestdist = dist
            
            if closestdist < self.radius:
                self.particles.pop(closest)
        
        pressed = self.key.get_pressed()
        dir = Vector2d()
        if pressed[self.pygame.K_w]:
            dir.translate((0,-1))
        if pressed[self.pygame.K_s]:
            dir.translate((0,1))
        if pressed[self.pygame.K_a]:
            dir.translate((-1,0))
        if pressed[self.pygame.K_d]:
            dir.translate((1,0))
        
        self.cam.translate(dir.scale(300*(2**-self.camZoom)*dt))

    def dbgOverlay(self):
        font = self.dbgfont
        screen = self.screen
        items = [
            f"fps: {self.clock.get_fps()}",
            f"objects: {len(self.particles)}",
            "paused" if self.paused else "unpaused",
            f"zoom: {2**self.camZoom:.2f}x",
        ]

        for idx, item in enumerate(items):
            text = font.render(item,True,self.Color(0,255,0))
            screen.blit(text,(0,idx*20))


def test():
    sim = Simulation()
    sim.initGraphics()
    sim.main()

def testHeadless():
    sim = Simulation()
    with open("output.sim","wb") as f:
        sim.initHeadless(f,1000)
        sim.main()

if __name__ == "__main__":
    testHeadless()