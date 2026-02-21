import particle as Particle
from vector import Vector2d
import pygame
import random
import math

class Simulation:
    def __init__(self, screen:pygame.Surface):
        self.screen = screen
        self.running = True
        self.clock = pygame.time.Clock()
        self.dbgfont = pygame.font.Font(size=20)

        self.horizontalLim = screen.get_width()
        self.verticalLim = screen.get_height()
        self.centerPos = Vector2d(screen.get_width()//2,screen.get_height()//2)
        self.cam = Vector2d(0,0)

        self.borderTopLeft = Vector2d(-screen.get_width()//2,-screen.get_height()//2)
        self.borderBottomRight = Vector2d(screen.get_width()//2,screen.get_height()//2)

        self.particles:list[Particle.Particle] = []
        self.cell_size = Particle.Particle.radius*2

        self.paused = False

        self.debug = True

    def main(self):

        render = 0

        self.buffer = []

        for idx in range(500):
            for idk in range(1,5):
                part = Particle.Particle((370,-200+idk*Particle.Particle.radius*1.5))
                part.vel.x -= 1
                self.buffer.append(part)

        while self.running:
            self.frame()
            self.clock.tick(30)
    
    def frame(self):
        buffer = self.buffer
        if buffer:
            self.particles.append(buffer.pop())
            self.particles.append(buffer.pop())
            self.particles.append(buffer.pop())
            self.particles.append(buffer.pop())

        self.event()
        if not self.paused:
            self.physic()

        self.render()

    
    def render(self):
        screen = self.screen

        screen.fill(pygame.Color(0,0,0))

        centerPos = self.centerPos
        horLim = self.horizontalLim
        verLim = self.verticalLim
        r = Particle.Particle.radius
        d = r*2
        circle_surf = pygame.Surface((d, d), pygame.SRCALPHA)
        pygame.draw.circle(circle_surf, pygame.Color(255,255,255), (r, r), r)

        for particle in self.particles:
            pos = (particle.pos + centerPos).translate(self.cam)
            # culling
            if (abs(pos.x) > horLim+particle.radius) or (abs(pos.y) > verLim+particle.radius):
                continue

            screen.blit(circle_surf, (pos.x-r, pos.y-r))
        
        if self.debug:
            self.dbgOverlay()

        pygame.display.update()
    
    def physic(self):
        particles = self.particles
        cs = self.cell_size
        self.doGravity()

        for _ in range(8):
            self.boundCheck()
            self.overlapCheck(particles,cs)
            self.doPhysicMethod()
    def buildGrid(self, particles, cs):
        grid = {}

        for p in particles:
            cx = int(p.pos.x // cs)
            cy = int(p.pos.y // cs)

            key = (cx, cy)
            if key in grid:
                grid[key].append(p)
            else:
                grid[key] = [p]

        return grid
    
    def doPhysicMethod(self):
        particles = self.particles
        applyPhysic = self.applyPhysic
        for id in range(len(particles)):
            applyPhysic(particles[id])
    
    def doGravity(self):
        particles = self.particles
        gravity = self.gravity
        for id in range(len(particles)):
            gravity(particles[id])
    
    def gravity(self,part):
        part.vel.translate(part.gravity)
    
    def overlapCheck(self, particles, cs):
        applyOverlap = self.applyOverlap
        grid:dict[tuple[int,int],list[Particle.Particle]] = self.buildGrid(particles,cs)

        for (cx, cy), cell_particles in grid.items():

            for id1 in range(len(cell_particles)):
                p1 = cell_particles[id1]
                p1x = p1.pos.x
                p1y = p1.pos.y
                p1r = p1.radius
                # Check this cell and neighbors
                for id2 in range(id1+1,len(cell_particles)):
                    p2 = cell_particles[id2]
                    dx = p2.pos.x - p1x
                    dy = p2.pos.y - p1y
                    rs = p1r + p2.radius
                    dist_sq = dx*dx + dy*dy

                    if dist_sq < rs*rs:
                        applyOverlap(p1, p2, dx, dy, dist_sq, rs)
                for ox in (-1,0,1):
                    for oy in (-1,0,1):
                        neighbor_key = (cx + ox, cy + oy)

                        neighbor_particles = grid.get(neighbor_key)

                        if not neighbor_particles:
                            continue

                        for p2 in neighbor_particles:

                            dx = p2.pos.x - p1x
                            dy = p2.pos.y - p1y
                            rs = p1r + p2.radius
                            dist_sq = dx*dx + dy*dy

                            if dist_sq < rs*rs:
                                applyOverlap(p1, p2, dx, dy, dist_sq, rs)
            grid[(cx, cy)] = None
    
    def boundCheck(self):
        particles = self.particles
        for id in range(len(particles)):
            if particles[id].pos.x < self.borderTopLeft.x:
                particles[id].vel.x = abs(particles[id].vel.x) * particles[id].elasticity
                particles[id].pos.x = self.borderTopLeft.x
            elif particles[id].pos.x > self.borderBottomRight.x:
                particles[id].vel.x = -abs(particles[id].vel.x) * particles[id].elasticity
                particles[id].pos.x = self.borderBottomRight.x
            elif particles[id].pos.y < self.borderTopLeft.y:
                particles[id].vel.y = abs(particles[id].vel.y) * particles[id].elasticity
                particles[id].pos.y = self.borderTopLeft.y
            elif particles[id].pos.y > self.borderBottomRight.y:
                particles[id].vel.y = -abs(particles[id].vel.y) * particles[id].elasticity
                particles[id].pos.y = self.borderBottomRight.y
    # assume all particle have equal mass
    def applyCollide(self,pri:Particle.Particle,other:Particle.Particle,
                     nx,ny):

        # relative velocity
        rvx = pri.vel.x - other.vel.x
        rvy = pri.vel.y - other.vel.y

        vel_along_normal = rvx * nx + rvy * ny

        if vel_along_normal < 0:
            return  # moving apart

        impulse = vel_along_normal * pri.elasticity

        imx = impulse * nx
        imy = impulse *ny

        pri.vel.x -= imx
        pri.vel.y -= imy
        other.vel.x += imx
        other.vel.y += imy
    def applyOverlap(self,pri:Particle.Particle,other:Particle.Particle,
                     dx, dy, dist_sq, rs):
        dist = math.sqrt(dist_sq)
        try:
            normalx = dx/dist
        except ZeroDivisionError:
            normalx = 0
        try:
            normaly = dy/dist
        except ZeroDivisionError:
            normaly = 0
        self.applyCollide(pri,other,normalx,normaly)
        expectdist = rs-dist

        correctionx = normalx*expectdist/2
        correctiony = normaly*expectdist/2

        pri.pos.x -= correctionx
        pri.pos.y -= correctiony

        other.pos.x += correctionx
        other.pos.y += correctiony

    def applyPhysic(self,part:Particle.Particle):
        part.pos.translate(part.vel)
        part.vel.scale(part.velConserve)

    def event(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    self.paused = not self.paused
                elif event.key == pygame.K_f:
                    self.paused = True
                    self.physic()
        if pygame.mouse.get_pressed()[0]:
            self.particles.append(Particle.Particle(
                    Vector2d(pygame.mouse.get_pos()).translate(-self.cam).translate(-self.centerPos).translate((random.random(),random.random()))
            ))

    def dbgOverlay(self):
        font = self.dbgfont
        screen = self.screen
        items = [
            f"fps: {self.clock.get_fps()}",
            f"objects: {len(self.particles)}",
            "paused" if self.paused else "unpaused",
        ]

        for idx, item in enumerate(items):
            text = font.render(item,True,pygame.Color(0,255,0))
            screen.blit(text,(0,idx*20))


if __name__ == "__main__":
    pygame.init()
    pygame.font.init()

    screen = pygame.display.set_mode((800,600))

    sim = Simulation(screen)

    sim.main()